import inspect
from controller.decorators import authenticated
from controller.github.github_utils import get_existing_github_oauth_user_data, CorruptGithubOauthDataException


def github_authenticated(allow_unauth=False):
    """
    Decorator to grab the current user's github auth data

    If the user is not, the response will be:
    {
            "success": false,
            "code": "MISSING_GITHUB_OAUTH",
            "msg": "...",
    }
    """
    def github_authenticated_func(func):
        def wrapper(*args, **kwargs):
            self_reference = args[0]

            try:
                auth_data = get_existing_github_oauth_user_data(
                    self_reference.dbsession,
                    self_reference.logger,
                    self_reference.get_authenticated_user_id()
                )
            except CorruptGithubOauthDataException as e:
                self_reference.write({
                    "success": False,
                    "code": "CORRUPT_OAUTH_STATE",
                    "msg": "Github OAuth is in a corrupt state for this account",
                })
                return

            if auth_data is None:
                if allow_unauth:
                    kwargs['oauth_token'] = None
                    kwargs['oauth_json_data'] = None
                    return func(*args, **kwargs)

                self_reference.write({
                    "success": False,
                    "code": "AUTH_REQUIRED",
                    "msg": "Github OAuth has not been enabled for this account",
                })
                return

            oauth_token, oauth_json_data = auth_data

            func_parameters = inspect.signature(func).parameters

            if 'oauth_token' in func_parameters:
                kwargs['oauth_token'] = str(oauth_token)

            if 'oauth_json_data' in func_parameters:
                kwargs['oauth_json_data'] = oauth_json_data

            return func(*args, **kwargs)

        if allow_unauth:
            return wrapper
        return authenticated(wrapper)

    return github_authenticated_func
