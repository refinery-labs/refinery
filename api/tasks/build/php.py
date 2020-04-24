from copy import deepcopy
from io import BytesIO
from pyconstants.project_constants import EMPTY_ZIP_DATA
from re import sub
from tasks.build.common import get_final_zip_package_path, get_codebuild_artifact_zip_data
from uuid import uuid4
from yaml import dump
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from tasks.s3 import s3_object_exists, read_from_s3


def get_php73_lambda_base_zip(aws_client_factory, credentials, libraries):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    libraries_object = {}
    for library in libraries:
        libraries_object[str(library)] = "latest"

    final_s3_package_zip_path = get_final_zip_package_path(
        "php7.3",
        libraries_object
    )

    if s3_object_exists(aws_client_factory, credentials, credentials["lambda_packages_bucket"], final_s3_package_zip_path):
        return read_from_s3(
            aws_client_factory,
            credentials,
            credentials["lambda_packages_bucket"],
            final_s3_package_zip_path
        )

    # Kick off CodeBuild for the libraries to get a zip artifact of
    # all of the libraries.
    build_id = start_php73_codebuild(
        aws_client_factory,
        credentials,
        libraries_object
    )
# This continually polls for the CodeBuild build to finish
    # Once it does it returns the raw artifact zip data.
    return get_codebuild_artifact_zip_data(
        aws_client_factory,
        credentials,
        build_id,
        final_s3_package_zip_path
    )


def start_php73_codebuild(aws_client_factory, credentials, libraries_object):
    """
    Returns a build ID to be polled at a later time
    """
    codebuild_client = aws_client_factory.get_aws_client(
        "codebuild",
        credentials
    )

    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    commands = []

    for key, value in libraries_object.iteritems():
        commands.append(
            "composer require " + key
        )

    # Create empty zip file
    codebuild_zip = BytesIO(EMPTY_ZIP_DATA)

    buildspec_template = {
        "artifacts": {
            "files": [
                "**/*"
            ]
        },
        "phases": {
            "build": {
                "commands": commands
            },
            "install": {
                "runtime-versions": {
                    "php": 7.3
                }
            }
        },
        "version": 0.2
    }

    with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
        # Write buildspec.yml defining the build process
        buildspec = ZipInfo(
            "buildspec.yml"
        )
        buildspec.external_attr = 0777 << 16L
        zip_file_handler.writestr(
            buildspec,
            dump(
                buildspec_template
            )
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
        sourceLocationOverride=credentials["lambda_packages_bucket"] + "/" + s3_key,
    )

    build_id = codebuild_response["build"]["id"]

    return build_id

def get_php_73_base_code(app_config, code):
    code = sub(
        r"function main\([^\)]+\)[^{]\{",
        "function main( $block_input ) {global $backpack;",
        code
    )

    code = code.replace(
        "require __DIR__",
        "require $_ENV[\"LAMBDA_TASK_ROOT\"]"
    )

    code = code + "\n\n" + app_config.get("LAMDBA_BASE_CODES")["php7.3"]
    return code


def build_php_73_lambda(app_config, aws_client_factory, credentials, code, libraries):
    code = get_php_73_base_code(
        app_config,
        code
    )

    # Use CodeBuilder to get a base zip of the libraries
    base_zip_data = deepcopy(EMPTY_ZIP_DATA)
    if len(libraries) > 0:
        base_zip_data = get_php73_lambda_base_zip(
            aws_client_factory,
            credentials,
            libraries
        )

    # Create a virtual file handler for the Lambda zip package
    lambda_package_zip = BytesIO(base_zip_data)

    with ZipFile(lambda_package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
        info = ZipInfo(
            "lambda"
        )
        info.external_attr = 0777 << 16L

        # Write lambda.php into new .zip
        zip_file_handler.writestr(
            info,
            str(code)
        )

    lambda_package_zip_data = lambda_package_zip.getvalue()
    lambda_package_zip.close()

    return lambda_package_zip_data


