import pinject
from mock import MagicMock


class MockGithubDependenciesHolder:
    aws_cost_explorer = None

    @pinject.copy_args_to_public_fields
    def __init__(
            self,
            github_oauth_provider,
            user_creation_assistant
    ):
        pass


class MockGithubDependencies(pinject.BindingSpec):
    @pinject.provides("github_oauth_provider")
    def provide_github_oauth_provider( self ):
        return MagicMock()

    @pinject.provides("user_creation_assistant")
    def provide_user_creation_assistant( self ):
        return MagicMock()
