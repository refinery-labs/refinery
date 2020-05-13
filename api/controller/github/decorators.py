import inspect
import json

from controller.decorators import authenticated
from controller.github.github_utils import get_existing_github_oauth_user_data


def github_authenticated(func):
    """
    Decorator to grab the current user's github auth data

    If the user is not, the response will be:
    {
            "success": false,
            "code": "MISSING_GITHUB_OAUTH",
            "msg": "...",
    }
    """
    @authenticated
    def wrapper(*args, **kwargs):
        self_reference = args[0]

        oauth_token, oauth_json_data = get_existing_github_oauth_user_data(
            self_reference.dbsession,
            self_reference.logger,
            self_reference.get_authenticated_user_id()
        )

        if oauth_json_data is None or oauth_token is None:
            self_reference.write({
                "success": False,
                "code": "AUTH_REQUIRED",
                "msg": "Github OAuth has not been enabled for this account",
            })
            return

        func_parameters = inspect.signature(func).parameters

        if 'oauth_token' in func_parameters:
            kwargs['oauth_token'] = str(oauth_token)

        if 'oauth_json_data' in func_parameters:
            kwargs['oauth_json_data'] = oauth_json_data

        return func(*args, **kwargs)

    return wrapper
