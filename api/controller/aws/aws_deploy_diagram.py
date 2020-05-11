import json

from tornado import gen

from controller.aws.aws_deployment_types import DeploymentDiagram, workflow_state_from_json, workflow_relationship_from_json
from utils.general import get_random_deploy_id, logit


@gen.coroutine
def deploy_diagram(task_spawner, api_gateway_manager, credentials, project_name, project_id, diagram_data, project_config):
	"""

	:param task_spawner:
	:param api_gateway_manager:
	:param credentials:
	:param project_name:
	:param project_id:
	:param diagram_data:
	:param project_config:
	:return:
	"""

	# Kick off the creation of the log table for the project ID
	# This is fine to do if one already exists because the SQL
	# query explicitly specifies not to create one if it exists.
	project_log_table_future = task_spawner.create_project_id_log_table(
		credentials,
		project_id
	)

	# Random ID to keep deploy ARNs unique
	unique_deploy_id = get_random_deploy_id()

	deployment_exceptions = []

	unique_name_counter = 0

	deployment_diagram: DeploymentDiagram = DeploymentDiagram(project_id, project_name, project_config)

	# If we have workflow files and links, add them to the deployment
	workflow_files_json = diagram_data.get("workflow_files")
	workflow_file_links_json = diagram_data.get("workflow_file_links")
	if workflow_files_json and workflow_file_links_json:
		deployment_diagram.add_workflow_files(workflow_files_json, workflow_file_links_json)

	# Create an in-memory representation of the deployment data
	for n, workflow_state_json in enumerate(diagram_data["workflow_states"]):

		# Update all of the workflow states with new random deploy ID
		if "name" in workflow_state_json:
			workflow_state_json["name"] += unique_deploy_id + str(unique_name_counter)
			unique_name_counter = unique_name_counter + 1

		workflow_state = workflow_state_from_json(
			credentials, deployment_diagram, workflow_state_json)

		deployment_diagram.add_workflow_state(workflow_state)

	# If we did not find an api gateway, let's create a placeholder for now
	if deployment_diagram.api_gateway is None:
		deployment_diagram.initialize_api_gateway(credentials)

	# Add transition data to each Lambda
	for workflow_relationship_json in diagram_data["workflow_relationships"]:
		workflow_relationship_from_json(deployment_diagram, workflow_relationship_json)
	deployment_diagram.finalize_merge_transitions()

	deployment_exceptions = yield deployment_diagram.deploy(
		task_spawner, api_gateway_manager, credentials, unique_deploy_id)

	if len(deployment_exceptions) > 0:
		# This is the earliest point we can apply the breaks in the case of an exception
		# It's the callers responsibility to tear down the nodes

		logit("[ ERROR ] An uncaught exception occurred during the deployment process!", "error")
		logit(deployment_exceptions, "error")
		raise gen.Return({
			"success": False,
			"teardown_nodes_list": deployment_diagram.get_workflow_states_for_teardown(),
			"exceptions": deployment_exceptions,
		})

	# Make sure that log table is set up
	# It almost certainly is by this point
	yield project_log_table_future

	raise gen.Return({
		"success": True,
		"project_name": project_name,
		"project_id": project_id,
		"deployment_diagram": deployment_diagram.serialize(),
		"project_config": project_config
	})
