from copy import deepcopy
from io import BytesIO
from json import dumps

import yaml

from pyconstants.project_constants import EMPTY_ZIP_DATA
from re import sub
from tasks.build.common import get_final_zip_package_path, get_codebuild_artifact_zip_data
from tasks.s3 import s3_object_exists, read_from_s3
from uuid import uuid4
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from utils.block_libraries import generate_libraries_dict


def start_node810_codebuild(aws_client_factory, credentials, libraries_object):
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

    package_json_template = {
        "name": "refinery-lambda",
        "version": "1.0.0",
        "description": "Lambda created by Refinery",
        "main": "main.js",
        "dependencies": libraries_object,
        "devDependencies": {},
        "scripts": {}
    }

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
                "commands": [
                    "npm install"
                ]
            },
            "install": {
                "runtime-versions": {
                    "nodejs": 8
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
        buildspec.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            buildspec,
            yaml.dump(
                buildspec_template
            )
        )

        print(dumps(
            package_json_template
        ))

        # Write the package.json
        package_json = ZipInfo("package.json")
        package_json.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            package_json,
            dumps(
                package_json_template
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


def get_nodejs_810_lambda_base_zip(aws_client_factory, credentials, libraries):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    libraries_object = generate_libraries_dict(libraries)

    final_s3_package_zip_path = get_final_zip_package_path(
        "nodejs8.10",
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
    build_id = start_node810_codebuild(
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


def get_nodejs_810_base_code(app_config, code):
    code = sub(
        r"function main\([^\)]+\)[^{]\{",
        "function main( blockInput ) {",
        code
    )

    code = sub(
        r"function mainCallback\([^\)]+\)[^{]\{",
        "function mainCallback( blockInput, callback ) {",
        code
    )

    code = code + "\n\n" + \
        app_config.get("LAMDBA_BASE_CODES")["nodejs8.10"]

    return code


def build_nodejs_810_lambda(app_config, aws_client_factory, credentials, code, libraries):
    code = get_nodejs_810_base_code(
        app_config,
        code
    )

    # Use CodeBuilder to get a base zip of the libraries
    base_zip_data = deepcopy(EMPTY_ZIP_DATA)
    if len(libraries) > 0:
        base_zip_data = get_nodejs_810_lambda_base_zip(
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
        info.external_attr = 0o777 << 16

        # Write lambda.py into new .zip
        zip_file_handler.writestr(
            info,
            str(code)
        )

    lambda_package_zip_data = lambda_package_zip.getvalue()
    lambda_package_zip.close()

    return lambda_package_zip_data


def get_nodejs_10163_base_code(app_config, code):
    code = sub(
        r"function main\([^\)]+\)[^{]\{",
        "function main( blockInput ) {",
        code
    )

    code = sub(
        r"function mainCallback\([^\)]+\)[^{]\{",
        "function mainCallback( blockInput, callback ) {",
        code
    )

    code = code + "\n\n" + \
        app_config.get("LAMDBA_BASE_CODES")["nodejs10.16.3"]
    return code


def build_nodejs_10163_lambda(app_config, aws_client_factory, credentials, code, libraries):
    code = get_nodejs_10163_base_code(
        app_config,
        code
    )

    # Use CodeBuilder to get a base zip of the libraries
    base_zip_data = deepcopy(EMPTY_ZIP_DATA)
    if len(libraries) > 0:
        base_zip_data = get_nodejs_10163_lambda_base_zip(
            aws_client_factory,
            credentials,
            libraries
        )

    # Create a virtual file handler for the Lambda zip package
    lambda_package_zip = BytesIO(base_zip_data)

    with ZipFile(lambda_package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
        info = ZipInfo("lambda")
        info.external_attr = 0o777 << 16

        # Write lambda.py into new .zip
        zip_file_handler.writestr(
            info,
            str(code)
        )

    lambda_package_zip_data = lambda_package_zip.getvalue()
    lambda_package_zip.close()

    return lambda_package_zip_data


def get_nodejs_10163_lambda_base_zip(aws_client_factory, credentials, libraries):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    libraries_object = generate_libraries_dict(libraries)

    # TODO we should deprecate 10163, this is a temporary fix for a known bug fixed upstream
    final_s3_package_zip_path = get_final_zip_package_path(
        "nodejs10.20.1",
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
    build_id = start_node10163_codebuild(
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


def start_node10163_codebuild(aws_client_factory, credentials, libraries_object):
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

    package_json_template = {
        "name": "refinery-lambda",
        "version": "1.0.0",
        "description": "Lambda created by Refinery",
        "main": "main.js",
        "dependencies": libraries_object,
        "devDependencies": {},
        "scripts": {}
    }

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
    }

    with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
        # Write buildspec.yml defining the build process
        buildspec = ZipInfo(
            "buildspec.yml"
        )
        buildspec.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            buildspec,
            yaml.dump(
                buildspec_template
            )
        )

        # Write the package.json
        package_json = ZipInfo(
            "package.json"
        )
        package_json.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            package_json,
            dumps(
                package_json_template
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


def get_nodejs_10201_base_code(app_config, code):
    code = sub(
        r"function main\([^\)]+\)[^{]\{",
        "function main( blockInput ) {",
        code
    )

    code = sub(
        r"function mainCallback\([^\)]+\)[^{]\{",
        "function mainCallback( blockInput, callback ) {",
        code
    )

    code = code + "\n\n" + app_config.get("LAMDBA_BASE_CODES")["nodejs10.20.1"]
    return code


def build_nodejs_10201_lambda(app_config, aws_client_factory, credentials, code, libraries):
    code = get_nodejs_10201_base_code(
        app_config,
        code
    )

    # Use CodeBuilder to get a base zip of the libraries
    base_zip_data = deepcopy(EMPTY_ZIP_DATA)
    if len(libraries) > 0:
        base_zip_data = get_nodejs_10201_lambda_base_zip(
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
        info.external_attr = 0o777 << 16

        # Write lambda.py into new .zip
        zip_file_handler.writestr(
            info,
            str(code)
        )

    lambda_package_zip_data = lambda_package_zip.getvalue()
    lambda_package_zip.close()

    return lambda_package_zip_data


def get_nodejs_10201_lambda_base_zip(aws_client_factory, credentials, libraries):
    s3_client = aws_client_factory.get_aws_client(
        "s3",
        credentials
    )

    libraries_object = generate_libraries_dict(libraries)

    final_s3_package_zip_path = get_final_zip_package_path(
        "nodejs10.16.3",
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
    build_id = start_node10201_codebuild(
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


def start_node10201_codebuild(aws_client_factory, credentials, libraries_object):
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

    package_json_template = {
        "name": "refinery-lambda",
        "version": "1.0.0",
        "description": "Lambda created by Refinery",
        "main": "main.js",
        "dependencies": libraries_object,
        "devDependencies": {},
        "scripts": {}
    }

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
    }

    with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
        # Write buildspec.yml defining the build process
        buildspec = ZipInfo(
            "buildspec.yml"
        )
        buildspec.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            buildspec,
            yaml.dump(
                buildspec_template
            )
        )

        # Write the package.json
        package_json = ZipInfo(
            "package.json"
        )
        package_json.external_attr = 0o777 << 16
        zip_file_handler.writestr(
            package_json,
            dumps(
                package_json_template
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
