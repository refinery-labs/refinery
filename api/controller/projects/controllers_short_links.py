from jsonschema import validate as validate_schema
from tornado import gen

from controller import BaseHandler
from controller.decorators import authenticated
from controller.projects import GET_PROJECT_SHORT_LINK_SCHEMA, CREATE_PROJECT_SHORT_LINK_SCHEMA
from models import ProjectShortLink


class GetProjectShortlink(BaseHandler):
    @gen.coroutine
    def post(self):
        """
        Returns project JSON by the project_short_link_id
        """
        validate_schema(self.json, GET_PROJECT_SHORT_LINK_SCHEMA)

        project_short_link = self.dbsession.query(ProjectShortLink).filter_by(
            short_id=self.json["project_short_link_id"]
        ).first()

        if not project_short_link:
            self.write({
                "success": False,
                "msg": "Project short link was not found!"
            })
            raise gen.Return()

        project_short_link_dict = project_short_link.to_dict()

        self.write({
            "success": True,
            "msg": "Project short link created successfully!",
            "result": {
                "project_short_link_id": project_short_link_dict["short_id"],
                "diagram_data": project_short_link_dict["project_json"],
            }
        })


class CreateProjectShortlink(BaseHandler):
    @authenticated
    @gen.coroutine
    def post(self):
        """
        Creates a new project shortlink for a project so it can be shared
        and "forked" by other people on the platform.
        """
        validate_schema(self.json, CREATE_PROJECT_SHORT_LINK_SCHEMA)

        new_project_shortlink = ProjectShortLink()
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