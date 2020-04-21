import json

from tornado import httpclient, gen
from tornado.httpclient import HTTPError

from controller.auth.github.utils import decode_response_body


class GithubAssistant:
    _API_BASE_HEADERS = {
        "Accept": "application/json",
        "User-Agent": "Tornado OAuth"
    }
    _ACCESS_TOKEN_HEADER_FORMAT = "token {access_token}"
    _OAUTH_LIST_USER_URL = "https://api.github.com/user/repos"

    def __init__(self, logger):
        self.logger = logger

        # TODO: Allow this to be stubbed via the constructor
        self.http = httpclient.AsyncHTTPClient()

    def _get_auth_base_headers( self, access_token ):
        base_headers = self._API_BASE_HEADERS
        base_headers["Authorization"] = self._ACCESS_TOKEN_HEADER_FORMAT.format(access_token=access_token)
        return base_headers

    # https://developer.github.com/v3/repos/#list-repositories-for-the-authenticated-user
    @gen.coroutine
    def list_repos_for_user( self, access_token ):
        try:
            response = yield self.http.fetch(
                self._OAUTH_LIST_USER_URL,
                headers=self._get_auth_base_headers(access_token)
            )
        except HTTPError as e:
            raise Exception( "Unable to list repos for user via token from Github", data=e )

        if not response:
            raise Exception( "Missing body when listing users via token from Github" )

        # TODO check exception
        parsed_response = json.loads(response.body)

        repos = []
        for repo_result in parsed_response:
            repos.append({
                "clone_url": repo_result["clone_url"],
                "full_name": repo_result["full_name"]
            })

        raise gen.Return( repos )
