from jsonschema import validate as validate_schema

from controller import BaseHandler
from models import StateLog


class StashStateLog(BaseHandler):
    def post(self):
        """
        For storing state logs that the frontend sends
        to the backend to later be used for replaying sessions, etc.
        """
        schema = {
            "type": "object",
            "properties": {
                    "session_id": {
                        "type": "string"
                    },
                "state": {
                        "type": "object",
                    }
            },
            "required": [
                "session_id",
                "state"
            ]
        }

        validate_schema(self.json, schema)

        authenticated_user_id = self.get_authenticated_user_id()

        state_log = StateLog()
        state_log.session_id = self.json["session_id"]
        state_log.state = self.json["state"]
        state_log.user_id = authenticated_user_id

        self.dbsession.add(state_log)
        self.dbsession.commit()

        self.write({
            "success": True,
        })
