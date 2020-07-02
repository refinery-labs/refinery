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


class GithubListUserRepos(BaseHandler):
    dependencies = GithubListUserReposDependencies

    github_assistant = None  # type: GithubAssistant

    @gen.coroutine
    @github_authenticated
    def get( self, oauth_token, oauth_json_data ):

        repos = yield self.github_assistant.list_repos_for_user(oauth_token)
        self.write({
            "success": True,
            "repos": repos
        })

class GithubCreateNewRepoDependencies:
    @pinject.copy_args_to_public_fields
    def __init__( self, github_assistant ):
        pass


class GithubCreateNewRepo(BaseHandler):
    dependencies = GithubCreateNewRepoDependencies

    github_assistant = None  # type: GithubAssistant

    @gen.coroutine
    @github_authenticated
    def post( self, oauth_token, oauth_json_data ):
        validate_schema(self.json, GITHUB_CREATE_NEW_REPO_SCHEMA)

        repo_name = self.json["repo_name"]

        repos = yield self.github_assistant.create_new_user_repo(oauth_token, repo_name)
        self.write({
            "success": True,
            "repos": repos
        })
