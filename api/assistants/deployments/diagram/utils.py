import json

from tornado import gen

from tasks.build.python import get_python36_base_code, get_python27_base_code
from tasks.build.nodejs import get_nodejs_810_base_code, get_nodejs_10163_base_code, get_nodejs_10201_base_code
from tasks.build.php import get_php_73_base_code
from tasks.build.ruby import get_ruby_264_base_code
from tasks.build.golang import get_go_112_base_code
from utils.general import get_random_node_id, logit, split_list_into_chunks


def get_language_specific_environment_variables(language):
	if language == "python2.7" or language == "python3.6":
		return {
			"PYTHONPATH": "/var/task/",
			"PYTHONUNBUFFERED": "1"
		}
	elif language == "nodejs8.10" or language == "nodejs10.16.3" or language == "nodejs10.20.1":
		return {
			"NODE_PATH": "/var/task/node_modules/"
		}
	return {}


def get_base_lambda_code(app_config, language, code):
	if language == "python3.6":
		return get_python36_base_code(app_config, code)
	elif language == "python2.7":
		return get_python27_base_code(app_config, code)
	elif language == "nodejs8.10":
		return get_nodejs_810_base_code(app_config, code)
	elif language == "nodejs10.16.3":
		return get_nodejs_10163_base_code(app_config, code)
	elif language == "nodejs10.20.1":
		return get_nodejs_10201_base_code(app_config, code)
	elif language == "php7.3":
		return get_php_73_base_code(app_config, code)
	elif language == "ruby2.6.4":
		return get_ruby_264_base_code(app_config, code)
	elif language == "go1.12":
		return get_go_112_base_code(app_config, code)


def get_node_by_id(target_id, workflow_states):
	for workflow_state in workflow_states:
		if workflow_state["id"] == target_id:
			return workflow_state

	return False


def update_workflow_states_list(updated_node, workflow_states):
	for i in range(0, len(workflow_states)):
		if workflow_states[i]["id"] == updated_node["id"]:
			workflow_states[i] = updated_node
			break

	return workflow_states


class MissingResourceException(Exception):
	pass


@gen.coroutine
def create_lambda_api_route(task_spawner, api_gateway_manager, credentials, api_gateway_id, http_method, route, lambda_name, overwrite_existing):
	def not_empty(input_item):
		return input_item != ""

	path_parts = route.split("/")
	path_parts = list(filter(not_empty, path_parts))

	# First we clean the Lambda of API Gateway policies which point
	# to dead API Gateways
	yield task_spawner.clean_lambda_iam_policies(
		credentials,
		lambda_name
	)

	# A default resource is created along with an API gateway, we grab
	# it so we can make our base method
	resources = yield api_gateway_manager.get_resources(
		credentials,
		api_gateway_id
	)

	base_resource_id = None

	for resource in resources:
		if resource["path"] == "/":
			base_resource_id = resource["id"]
			break

	if base_resource_id is None:
		raise MissingResourceException("Missing API Gateway base resource ID. This should never happen")

	# Create a map of paths to verify existance later
	# so we don't overwrite existing resources
	path_existence_map = {}
	for resource in resources:
		path_existence_map[resource["path"]] = resource["id"]

	# Set the pointer to the base
	current_base_pointer_id = base_resource_id

	# Path level, continously updated
	current_path = ""

	# Create entire path from chain
	for path_part in path_parts:
		"""
		TODO: Check for conflicting resources and don't
		overwrite an existing resource if it exists already.
		"""
		# Check if there's a conflicting resource here
		current_path = current_path + "/" + path_part

		# Get existing resource ID instead of creating one
		if current_path in path_existence_map:
			current_base_pointer_id = path_existence_map[current_path]
		else:
			# Otherwise go ahead and create one
			new_resource = yield task_spawner.create_resource(
				credentials,
				api_gateway_id,
				current_base_pointer_id,
				path_part
			)

			current_base_pointer_id = new_resource["id"]

	# Create method on base resource
	method_response = yield task_spawner.create_method(
		credentials,
		"HTTP Method",
		api_gateway_id,
		current_base_pointer_id,
		http_method,
		False,
	)

	# Link the API Gateway to the lambda
	link_response = yield task_spawner.link_api_method_to_lambda(
		credentials,
		api_gateway_id,
		current_base_pointer_id,
		http_method,  # GET was previous here
		route,
		lambda_name
	)

	resources = yield api_gateway_manager.get_resources(
		credentials,
		api_gateway_id
	)

	# Clown-shoes AWS bullshit for binary response
	yield task_spawner.add_integration_response(
		credentials,
		api_gateway_id,
		current_base_pointer_id,
		http_method,
		lambda_name
	)


