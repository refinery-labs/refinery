import json

from tornado import httpclient, gen
from tornado.httpclient import HTTPError


class PigeonService:
    _API_BASE_HEADERS = {
    }
    _PIGEON_CREATE_WORKFLOWS_PATH = "deployment"

    def __init__(self, logger, app_config):
        self.logger = logger
        self.workflow_manager_api_url = app_config.get("workflow_manager_api_url")

        # TODO: Allow this to be stubbed via the constructor
        self.http = httpclient.AsyncHTTPClient()

    @gen.coroutine
    def create_workflows_for_deployment(self, serialized_deployment):
        try:
            response = yield self.http.fetch(
                f"{self.workflow_manager_api_url}/{self._PIGEON_CREATE_WORKFLOWS_PATH}",
                headers={"Content-Type": "application/json"},
                method="POST",
                body=json.dumps(serialized_deployment)
            )
        except HTTPError as e:
            raise Exception("Unable to create Pigeon workflows: " + str(e))

        parsed_response = json.loads(response.body)
        if not parsed_response["success"]:
            raise Exception("Unable to create Pigeon workflows: " + parsed_response["error"])

    @gen.coroutine
    def delete_deployment_workflows(self, deployment_id):
        try:
            response = yield self.http.fetch(
                f"{self.workflow_manager_api_url}/{self._PIGEON_CREATE_WORKFLOWS_PATH}/{deployment_id}",
                method="DELETE",
            )
        except HTTPError as e:
            raise Exception("Unable to delete Pigeon workflows: " + str(e))

        parsed_response = json.loads(response.body)
        if not parsed_response["success"]:
            raise Exception("Unable to delete Pigeon workflows: " + parsed_response["error"])
