from deployment.serverless.config_builder import ServerlessConfigBuilder
from functools import cached_property
from io import BytesIO
from os.path import join
from pyconstants.project_constants import PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME
from pyconstants.project_constants import NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME
from utils.general import add_file_to_zipfile
from yaml import dump
from zipfile import ZIP_DEFLATED, ZipFile


BUILDSPEC = dump({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "install": {
            "commands": [
                "npm install -g serverless"
            ]
        },
        "build": {
            "commands": [
                "serverless deploy --stage prod",
                "serverless info -v --stage prod > serverless_info"
            ]
        },
    },
    "run-as": "root",
    "version": 0.1
})


class ServerlessModuleBuilder:
    def __init__(self, app_config, project_id, deployment_id, diagram_data):
        self.app_config = app_config
        self.project_id = project_id
        self.deployment_id = deployment_id
        self.diagram_data = diagram_data

    ###########################################################################
    # High level builder stuff
    ###########################################################################

    @cached_property
    def workflow_state_builders(self):
        return {
            "lambda": self.build_lambda,
            "sqs_queue": self.build_sqs_queue
        }

    def build(self, buffer=None):
        if buffer is not None:
            self._build(buffer)

            return buffer.getvalue()

        with BytesIO() as buffer:
            self._build(buffer)
            return buffer.getvalue()

    def _build(self, buffer):
        with ZipFile(buffer, 'w', ZIP_DEFLATED) as zipfile:
            self.build_workflow_states(zipfile)
            self.build_config(zipfile)
            self.add_buildspec(zipfile)

    def build_config(self, zipfile):
        builder = ServerlessConfigBuilder(
            self.app_config,
            self.project_id,
            self.deployment_id,
            self.diagram_data
        )
        serverless_yaml = builder.build()

        add_file_to_zipfile(zipfile, "serverless.yml", serverless_yaml)

    def build_workflow_states(self, zipfile):
        for workflow_state in self.diagram_data['workflow_states']:
            type_ = workflow_state['type']
            builder = self.workflow_state_builders.get(type_)

            if builder:
                builder(workflow_state, zipfile)

    def add_buildspec(self, zipfile):
        add_file_to_zipfile(zipfile, "buildspec.yml", BUILDSPEC)

    ###########################################################################
    # Lambda builder
    ###########################################################################

    @cached_property
    def lambda_builders(self):
        return {
            PYTHON_36_TEMPORAL_RUNTIME_PRETTY_NAME: self.build_python,
            NODEJS_10_TEMPORAL_RUNTIME_PRETTY_NAME: self.build_nodejs
        }

    def build_lambda(self, workflow_state, zipfile):
        language = workflow_state['language']
        builder = self.lambda_builders[language]

        builder(workflow_state, zipfile)

    def build_python(self, workflow_state, zipfile):
        id_ = workflow_state['id']
        code = workflow_state['code']
        lambda_fn = self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")['python3.6']

        add_file_to_zipfile(zipfile, self.get_path(id_, "refinery_main.py"), code)
        add_file_to_zipfile(zipfile, self.get_path(id_, "lambda_function.py"), lambda_fn)

    def build_nodejs(self, workflow_state, zipfile):
        id_ = workflow_state['id']
        code = workflow_state['code']
        lambda_fn = self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")['nodejs10.x']

        add_file_to_zipfile(zipfile, self.get_path(id_, "refinery_main.js"), code)
        add_file_to_zipfile(zipfile, self.get_path(id_, "index.js"), lambda_fn)

    def get_path(self, id_, path):
        id_ = ''.join([i for i in id_ if i.isalnum()])

        return join(f'lambda/{id_}', path)

    ###########################################################################
    # SQS builder
    ###########################################################################

    def build_sqs_queue(self, workflow_state, zipfile):
        lambda_fn = self.app_config.get("LAMBDA_TEMPORAL_RUNTIMES")['sqs_notifier']

        add_file_to_zipfile(zipfile, "lambda/queue/index.js", lambda_fn)
