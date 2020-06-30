import pinject
from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated
from controller.projects import CREATE_GIT_REPO_SCHEMA
from models import GitRepoModel
from assistants.github.oauth_provider import GithubOAuthProvider


class CreateGitRepoDependencies:
    @pinject.copy_args_to_public_fields
    def __init__(self, github_oauth_provider):
        pass


class CreateGitRepo(BaseHandler):
    dependencies = CreateGitRepoDependencies
    github_oauth_provider = None  # type: GithubOAuthProvider

    @authenticated
    @gen.coroutine
    def post(self):
        """
        Adds a new Git Repo to the database
        """
        validate_schema(self.json, CREATE_GIT_REPO_SCHEMA)

        user = self.get_authenticated_user()

        git_repo_id = self.json['git_repo_id']

        new_project_shortlink = GitRepoModel(user.organization_id, )
        new_project_shortlink.project_json = self.json["diagram_data"]
        self.dbsession.add(new_project_shortlink)
        self.dbsession.commit()

        self.write({
            "success": True,
            "msg": "Project short link created successfully!",
            "result": {
                "project_short_link_id": new_project_shortlink.short_id
            }
        })
