import json

from sqlalchemy.orm import Session

from models import UserOAuthAccountModel
from utils.general import logit


def get_existing_github_oauth_user_data(dbsession, logger, user_id):
    # type: (Session, logit, basestring) -> ((str, dict) or None)
    """
    Retrieves the latest copy of a User's OAuth Github data.
    :param dbsession: Existing DBSession
    :param logger: Instance of logger to call on errors
    :param user_id: The Refinery User's ID to look for existing Github data for
    :return: Instance of the user's oauth_data_record (if it exists), else None
    """
    user_oauth_account = dbsession.query( UserOAuthAccountModel ).filter(
        UserOAuthAccountModel.user_id == user_id
    ).first()

    if user_oauth_account is None:
        return None

    # get the latest data record
    oauth_data_record = user_oauth_account.oauth_data_records[-1]

    try:
        return oauth_data_record.oauth_token, json.loads(oauth_data_record.json_data)
    except ValueError as e:
        # Should never happen but just in case
        logger('Invalid JSON data in UserOAuthDataRecordModel: ' + repr(e), 'error')
        return None

