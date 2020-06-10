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
