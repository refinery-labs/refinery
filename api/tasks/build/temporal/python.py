from yaml import dump

from pyconstants.project_constants import PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME, EMPTY_ZIP_DATA, LANGUAGE_TO_RUNTIME
from tasks.build.temporal.language_builder import LanguageBuilder
from utils.block_libraries import generate_libraries_dict, get_requirements_text


PYTHON_BUILDSPEC = dump({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "build": {
            "commands": [
                "pip install --target . -r requirements.txt" ]
        },
    },
    "run-as": "root",
    "version": 0.1
})


class PythonBuilder(LanguageBuilder):
    RUNTIME = "python3.6"
    RUNTIME_PRETTY_NAME = PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME
    BUILDSPEC = PYTHON_BUILDSPEC
    IMAGE_OVERRIDE = "docker.io/python:3.6.9"

    def add_files_to_build_package(self, file_map, code):
        file_map["__init__.py"] = ""
        file_map["refinery_main.py"] = code
        file_map["lambda_function.py"] = self.lambda_function

        handler_code = self.container_runtime

        file_map["container_lambda_function.py"] = handler_code

    def add_files_to_codebuild_package(self, filemap, libraries_object):
            filemap["requirements.txt"] = get_requirements_text(libraries_object)
