import pinject
from tornado import gen
from jsonschema import validate as validate_schema

from assistants.github.github_assistant import GithubAssistant
from controller.base import BaseHandler
from controller.github.decorators import github_authenticated
from controller.github.schemas import GITHUB_CREATE_NEW_REPO_SCHEMA


class GithubListUserReposDependencies:
    @pinject.copy_args_to_public_fields
    def __init__( self, github_assistant ):
        pass


class GithubUserRepos(BaseHandler):
    dependencies = GithubListUserReposDependencies

    github_assistant = None  # type: GithubAssistant

    @gen.coroutine
    @github_authenticated(allow_unauth=False)
    def get( self, oauth_token, oauth_json_data ):

        repos = yield self.github_assistant.list_repos_for_user(oauth_token)
        self.write({
            "success": True,
            "repos": repos
        })

    @gen.coroutine
    @github_authenticated(allow_unauth=False)
    def post( self, oauth_token, oauth_json_data ):
        validate_schema(self.json, GITHUB_CREATE_NEW_REPO_SCHEMA)

        repo_name = self.json["name"]
        repo_description = self.json["description"]

        try:
            repo = yield self.github_assistant.create_new_user_repo(oauth_token, repo_name, repo_description)
        except Exception as e:
            self.logger("Error when creating a new user repo: " + str(e), "error")
            self.write({
                "success": False
            })
            raise gen.Return()

        self.write({
            "success": True,
            "repo": repo
        })
