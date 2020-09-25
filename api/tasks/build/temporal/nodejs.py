from io import BytesIO
from json import dumps
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from yaml import dump

from pyconstants.project_constants import NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME
from tasks.build.common import get_codebuild_artifact_zip_data, get_final_zip_package_path
from tasks.s3 import read_from_s3, s3_object_exists
from utils.block_libraries import generate_libraries_dict
from utils.general import add_file_to_zipfile

BUILDSPEC = dump({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "build": {
            "commands": [
                "npm install"
            ]
        },
        "install": {
            "runtime-versions": {
                "nodejs": 10
            }
        }
    },
    "version": 0.2
})


class NodeJs12Builder:
    RUNTIME = "nodejs10.x"
    RUNTIME_PRETTY_NAME = NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME

    def __init__(self, app_config, aws_client_factory, credentials, code, libraries):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.credentials = credentials
        self.code = code
        self.libraries = libraries
        self.libraries_object = generate_libraries_dict(self.libraries)

    @property
    def lambda_function(self):
        return self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")[self.RUNTIME]

    def build(self):
        # Create a virtual file handler for the Lambda zip package
        package_zip = BytesIO(self.get_zip())

        with ZipFile(package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            add_file_to_zipfile(zip_file_handler, "refinery_main.js", self.code)
            add_file_to_zipfile(zip_file_handler, "index.js", self.lambda_function)

        zip_data = package_zip.getvalue()
        package_zip.close()

        return zip_data

    def get_zip(self):
        if len(self.libraries) == 0:
            return b''

        s3_zip_path = get_final_zip_package_path(self.RUNTIME, self.libraries_object)
        exists = s3_object_exists(
            self.aws_client_factory,
            self.credentials,
            self.credentials["lambda_packages_bucket"],
            s3_zip_path
        )

        if exists:
            return read_from_s3(
                self.aws_client_factory,
                self.credentials,
                self.credentials["lambda_packages_bucket"],
                s3_zip_path
            )

        # Kick off CodeBuild for the libraries to get a zip artifact of
        # all of the libraries.
        build_id = self.start_codebuild()

        # This continually polls for the CodeBuild build to finish
        # Once it does it returns the raw artifact zip data.
        return get_codebuild_artifact_zip_data(
            self.aws_client_factory,
            self.credentials,
            build_id,
            s3_zip_path
        )

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

        package_json = {
            "name": "refinery-lambda",
            "version": "1.0.0",
            "description": "Lambda created by Refinery",
            "main": "index.js",
            "dependencies": self.libraries_object,
            "devDependencies": {},
            "scripts": {}
        }

        # Create empty zip file
        codebuild_zip = BytesIO()

        with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            # Write buildspec.yml defining the build process
            add_file_to_zipfile(zip_file_handler, "buildspec.yml", BUILDSPEC)
            add_file_to_zipfile(zip_file_handler, "package.json", dumps(package_json))

        codebuild_zip_data = codebuild_zip.getvalue()
        codebuild_zip.close()

        # S3 object key of the build package, randomly generated.
        s3_key = "buildspecs/{}.zip".format(str(uuid4()))

        # Write the CodeBuild build package to S3
        s3_client.put_object(
            Bucket=self.credentials["lambda_packages_bucket"],
            Body=codebuild_zip_data,
            Key=s3_key,
            ACL="public-read",  # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
        )

        # Fire-off the build
        codebuild_response = codebuild_client.start_build(
            projectName="refinery-builds",
            sourceTypeOverride="S3",
            sourceLocationOverride="{}/{}".format(self.credentials["lambda_packages_bucket"], s3_key)
        )

        build_id = codebuild_response["build"]["id"]
        return build_id
