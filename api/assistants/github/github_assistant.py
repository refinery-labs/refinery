import json
import os

import requests
from tornado import httpclient, gen
from tornado.httpclient import HTTPError


class GithubAssistant:
    _API_BASE_HEADERS = {
        "Accept": "application/json",
        "User-Agent": "Tornado OAuth"
    }
    _ACCESS_TOKEN_HEADER_FORMAT = "token {access_token}"
    _OAUTH_USER_REPOS_URL = "https://api.github.com/user/repos"

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
    def list_repos_for_user( self, access_token, page=0 ):
        try:
            response = yield self.http.fetch(
                # Grab 100 pages at a time and sort them by the most recently updated projects.
                self._OAUTH_USER_REPOS_URL + '?per_page=100&sort=updated&page=' + str(page),
                headers=self._get_auth_base_headers(access_token)
            )
        except HTTPError as e:
            raise Exception( "Unable to list repos for user via token from Github: " + str(e) )

        if not response:
            raise Exception( "Missing body when listing users via token from Github" )

        # TODO check exception
        parsed_response = json.loads(response.body)

        repos = []
        for repo_result in parsed_response:
            repos.append({
                "clone_url": repo_result["clone_url"],
                "description": repo_result["description"],
                "full_name": repo_result["full_name"],
                "stargazers_count": repo_result["stargazers_count"],
                "updated_at": repo_result["updated_at"],
                "private": repo_result["private"]
            })

        # Grab additional pages (pagination)
        if "Link" in response.headers:
            parsed_links = requests.utils.parse_header_links(response.headers['Link'])
            next_link = [link for link in parsed_links if link["rel"] == "next"]

            if len(next_link) > 0:
                # Recursive call with the deeper page
                # TODO: We can optimize this by grabbing the "last" page and then, in parallel, grabbing the pages.
                repos = repos + (yield self.list_repos_for_user(access_token, page + 1))

        raise gen.Return( repos )

    @gen.coroutine
    def create_new_user_repo(self, access_token, repo_name, repo_description):
        body = {
            "name": repo_name,
            "description": repo_description,
            "private": True
        }

        response = None
        try:
            response = yield self.http.fetch(
                # Grab 100 pages at a time and sort them by the most recently updated projects.
                self._OAUTH_USER_REPOS_URL,
                method="POST",
                body=json.dumps(body),
                headers=self._get_auth_base_headers(access_token)
            )
        except HTTPError as e:
            raise Exception( "Unable to create new repo for user via token from Github: " + str(e) )

        repo = json.loads(response.body)
        return repo
