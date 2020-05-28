from typing import Dict

from assistants.deployments.aws.api_endpoint import ApiEndpointWorkflowState


class ApiGatewayEndpoint:
    def __init__(self, _id, path):
        self.id = _id
        self.path = path
        self._in_use = False

        # map HTTP methods to whether or not they are in use
        self._methods: Dict[str, bool] = dict()

    def set_method_in_use(self, method):
        self._methods[method] = True

    def set_endpoint_in_use(self):
        self._in_use = True

    def get_methods_to_be_removed(self):
        return [method for method, in_use in self._methods.items() if not in_use]

    def endpoint_can_be_removed(self):
        # if all of the methods are not being used, then we can remove this
        return (not self._in_use) and (not any([in_use for in_use in self._methods.values()]))


class ApiGatewayLambdaConfig:
    def __init__(self, lambda_uri, method, path):
        self.lambda_uri = lambda_uri
        self.method = method
        self.path = path

    def matches_expected_state(self, api_endpoint: ApiEndpointWorkflowState):
        return self.method == api_endpoint.http_method and self.path == api_endpoint.api_path
