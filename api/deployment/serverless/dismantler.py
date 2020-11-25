from deployment.base import Dismantler
from functools import cached_property
from tasks.build.common import wait_for_codebuild_completion
from yaml import dump


BUILDSPEC = dump({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "build": {
            "commands": [
                "serverless remove"
            ]
        },
    },
    "run-as": "root",
    "version": 0.1
})


class ServerlessDismantler(Dismantler):
    def __init__(self, app_config, aws_client_factory, s3_path):
        self.app_config = app_config
        self.aws_client_factory = aws_client_factory
        self.s3_path = s3_path

    @cached_property
    def codebuild(self):
        return self.aws_client_factory.get_aws_client(
            "codebuild",
            self.credentials
        )

    def dismantle(self):
        build_id = self.codebuild.start_build(
            projectName='refinery-serverless-teardowns',
            sourceTypeOverride='s3',
            sourceLocationOverride=self.s3_path,
            imageOverride="aws/codebuild/nodejs:12"
        )['build']['id']

        wait_for_codebuild_completion(
            self.aws_client_factory,
            self.credentials,
            build_id
        )
