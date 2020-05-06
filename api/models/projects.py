from .initiate_database import *
import json
import uuid
import time

from .user_project_associations import users_projects_association_table


class Project(Base):
    __tablename__ = "projects"

    id = Column(CHAR(36), primary_key=True)
    name = Column(
        Text()
    )

    # Many to many relationship to projects
    # A user can belong to many projects
    # A project can belong to many users
    users = relationship(
        "User",
        lazy="dynamic",
        secondary=users_projects_association_table,
        back_populates="projects"
    )

    # Versions of the projects
    versions = relationship(
        "ProjectVersion",
        backref="projects",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    deployments = relationship(
        "Deployment",
        backref="projects",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    configs = relationship(
        "ProjectConfig",
        backref="configs",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    timestamp = Column(Integer())

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = int(time.time())

    def to_dict(self):
        exposed_attributes = [
            "id",
            "name",
            "timestamp"
        ]

        json_attributes = []
        return_dict = {}

        for attribute in exposed_attributes:
            if attribute in json_attributes:
                return_dict[attribute] = json.loads(
                    getattr(self, attribute)
                )
            else:
                return_dict[attribute] = getattr(self, attribute)

        return return_dict

    def __str__(self):
        return self.id
