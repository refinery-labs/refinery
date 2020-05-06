import pinject
from tornado import gen

from assistants.github.github_assistant import GithubAssistant
from controller.base import BaseHandler
from controller.github.decorators import github_authenticated


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
