import os
from abc import abstractmethod, ABC
from json import dumps
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pinject

from assistants.aws_clients.aws_clients_assistant import AwsClientFactory
from config.app_config import AppConfig
from pyconstants.project_constants import CONTAINER_LANGUAGE, LAMBDA_TEMPORAL_RUNTIMES
from tasks.build.common import get_final_zip_package_path, get_codebuild_artifact_zip_data
from tasks.s3 import s3_object_exists, read_from_s3
from utils.block_libraries import generate_libraries_dict
from io import BytesIO

from utils.general import add_file_to_zipfile


class LanguageBuilder(ABC):
    RUNTIME = None
    BUILDSPEC = None
    IMAGE_OVERRIDE = None

    app_config: AppConfig = None
    aws_client_factory: AwsClientFactory = None

    @pinject.copy_args_to_public_fields
    def __init__(self, app_config, aws_client_factory):
        pass

    @property
    def lambda_function(self):
        return self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")[self.RUNTIME]

    @property
    def container_runtime(self):
        return self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")[CONTAINER_LANGUAGE + self.RUNTIME]

    @abstractmethod
    def add_files_to_build_package(self, filemap, code):
        pass

    def build(self, credentials, code, libraries, file_map):
        libraries_object = generate_libraries_dict(libraries)
        zip_with_deps = self.get_zip_with_deps(credentials, libraries_object)

        # Create a virtual file handler for the Lambda zip package
        package_zip = BytesIO(zip_with_deps)

        # with ZipFile(package_zip, 'w') as _:
        #     pass

        with ZipFile(package_zip, "r") as zip_file_handler:
            for filename in zip_file_handler.namelist():
                file_map[filename] = zip_file_handler.read(filename)

        self.add_files_to_build_package(file_map, code)

        package_zip.close()

        # make sure all content is a bytes-like type
        for filepath, content in file_map.items():
            if type(content) is str:
                file_map[filepath] = content.encode()

    def get_zip_with_deps(self, credentials, libraries_object):
        if len(libraries_object) == 0:
            return b''

        s3_zip_path = get_final_zip_package_path(self.RUNTIME, libraries_object)
        exists = s3_object_exists(
            self.aws_client_factory,
            credentials,
            credentials["lambda_packages_bucket"],
            s3_zip_path
        )

        if exists:
            return read_from_s3(
                self.aws_client_factory,
                credentials,
                credentials["lambda_packages_bucket"],
                s3_zip_path
            )

        # Kick off CodeBuild for the libraries to get a zip artifact of
        # all of the libraries.
        build_id = self.start_codebuild(credentials, libraries_object)

        # This continually polls for the CodeBuild build to finish
        # Once it does it returns the raw artifact zip data.
        return get_codebuild_artifact_zip_data(
            self.aws_client_factory,
            credentials,
            build_id,
            s3_zip_path
        )

    @abstractmethod
    def add_files_to_codebuild_package(self, filemap, libraries_object):
        pass

    def start_codebuild(self, credentials, libraries_object):
        """
        Returns a build ID to be polled at a later time
        """
        codebuild_client = self.aws_client_factory.get_aws_client(
            "codebuild",
            credentials
        )

        s3_client = self.aws_client_factory.get_aws_client(
            "s3",
            credentials
        )

        # Create empty zip file
        codebuild_zip = BytesIO()

        with ZipFile(codebuild_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            # Write buildspec.yml defining the build process
            filemap = {
                "buildspec.yml": self.BUILDSPEC
            }

            self.add_files_to_codebuild_package(filemap, libraries_object)

            for filename, contents in filemap.items():
                add_file_to_zipfile(zip_file_handler, filename, contents)

        codebuild_zip_data = codebuild_zip.getvalue()
        codebuild_zip.close()

        # S3 object key of the build package, randomly generated.
        s3_key = "buildspecs/{}.zip".format(str(uuid4()))

        # Write the CodeBuild build package to S3
        s3_client.put_object(
            Bucket=credentials["lambda_packages_bucket"],
            Body=codebuild_zip_data,
            Key=s3_key,
            ACL="public-read",  # THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
        )

        # Fire-off the build
        codebuild_response = codebuild_client.start_build(
            projectName="refinery-builds",
            sourceTypeOverride="S3",
            sourceLocationOverride="{}/{}".format(credentials["lambda_packages_bucket"], s3_key),
            imageOverride=self.IMAGE_OVERRIDE
        )

        build_id = codebuild_response["build"]["id"]
        return build_id
