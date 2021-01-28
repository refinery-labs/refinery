from io import BytesIO
from json import dumps
from zipfile import ZIP_DEFLATED, ZipFile

from utils.general import add_file_to_zipfile

BUILDSPEC = dumps({
    "artifacts": {
        "files": [
            "**/*"
        ]
    },
    "phases": {
        "install": {
            "commands": []
        },
        "build": {
            "commands": [
                "docker build . -t app",
                "docker tag app $DOCKER_REPOSITORY_URL",
                "aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $DOCKER_REGISTRY_URI",
                "docker push $DOCKER_REPOSITORY_URL"
            ]
        },
    },
    "run-as": "root",
    "version": 0.1
})

BASE_DOCKERFILE = """
FROM 134071937287.dkr.ecr.us-west-2.amazonaws.com/refinery-container-runtime AS refinery-container-runtime

{user_dockerfile}

COPY --from=refinery-container-runtime /var/runtime /var/runtime/

ENTRYPOINT ["/var/runtime/bootstrap"]
CMD []
"""

class DockerEnvBuilder:
    def __init__(self, app_config, project_id, user_dockerfile):
        self.app_config = app_config
        self.project_id = project_id
        self.user_dockerfile = user_dockerfile

    ###########################################################################
    # High level builder stuff
    ###########################################################################

    def build(self, buffer=None):
        if buffer is not None:
            self._build(buffer)

            return buffer.getvalue()

        with BytesIO() as buffer:
            self._build(buffer)
            return buffer.getvalue()

    def _build(self, buffer):
        with ZipFile(buffer, 'w', ZIP_DEFLATED) as zipfile:
            self.build_dockerfile(zipfile)
            self.add_buildspec(zipfile)

    def build_dockerfile(self, zipfile):
        dockerfile = BASE_DOCKERFILE.format(self.user_dockerfile)
        add_file_to_zipfile(zipfile, "Dockerfile", dockerfile)

    def add_buildspec(self, zipfile):
        add_file_to_zipfile(zipfile, "buildspec.yml", BUILDSPEC)
