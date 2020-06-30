import pinject
from mock import MagicMock


class MockUserCreationAssistantDependencies(pinject.BindingSpec):
    @pinject.provides("github_oauth_provider")
    def provide_github_oauth_provider( self ):
        return MagicMock()

    @pinject.provides("oauth_service")
    def provide_oauth_service( self ):
        return MagicMock()

    @pinject.provides("project_inventory_service")
    def provide_project_inventory_service( self ):
        return MagicMock()

    @pinject.provides("stripe_service")
    def provide_stripe_service( self ):
        return MagicMock()

    @pinject.provides("user_management_service")
    def provide_user_management_service( self ):
        return MagicMock()