@gen.coroutine
def create_warmer_for_lambda_set(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list):
	# Create Lambda warmers if enabled
	warmer_trigger_name = "WarmerTrigger" + unique_deploy_id
	logit("Deploying auto-warmer CloudWatch rule...")
	warmer_trigger_result = yield task_spawner.create_cloudwatch_rule(
		credentials,
		get_random_node_id(),
		warmer_trigger_name,
		"rate(5 minutes)",
		"A CloudWatch Event trigger to keep the deployed Lambdas warm.",
		"",
	)

	# Go through all the Lambdas deployed and make them the targets of the
	# warmer Lambda so everything is kept hot.
	# Additionally we'll invoke them all once with a warmup request so
	# that they are hot if hit immediately
	for deployed_lambda in combined_warmup_list:
		yield task_spawner.add_rule_target(
			credentials,
			warmer_trigger_name,
			deployed_lambda["name"],
			deployed_lambda["arn"],
			json.dumps({
				"_refinery": {
					"warmup": warmup_concurrency_level,
				}
			})
		)

		task_spawner.warm_up_lambda(
			credentials,
			deployed_lambda["arn"],
			warmup_concurrency_level
		)

	raise gen.Return({
		"id": warmer_trigger_result["id"],
		"name": warmer_trigger_name,
		"arn": warmer_trigger_result["arn"]
	})


@gen.coroutine
def add_auto_warmup(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list):
	# Split warmup list into a list of lists with each list containing five elements.
	# This is so that we match the limit for CloudWatch Rules max targets (5 per rule).
	# See "Targets" under this following URL:
	# https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/cloudwatch_limits_cwe.html
	split_combined_warmup_list = split_list_into_chunks(
		combined_warmup_list,
		5
	)

	# Ensure each Cloudwatch Rule has a unique name
	warmup_unique_counter = 0

	warmup_futures = []

	for warmup_chunk_list in split_combined_warmup_list:
		warmup_futures.append(
			create_warmer_for_lambda_set(
				task_spawner,
				credentials,
				warmup_concurrency_level,
				unique_deploy_id + "_W" + str(warmup_unique_counter),
				warmup_chunk_list
			)
		)

		warmup_unique_counter += 1

	# Wait for all of the concurrent Cloudwatch Rule creations to finish
	warmer_triggers = yield warmup_futures
	raise gen.Return(warmer_triggers)

def get_layers_for_lambda(language):
	"""
	IGNORE THIS NOTICE AT YOUR OWN PERIL. YOU HAVE BEEN WARNED.

	All layers are managed under our root AWS account at 134071937287.

	When a new layer is published the ARNs must be updated in source intentionally
	so that whoever does so must read this notice and understand what MUST
	be done before updating the Refinery customer runtime for customers.

	You must do the following:
	* Extensively test the new custom runtime.
	* Upload the new layer version to the root AWS account.
	* Run the following command on the root account to publicly allow use of the layer:

	aws lambda add-layer-version-permission \
	--layer-name REPLACE_ME_WITH_LAYER_NAME \
	--version-number REPLACE_ME_WITH_LAYER_VERSION \
	--statement-id public \
	--action lambda:GetLayerVersion \
	--principal "*" \
	--region us-west-2

	* Test the layer in a development version of Refinery to ensure it works.
	* Update the source code with the new layer ARN

	Once this is done all future deployments will use the new layers.
	"""
	new_layers = []

	# Add the custom runtime layer in all cases
	if language == "nodejs8.10":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-node810-custom-runtime:30"
		)
	elif language == "nodejs10.16.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs10-custom-runtime:9"
		)
	elif language == "nodejs10.20.1":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs1020-custom-runtime:1"
		)
	elif language == "php7.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-php73-custom-runtime:28"
		)
	elif language == "go1.12":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-go112-custom-runtime:29"
		)
	elif language == "python2.7":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python27-custom-runtime:28"
		)
	elif language == "python3.6":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python36-custom-runtime:29"
		)
	elif language == "ruby2.6.4":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-ruby264-custom-runtime:29"
		)

	return new_layers
