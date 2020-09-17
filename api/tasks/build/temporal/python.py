from io import BytesIO
from tasks.build.common import get_final_zip_package_path, get_codebuild_artifact_zip_data
from utils.general import add_file_to_zipfile
from pyconstants.project_constants import EMPTY_ZIP_DATA
from utils.block_libraries import generate_libraries_dict, get_requirements_text


BUILDSPEC = yaml.dump({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "build": {
            "commands": [
                "pip install --target . -r requirements.txt"
            ]
        },
    },
    "run-as": "root",
    "version": 0.1
})


class Python36Builder:
    RUNTIME = "python3.6"

    def __init__(self, app_config, aws_client_factory, credentials, code, libraries):
        # TODO use dependency injection
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.code = code
        self.libraries = libraries
        self.libraries_object = generate_libraries_dict(self.libraries)

    @property
    def lambda_function(self):
        return self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")[RUNTIME]

    def build(self):
        base_zip_data = EMPTY_ZIP_DATA

        if len(libraries) > 0:
            base_zip_data = self.get_zip_with_deps()

        # Create a virtual file handler for the Lambda zip package
        lambda_package_zip = BytesIO(base_zip_data)

        with ZipFile(lambda_package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            add_file_to_zipfile(zip_file_handler, "refinery_main.py", str(code))
            add_file_to_zipfile(zip_file_handler, "lambda_function.py", self.lambda_function)

        lambda_package_zip_data = lambda_package_zip.getvalue()
        lambda_package_zip.close()

        return lambda_package_zip_data

    def get_zip_with_deps(self):
        s3_zip_path = get_final_zip_package_path(
            self.RUNTIME,
            self.libraries_object
        )

        build_id = self.start_codebuild()

        # This continually polls for the CodeBuild build to finish
        # Once it does it returns the raw artifact zip data.
        return self.get_codebuild_artifact_zip_data(build_id, s3_zip_path)

    def start_codebuild(self):
        """
        Returns a build ID to be polled at a later time
        """
        codebuild_client = self.aws_client_factory.get_aws_client(
            "codebuild",
            self.credentials
        )

        s3_client = self.aws_client_factory.get_aws_client(
            "s3",
            self.credentials
        )

        # Create empty zip file
        codebuild_zip = BytesIO(EMPTY_ZIP_DATA)

       with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            # Write buildspec.yml defining the build process
            add_file_to_zipfile(
                zip_file_handler,
                "buildspec.yml",
                BUILDSPEC
            )

            # Write the package.json
            add_file_to_zipfile(
                zip_file_handler,
                "requirements.txt",
                get_requirements_text(self.libraries_dict)
            )

        codebuild_zip_data = codebuild_zip.getvalue()
        codebuild_zip.close()

        # S3 object key of the build package, randomly generated.
        s3_key = "buildspecs/" + str(uuid4()) + ".zip"

        # Write the CodeBuild build package to S3
        s3_response = s3_client.put_object(
            Bucket=credentials["lambda_packages_bucket"],
            Body=codebuild_zip_data,
            Key=s3_key,
            ACL="public-read",  # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
        )

        # Fire-off the build
        codebuild_response = codebuild_client.start_build(
            projectName="refinery-builds",
            sourceTypeOverride="S3",
            imageOverride="docker.io/python:3.6.9",
            sourceLocationOverride=credentials["lambda_packages_bucket"] + "/" + s3_key,
        )

        build_id = codebuild_response["build"]["id"]
        return build_id