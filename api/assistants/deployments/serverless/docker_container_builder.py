from io import BytesIO
from zipfile import ZIP_STORED, ZipFile


class DockerContainerBuilder:
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
        with ZipFile(buffer, 'w', ZIP_STORED) as zipfile:
            pass

