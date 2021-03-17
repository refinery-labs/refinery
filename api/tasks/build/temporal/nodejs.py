from json import dumps

from yaml import dump

from pyconstants.project_constants import NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME
from tasks.build.temporal.language_builder import LanguageBuilder

NODEJS_BUILDSPEC = dump({
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


class NodeJsBuilder(LanguageBuilder):
    RUNTIME = "nodejs10.x"
    RUNTIME_PRETTY_NAME = NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME
    BUILDSPEC = NODEJS_BUILDSPEC
    IMAGE_OVERRIDE = "docker.io/nodejs:12"

    def add_files_to_build_package(self, filemap, code):
        filemap["refinery_main.js"] = code
        filemap["index.js"] = self.lambda_function

        handler_code = self.container_runtime

        filemap["container_lambda_function.js"] = handler_code

    def add_files_to_codebuild_package(self, filemap, libraries_object):
        package_json = {
            "name": "refinery-lambda",
            "version": "1.0.0",
            "description": "Lambda created by Refinery",
            "main": "index.js",
            "dependencies": libraries_object,
            "devDependencies": {},
            "scripts": {}
        }

        filemap["package.json"] = dumps(package_json)
