from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from utils.general import add_file_to_zipfile

BASE_DOCKERFILE = """
FROM 623905218559.dkr.ecr.us-west-2.amazonaws.com/refinery-container-runtime AS refinery-container-runtime

{user_dockerfile}

COPY --from=refinery-container-runtime /var/runtime/bootstrap /var/runtime/bootstrap
COPY --from=refinery-container-runtime /var/runtime/handlers /var/runtime/handlers

ENTRYPOINT [ "/var/runtime/bootstrap" ]
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

    def build_dockerfile(self, zipfile):
        dockerfile = BASE_DOCKERFILE.format(self.user_dockerfile)
        add_file_to_zipfile(zipfile, "Dockerfile", dockerfile)
