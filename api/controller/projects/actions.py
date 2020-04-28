import json

from models import ProjectConfig


def update_project_config(dbsession, project_id, project_config):
    # Convert to JSON if not already
    if isinstance(project_config, dict):
        project_config = json.dumps(
            project_config
        )

    # Check to see if there's a previous project config
    previous_project_config = dbsession.query(ProjectConfig).filter_by(
        project_id=project_id
    ).first()

    # If not, create one
    if previous_project_config is None:
        new_project_config = ProjectConfig()
        new_project_config.project_id = project_id
        new_project_config.config_json = project_config
        dbsession.add(new_project_config)
    else:  # Otherwise update the current config
        previous_project_config.project_id = project_id
        previous_project_config.config_json = project_config

    dbsession.commit()
