import copy
import json
import traceback
import uuid

from tornado import gen

from assistants.deployments.api_gateway import strip_api_gateway
from assistants.deployments.shared_files import get_shared_files_for_lambda
from tasks.build.python import get_python36_base_code, get_python27_base_code
from tasks.build.nodejs import get_nodejs_810_base_code, get_nodejs_10163_base_code, get_nodejs_10201_base_code
from tasks.build.php import get_php_73_base_code
from tasks.build.ruby import get_ruby_264_base_code
from tasks.build.golang import get_go_112_base_code
from data_types.aws_resources.alambda import Lambda
from pyconstants.project_constants import THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME
from pyexceptions.builds import BuildException
from utils.general import logit, get_random_deploy_id, get_random_node_id, split_list_into_chunks, get_lambda_safe_name


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


def get_language_specific_environment_variables(language):
    environment_variables_list = []

    if language == "python2.7" or language == "python3.6":
        environment_variables_list.append({
            "key": "PYTHONPATH",
            "value": "/var/task/",
        })
        environment_variables_list.append({
            "key": "PYTHONUNBUFFERED",
            "value": "1",
        })
    elif language == "nodejs8.10" or language == "nodejs10.16.3" or language == "nodejs10.20.1":
        environment_variables_list.append({
            "key": "NODE_PATH",
            "value": "/var/task/node_modules/",
        })

    return environment_variables_list


def get_environment_variables_for_lambda(credentials, lambda_object):
    all_environment_vars = copy.copy(lambda_object.environment_variables)

    # Add environment variables depending on language
    # This is mainly for module loading when we're doing inline executions.
    all_environment_vars = all_environment_vars + get_language_specific_environment_variables(
        lambda_object.language
    )

    all_environment_vars.append({
        "key": "REDIS_HOSTNAME",
        "value": credentials["redis_hostname"],
    })

    all_environment_vars.append({
        "key": "REDIS_PASSWORD",
        "value": credentials["redis_password"],
    })

    all_environment_vars.append({
        "key": "REDIS_PORT",
        "value": str(credentials["redis_port"]),
    })

    all_environment_vars.append({
        "key": "EXECUTION_PIPELINE_ID",
        "value": lambda_object.execution_pipeline_id,
    })

    all_environment_vars.append({
        "key": "LOG_BUCKET_NAME",
        "value": credentials["logs_bucket"],
    })

    all_environment_vars.append({
        "key": "PACKAGES_BUCKET_NAME",
        "value": credentials["lambda_packages_bucket"],
    })

    all_environment_vars.append({
        "key": "PIPELINE_LOGGING_LEVEL",
        "value": lambda_object.execution_log_level,
    })

    all_environment_vars.append({
        "key": "EXECUTION_MODE",
        "value": lambda_object.execution_mode,
    })

    all_environment_vars.append({
        "key": "TRANSITION_DATA",
        "value": json.dumps(
            lambda_object.transitions
        ),
    })

    if lambda_object.is_inline_execution:
        # The environment variable activates it as
        # an inline execution Lambda and allows us to
        # pass in arbitrary code to execution.
        all_environment_vars.append({
            "key": "IS_INLINE_EXECUTOR",
            "value": "True",
        })

    return all_environment_vars


@gen.coroutine
def deploy_lambda(task_spawner, credentials, id, lambda_object):
    """
    Here we build the default required environment variables.
    """
    lambda_object.environment_variables = get_environment_variables_for_lambda(
        credentials,
        lambda_object
    )

    logit(
        "Deploying '" + lambda_object.name + "' Lambda package to production..."
    )

    lambda_object.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/refinery_default_aws_lambda_role"

    # If it's a self-hosted (THIRDPARTY) AWS account we deploy with a different role
    # name which they manage themselves.
    if credentials["account_type"] == "THIRDPARTY":
        lambda_object.role = "arn:aws:iam::" + str(credentials["account_id"]) + ":role/" + THIRD_PARTY_AWS_ACCOUNT_ROLE_NAME

    # Don't yield for it, but we'll also create a log group at the same time
    # We're set a tag for that log group for cost tracking
    task_spawner.create_cloudwatch_group(
        credentials,
        "/aws/lambda/" + lambda_object.name,
        {
            "RefineryResource": "true"
        },
        7
    )

    deployed_lambda_data = yield task_spawner.deploy_aws_lambda(
        credentials,
        lambda_object
    )

    # If we have concurrency set, then we'll set that for our deployed Lambda
    if lambda_object.reserved_concurrency_count:
        logit("Setting reserved concurrency for Lambda '" +
              deployed_lambda_data["FunctionArn"] +
              "' to " +
              str(lambda_object.reserved_concurrency_count) +
              "...")
        yield task_spawner.set_lambda_reserved_concurrency(
            credentials,
            deployed_lambda_data["FunctionArn"],
            lambda_object.reserved_concurrency_count
        )

    raise gen.Return({
        "id": id,
        "name": lambda_object.name,
        "arn": deployed_lambda_data["FunctionArn"]
    })


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


def get_merge_lambda_arn_list(target_id, workflow_relationships, workflow_states):
    # First we create a list of Node IDs
    id_target_list = []

    for workflow_relationship in workflow_relationships:
        if workflow_relationship["type"] != "merge":
            continue

        if workflow_relationship["next"] != target_id:
            continue

        id_target_list.append(
            workflow_relationship["node"]
        )

    arn_list = []

    for workflow_state in workflow_states:
        if workflow_state["id"] in id_target_list:
            arn_list.append(
                workflow_state["arn"]
            )

    return arn_list


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
def create_warmer_for_lambda_set(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list, diagram_data):
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

    diagram_data["workflow_states"].append({
        "id": warmer_trigger_result["id"],
        "type": "warmer_trigger",
        "name": warmer_trigger_name,
        "arn": warmer_trigger_result["arn"]
    })

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


@gen.coroutine
def add_auto_warmup(task_spawner, credentials, warmup_concurrency_level, unique_deploy_id, combined_warmup_list, diagram_data):
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
                warmup_chunk_list,
                diagram_data
            )
        )

        warmup_unique_counter += 1

    # Wait for all of the concurrent Cloudwatch Rule creations to finish
    yield warmup_futures


def set_default_exception_handler(workflow_states, default_handler_id, default_exception_transition):
    for workflow_state in workflow_states:
        # Only set the exception handler for lambdas and api endpoints
        if workflow_state[ "type" ] != "lambda" and workflow_state[ "type" ] != "api_endpoint":
            continue

        # Do not set the exception handler for the exception handler!
        if workflow_state[ "id" ] == default_handler_id:
            continue

        # If there are exception handlers already set for this workflow state, do not set the default handler
        if len(workflow_state[ "transitions" ][ "exception" ]) > 0:
            continue

        workflow_state[ "transitions" ][ "exception" ] = default_exception_transition


@gen.coroutine
def deploy_diagram( task_spawner, api_gateway_manager, credentials, project_name, project_id, diagram_data, project_config ):
    """
    Deploy the diagram to AWS
    """

    """
    Process workflow relationships and tag Lambda
    nodes with an array of transitions.
    """

    # Kick off the creation of the log table for the project ID
    # This is fine to do if one already exists because the SQL
    # query explicitly specifies not to create one if it exists.
    project_log_table_future = task_spawner.create_project_id_log_table(
        credentials,
        project_id
    )

    # Random ID to keep deploy ARNs unique
    # TODO do more research into collision probability
    unique_deploy_id = get_random_deploy_id()

    unique_name_counter = 0

    # Environment variable map
    # { "LAMBDA_UUID": [{ "key": "", "value": ""}] }
    env_var_dict = {}

    # Set the default exception handler if there is one set in the project
    default_exception_transitions = []

    default_exception_handler_id = ""
    if "exception_handler" in diagram_data[ "global_handlers" ]:
        default_exception_handler_id = diagram_data[ "global_handlers" ][ "exception_handler" ][ "id" ]

    # First just set an empty array for each lambda node
    for workflow_state in diagram_data[ "workflow_states" ]:
        # Update all of the workflow states with new random deploy ID
        if "name" in workflow_state:
            workflow_state[ "name" ] += unique_deploy_id + str(unique_name_counter)

        # Make an environment variable array if there isn't one already
        env_var_dict[ workflow_state[ "id" ] ] = []

        # If there are environment variables in project_config, add them to the Lambda node data
        if workflow_state["type"] == "lambda" and "environment_variables" in workflow_state:
            for env_var_uuid, env_data in workflow_state["environment_variables"].items():
                if env_var_uuid in project_config["environment_variables"]:
                    # Add value to match schema
                    workflow_state[ "environment_variables" ][ env_var_uuid ][ "value" ] = project_config[ "environment_variables" ][ env_var_uuid ][ "value" ]
                    env_var_dict[ workflow_state[ "id" ] ].append({
                        "key": workflow_state[ "environment_variables" ][ env_var_uuid ][ "name" ],
                        "value": project_config[ "environment_variables" ][ env_var_uuid ][ "value" ]
                    })

        if workflow_state[ "type" ] == "lambda" or workflow_state[ "type" ] == "api_endpoint":
            # Set up default transitions data
            workflow_state[ "transitions" ] = {}
            workflow_state[ "transitions" ][ "if" ] = []
            workflow_state[ "transitions" ][ "else" ] = []
            workflow_state[ "transitions" ][ "exception" ] = []
            workflow_state[ "transitions" ][ "then" ] = []
            workflow_state[ "transitions" ][ "fan-out" ] = []
            workflow_state[ "transitions" ][ "fan-in" ] = []
            workflow_state[ "transitions" ][ "merge" ] = []

        unique_name_counter = unique_name_counter + 1

    """
    Here we calculate the teardown data ahead of time.

    This is used when we encounter an error during the
    deployment process which requires us to roll back.
    When the rollback occurs we pass our previously-generated
    list and pass it to the tear down function.

    [
        {
            "id": {{node_id}},
            "arn": {{production_resource_arn}},
            "name": {{node_name}},
            "type": {{node_type}},
        }
    ]
    """
    teardown_nodes_list = []


    """
    This holds all of the exception data which occurred during a
    deployment. Upon an unhandled exception occurring we rollback
    and teardown what's been deployed so far. After that we return
    an error to the user with information on what caused the deploy
    to fail.

    [
        {
            "type": "", # The type of the deployed node
            "name": "", # The name of the specific node
            "id": "", # The ID of the specific node
            "exception": "", # String of the exception details
        }
    ]
    """
    deployment_exceptions = []

    for workflow_state in diagram_data[ "workflow_states" ]:
        if workflow_state[ "type" ] == "lambda":
            node_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( workflow_state[ "name" ] )
        elif workflow_state[ "type" ] == "sns_topic":
            node_arn = "arn:aws:sns:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( workflow_state[ "name" ] )
        elif workflow_state[ "type" ] == "sqs_queue":
            node_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( workflow_state[ "name" ] )
        elif workflow_state[ "type" ] == "schedule_trigger":
            node_arn = "arn:aws:events:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":rule/" + get_lambda_safe_name( workflow_state[ "name" ] )
        elif workflow_state[ "type" ] == "api_endpoint":
            node_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( workflow_state[ "name" ] )
        else:
            node_arn = False

        # For pseudo-nodes like API Responses we don't need to create a teardown entry
        if node_arn:
            # Set ARN on workflow state
            workflow_state[ "arn" ] = node_arn

            teardown_nodes_list.append({
                "id": workflow_state[ "id" ],
                "arn": node_arn,
                "name": get_lambda_safe_name( workflow_state[ "name" ] ),
                "type": workflow_state[ "type" ],
            })

        if workflow_state[ "id" ] == default_exception_handler_id:
            default_exception_transitions = [workflow_state]

    if len(default_exception_transitions) > 0:
        set_default_exception_handler(diagram_data[ "workflow_states" ], default_exception_handler_id, default_exception_transitions)

    # Now add transition data to each Lambda
    for workflow_relationship in diagram_data[ "workflow_relationships" ]:
        origin_node_data = get_node_by_id(
            workflow_relationship[ "node" ],
            diagram_data[ "workflow_states" ]
        )

        target_node_data = get_node_by_id(
            workflow_relationship[ "next" ],
            diagram_data[ "workflow_states" ]
        )

        if origin_node_data[ "type" ] == "lambda" or origin_node_data[ "type" ] == "api_endpoint":
            if target_node_data[ "type" ] == "lambda":
                target_arn = "arn:aws:lambda:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":function:" + get_lambda_safe_name( target_node_data[ "name" ] )
            elif target_node_data[ "type" ] == "sns_topic":
                target_arn = "arn:aws:sns:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] )+ ":" + get_lambda_safe_name( target_node_data[ "name" ] )
            elif target_node_data[ "type" ] == "api_gateway_response":
                # API Gateway responses are a pseudo node and don't have an ARN
                target_arn = False
            elif target_node_data[ "type" ] == "sqs_queue":
                target_arn = "arn:aws:sqs:" + credentials[ "region" ] + ":" + str( credentials[ "account_id" ] ) + ":" + get_lambda_safe_name( target_node_data[ "name" ] )

            if workflow_relationship[ "type" ] == "then":
                origin_node_data[ "transitions" ][ "then" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                })
            elif workflow_relationship[ "type" ] == "else":
                origin_node_data[ "transitions" ][ "else" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                })
            elif workflow_relationship[ "type" ] == "exception":

                # If the default exception handler is set, unset it since the exception will be handled
                if origin_node_data[ "transitions" ][ "exception" ] == default_exception_transitions:
                    origin_node_data[ "transitions" ][ "exception" ] = []

                origin_node_data[ "transitions" ][ "exception" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                })
            elif workflow_relationship[ "type" ] == "if":
                origin_node_data[ "transitions" ][ "if" ].append({
                    "arn": target_arn,
                    "type": target_node_data[ "type" ],
                    "expression": workflow_relationship[ "expression" ]
                })
            elif workflow_relationship[ "type" ] == "fan-out":
                origin_node_data[ "transitions" ][ "fan-out" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                })
            elif workflow_relationship[ "type" ] == "fan-in":
                origin_node_data[ "transitions" ][ "fan-in" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                })
            elif workflow_relationship[ "type" ] == "merge":
                origin_node_data[ "transitions" ][ "merge" ].append({
                    "type": target_node_data[ "type" ],
                    "arn": target_arn,
                    "merge_lambdas": get_merge_lambda_arn_list(
                        target_node_data[ "id" ],
                        diagram_data[ "workflow_relationships" ],
                        diagram_data[ "workflow_states" ]
                    )
                })

            diagram_data[ "workflow_states" ] = update_workflow_states_list(
                origin_node_data,
                diagram_data[ "workflow_states" ]
            )

    """
    Separate out nodes into different types
    """
    lambda_nodes = []
    schedule_trigger_nodes = []
    sqs_queue_nodes = []
    sns_topic_nodes = []
    api_endpoint_nodes = []

    for workflow_state in diagram_data[ "workflow_states" ]:
        if workflow_state[ "type" ] == "lambda":
            lambda_nodes.append(
                workflow_state
            )
        elif workflow_state[ "type" ] == "schedule_trigger":
            schedule_trigger_nodes.append(
                workflow_state
            )
        elif workflow_state[ "type" ] == "sqs_queue":
            sqs_queue_nodes.append(
                workflow_state
            )
        elif workflow_state[ "type" ] == "sns_topic":
            sns_topic_nodes.append(
                workflow_state
            )
        elif workflow_state[ "type" ] == "api_endpoint":
            api_endpoint_nodes.append(
                workflow_state
            )

    """
    Deploy all Lambdas to production
    """
    lambda_node_deploy_futures = []

    for lambda_node in lambda_nodes:
        lambda_safe_name = get_lambda_safe_name( lambda_node[ "name" ] )
        logit( "Deploying Lambda '" + lambda_safe_name + "'..." )

        # For backwards compatibility
        if not ( "reserved_concurrency_count" in lambda_node ):
            lambda_node[ "reserved_concurrency_count" ] = False

        lambda_layers = get_layers_for_lambda(
            lambda_node[ "language" ]
        ) + lambda_node[ "layers" ]

        shared_files = get_shared_files_for_lambda(
            lambda_node[ "id" ],
            diagram_data
        )

        # Create Lambda object
        lambda_object = Lambda(
            name=lambda_safe_name,
            language=lambda_node[ "language" ],
            code=lambda_node[ "code" ],
            libraries=lambda_node[ "libraries" ],
            max_execution_time=lambda_node[ "max_execution_time" ],
            memory=lambda_node[ "memory" ],
            transitions=lambda_node[ "transitions" ],
            execution_mode="REGULAR",
            execution_pipeline_id=project_id,
            execution_log_level=project_config[ "logging" ][ "level" ],
            environment_variables=env_var_dict[ lambda_node[ "id" ] ],
            layers=lambda_layers,
            reserved_concurrency_count=lambda_node[ "reserved_concurrency_count" ],
            is_inline_execution=False,
            shared_files_list=shared_files
        )

        lambda_node_deploy_futures.append({
            "id": lambda_node[ "id" ],
            "name": lambda_safe_name,
            "type": lambda_node[ "type" ],
            "future": deploy_lambda(
                task_spawner,
                credentials,
                lambda_node[ "id" ],
                lambda_object
            )
        })

    """
    Deploy all API Endpoints to production
    """
    api_endpoint_node_deploy_futures = []

    for api_endpoint_node in api_endpoint_nodes:
        api_endpoint_safe_name = get_lambda_safe_name( api_endpoint_node[ "name" ] )
        logit( "Deploying API Endpoint '" + api_endpoint_safe_name + "'..." )

        lambda_layers = get_layers_for_lambda( "python2.7" )

        # Create Lambda object
        lambda_object = Lambda(
            name=api_endpoint_safe_name,
            language="python2.7",
            code="",
            libraries=[],
            max_execution_time=30,
            memory=512,
            transitions=api_endpoint_node[ "transitions" ],
            execution_mode="API_ENDPOINT",
            execution_pipeline_id=project_id,
            execution_log_level=project_config[ "logging" ][ "level" ],
            environment_variables=[],
            layers=lambda_layers,
            reserved_concurrency_count=False,
            is_inline_execution=False,
            shared_files_list=[]
        )

        api_endpoint_node_deploy_futures.append({
            "id": api_endpoint_node[ "id" ],
            "name": get_lambda_safe_name( api_endpoint_node[ "name" ] ),
            "type": api_endpoint_node[ "type" ],
            "future": deploy_lambda(
                task_spawner,
                credentials,
                api_endpoint_node[ "id" ],
                lambda_object
            )
        })

    """
    Deploy all time triggers to production
    """
    schedule_trigger_node_deploy_futures = []

    for schedule_trigger_node in schedule_trigger_nodes:
        schedule_trigger_name = get_lambda_safe_name( schedule_trigger_node[ "name" ] )
        logit( "Deploying schedule trigger '" + schedule_trigger_name + "'..." )
        schedule_trigger_node_deploy_futures.append({
            "id": schedule_trigger_node[ "id" ],
            "name": schedule_trigger_name,
            "type": schedule_trigger_node[ "type" ],
            "future": task_spawner.create_cloudwatch_rule(
                credentials,
                schedule_trigger_node[ "id" ],
                schedule_trigger_name,
                schedule_trigger_node[ "schedule_expression" ],
                schedule_trigger_node[ "description" ],
                schedule_trigger_node[ "input_string" ],
            )
        })

    """
    Deploy all SQS queues to production
    """
    sqs_queue_nodes_deploy_futures = []

    for sqs_queue_node in sqs_queue_nodes:
        sqs_queue_name = get_lambda_safe_name( sqs_queue_node[ "name" ] )
        logit( "Deploying SQS queue '" + sqs_queue_name + "'..." )
        sqs_queue_nodes_deploy_futures.append({
            "id": sqs_queue_node[ "id" ],
            "name": sqs_queue_name,
            "type": sqs_queue_node[ "type" ],
            "future": task_spawner.create_sqs_queue(
                credentials,
                sqs_queue_node[ "id" ],
                sqs_queue_name,
                int( sqs_queue_node[ "batch_size" ] ), # Not used, passed along
                900,  # Max Lambda runtime - TODO set this to the linked Lambda amount
            )
        })

    """
    Deploy all SNS topics to production
    """
    sns_topic_nodes_deploy_futures = []

    for sns_topic_node in sns_topic_nodes:
        sns_topic_name = get_lambda_safe_name( sns_topic_node[ "name" ] )
        logit( "Deploying SNS topic '" + sns_topic_name + "'..." )

        sns_topic_nodes_deploy_futures.append({
            "id": sns_topic_node[ "id" ],
            "name": sns_topic_name,
            "type": sns_topic_node[ "type" ],
            "future": task_spawner.create_sns_topic(
                credentials,
                sns_topic_node[ "id" ],
                sns_topic_name,
            )
        })

    # Combine futures
    combined_futures_list = []
    combined_futures_list += schedule_trigger_node_deploy_futures
    combined_futures_list += lambda_node_deploy_futures
    combined_futures_list += sqs_queue_nodes_deploy_futures
    combined_futures_list += sns_topic_nodes_deploy_futures
    combined_futures_list += api_endpoint_node_deploy_futures

    # Initialize list of results
    deployed_schedule_triggers = []
    deployed_lambdas = []
    deployed_sqs_queues = []
    deployed_sns_topics = []
    deployed_api_endpoints = []

    # Wait till everything is deployed
    for deploy_future_data in combined_futures_list:
        try:
            output = yield deploy_future_data[ "future" ]

            logit( "Deployed node '" + deploy_future_data[ "name" ] + "' successfully!" )

            # Append to approriate lists
            if deploy_future_data[ "type" ] == "lambda":
                deployed_lambdas.append(
                    output
                )
            elif deploy_future_data[ "type" ] == "sqs_queue":
                deployed_sqs_queues.append(
                    output
                )
            elif deploy_future_data[ "type" ] == "schedule_trigger":
                deployed_schedule_triggers.append(
                    output
                )
            elif deploy_future_data[ "type" ] == "sns_topic":
                deployed_sns_topics.append(
                    output
                )
            elif deploy_future_data[ "type" ] == "api_endpoint":
                deployed_api_endpoints.append(
                    output
                )
        except Exception as e:
            logit( "Failed to deploy node '" + deploy_future_data[ "name" ] + "'!", "error" )

            exception_msg = traceback.format_exc()
            if type(e) is BuildException:
                # noinspection PyUnresolvedReferences
                exception_msg = e.build_output

            logit( "Deployment failure exception details: " + repr(exception_msg), "error" )
            deployment_exceptions.append({
                "id": deploy_future_data[ "id" ],
                "name": deploy_future_data[ "name" ],
                "type": deploy_future_data[ "type" ],
                "exception": exception_msg
            })

    # This is the earliest point we can apply the breaks in the case of an exception
    # It's the callers responsibility to tear down the nodes
    if len( deployment_exceptions ) > 0:
        logit( "[ ERROR ] An uncaught exception occurred during the deployment process!", "error" )
        logit( deployment_exceptions, "error" )
        raise gen.Return({
            "success": False,
            "teardown_nodes_list": teardown_nodes_list,
            "exceptions": deployment_exceptions,
        })

    """
    Set up API Gateways to be attached to API Endpoints
    """

    # The API Gateway ID
    api_gateway_id = False

    # Pull previous API Gateway ID if it exists
    if project_config[ "api_gateway" ][ "gateway_id" ]:
        api_gateway_id = project_config[ "api_gateway" ][ "gateway_id" ]
        logit( "Previous API Gateway exists with ID of '" + api_gateway_id + "'..." )

    if len( deployed_api_endpoints ) > 0:
        api_route_futures = []

        # Verify the existance of API Gateway before proceeding
        # It could have been deleted.
        logit( "Verifying existance of API Gateway..." )
        if api_gateway_id:
            api_gateway_exists = yield api_gateway_manager.api_gateway_exists(
                credentials,
                api_gateway_id
            )
        else:
            api_gateway_exists = False

        # If it doesn't exist we'll set the API Gateway ID to False
        # So that it will be freshly created.
        if not api_gateway_exists:
            api_gateway_id = False

        # We need to create an API gateway
        logit( "Deploying API Gateway for API Endpoint(s)..." )

        # Create a new API Gateway if one does not already exist
        if api_gateway_id == False:
            # We just generate a random ID for the API Gateway, no great other way to do it.
            # e.g. when you change the project name now it's hard to know what the API Gateway
            # is...
            rest_api_name = "Refinery-API-Gateway_" + str( uuid.uuid4() ).replace(
                "-",
                ""
            )
            create_gateway_result = yield task_spawner.create_rest_api(
                credentials,
                rest_api_name,
                "API Gateway created by Refinery. Associated with project ID " + project_id,
                "1.0.0"
            )

            api_gateway_id = create_gateway_result[ "id" ]

            # Update project config
            project_config[ "api_gateway" ][ "gateway_id" ] = api_gateway_id
        else:
            # We do another strip of the gateway just to be sure
            yield strip_api_gateway(
                api_gateway_manager,
                credentials,
                project_config[ "api_gateway" ][ "gateway_id" ],
            )

        # Add the API Gateway as a new node
        diagram_data[ "workflow_states" ].append({
            "id": get_random_node_id(),
            "type": "api_gateway",
            "name": "__api_gateway__",
            "rest_api_id": api_gateway_id,
        })

        for deployed_api_endpoint in deployed_api_endpoints:
            for workflow_state in diagram_data[ "workflow_states" ]:
                if workflow_state[ "id" ] == deployed_api_endpoint[ "id" ]:
                    logit( "Setting up route " + workflow_state[ "http_method" ] + " " + workflow_state[ "api_path" ] + " for API Endpoint '" + workflow_state[ "name" ] + "'..." )
                    yield create_lambda_api_route(
                        task_spawner,
                        api_gateway_manager,
                        credentials,
                        api_gateway_id,
                        workflow_state[ "http_method" ],
                        workflow_state[ "api_path" ],
                        deployed_api_endpoint[ "name" ],
                        True
                    )


        logit( "Now deploying API gateway to stage..." )
        deploy_stage_results = yield task_spawner.deploy_api_gateway_to_stage(
            credentials,
            api_gateway_id,
            "refinery"
        )

    """
    Update all nodes with deployed ARN for easier teardown
    """
    # Update workflow lambda nodes with arn
    for deployed_lambda in deployed_lambdas:
        for workflow_state in diagram_data[ "workflow_states" ]:
            if workflow_state[ "id" ] == deployed_lambda[ "id" ]:
                workflow_state[ "arn" ] = deployed_lambda[ "arn" ]
                workflow_state[ "name" ] = deployed_lambda[ "name" ]

    # Update workflow API Endpoint nodes with arn
    for deployed_api_endpoint in deployed_api_endpoints:
        for workflow_state in diagram_data[ "workflow_states" ]:
            if workflow_state[ "id" ] == deployed_api_endpoint[ "id" ]:
                workflow_state[ "arn" ] = deployed_api_endpoint[ "arn" ]
                workflow_state[ "name" ] = deployed_api_endpoint[ "name" ]
                workflow_state[ "rest_api_id" ] = api_gateway_id
                workflow_state[ "url" ] = "https://" + str(api_gateway_id) + ".execute-api." + credentials[ "region" ] + ".amazonaws.com/refinery" + workflow_state[ "api_path" ]

    # Update workflow scheduled trigger nodes with arn
    for deployed_schedule_trigger in deployed_schedule_triggers:
        for workflow_state in diagram_data[ "workflow_states" ]:
            if workflow_state[ "id" ] == deployed_schedule_trigger[ "id" ]:
                workflow_state[ "arn" ] = deployed_schedule_trigger[ "arn" ]
                workflow_state[ "name" ] = deployed_schedule_trigger[ "name" ]

    # Update SQS queue nodes with arn
    for deployed_sqs_queue in deployed_sqs_queues:
        for workflow_state in diagram_data[ "workflow_states" ]:
            if workflow_state[ "id" ] == deployed_sqs_queue[ "id" ]:
                workflow_state[ "arn" ] = deployed_sqs_queue[ "arn" ]
                workflow_state[ "name" ] = deployed_sqs_queue[ "name" ]

    # Update SNS topics with arn
    for deployed_sns_topic in deployed_sns_topics:
        for workflow_state in diagram_data[ "workflow_states" ]:
            if workflow_state[ "id" ] == deployed_sns_topic[ "id" ]:
                workflow_state[ "arn" ] = deployed_sns_topic[ "arn" ]
                workflow_state[ "name" ] = deployed_sns_topic[ "name" ]


    """
    Link deployed schedule triggers to Lambdas
    """
    schedule_trigger_pairs_to_deploy = []
    for deployed_schedule_trigger in deployed_schedule_triggers:
        for workflow_relationship in diagram_data[ "workflow_relationships" ]:
            if deployed_schedule_trigger[ "id" ] == workflow_relationship[ "node" ]:
                # Find target node
                for deployed_lambda in deployed_lambdas:
                    if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
                        schedule_trigger_pairs_to_deploy.append({
                            "scheduled_trigger": deployed_schedule_trigger,
                            "target_lambda": deployed_lambda,
                        })

    schedule_trigger_targeting_futures = []
    for schedule_trigger_pair in schedule_trigger_pairs_to_deploy:
        schedule_trigger_targeting_futures.append(
            task_spawner.add_rule_target(
                credentials,
                schedule_trigger_pair[ "scheduled_trigger" ][ "name" ],
                schedule_trigger_pair[ "target_lambda" ][ "name" ],
                schedule_trigger_pair[ "target_lambda" ][ "arn" ],
                schedule_trigger_pair[ "scheduled_trigger" ][ "input_string" ]
            )
        )

    """
    Link deployed SQS queues to their target Lambdas
    """
    sqs_queue_triggers_to_deploy = []
    for deployed_sqs_queue in deployed_sqs_queues:
        for workflow_relationship in diagram_data[ "workflow_relationships" ]:
            if deployed_sqs_queue[ "id" ] == workflow_relationship[ "node" ]:
                # Find target node
                for deployed_lambda in deployed_lambdas:
                    if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
                        sqs_queue_triggers_to_deploy.append({
                            "sqs_queue_trigger": deployed_sqs_queue,
                            "target_lambda": deployed_lambda,
                        })

    sqs_queue_trigger_targeting_futures = []
    for sqs_queue_trigger in sqs_queue_triggers_to_deploy:
        sqs_queue_trigger_targeting_futures.append(
            task_spawner.map_sqs_to_lambda(
                credentials,
                sqs_queue_trigger[ "sqs_queue_trigger" ][ "arn" ],
                sqs_queue_trigger[ "target_lambda" ][ "arn" ],
                int( sqs_queue_trigger[ "sqs_queue_trigger" ][ "batch_size" ] )
            )
        )

    """
    Link deployed SNS topics to their Lambdas
    """
    sns_topic_triggers_to_deploy = []
    for deployed_sns_topic in deployed_sns_topics:
        for workflow_relationship in diagram_data[ "workflow_relationships" ]:
            if deployed_sns_topic[ "id" ] == workflow_relationship[ "node" ]:
                # Find target node
                for deployed_lambda in deployed_lambdas:
                    if deployed_lambda[ "id" ] == workflow_relationship[ "next" ]:
                        sns_topic_triggers_to_deploy.append({
                            "sns_topic_trigger": deployed_sns_topic,
                            "target_lambda": deployed_lambda,
                        })

    sns_topic_trigger_targeting_futures = []
    for sns_topic_trigger in sns_topic_triggers_to_deploy:
        sns_topic_trigger_targeting_futures.append(
            task_spawner.subscribe_lambda_to_sns_topic(
                credentials,
                sns_topic_trigger[ "sns_topic_trigger" ][ "arn" ],
                sns_topic_trigger[ "target_lambda" ][ "arn" ],
            )
        )

    # Combine API endpoints and deployed Lambdas since both are
    # Lambdas at the core and need to be warmed.
    combined_warmup_list = []
    combined_warmup_list = combined_warmup_list + json.loads(
        json.dumps(
            deployed_lambdas
        )
    )
    combined_warmup_list = combined_warmup_list + json.loads(
        json.dumps(
            deployed_api_endpoints
        )
    )

    if "warmup_concurrency_level" in project_config and project_config[ "warmup_concurrency_level" ]:
        logit( "Adding auto-warming to the deployment..." )
        warmup_concurrency_level = int( project_config[ "warmup_concurrency_level" ] )
        yield add_auto_warmup(
            task_spawner,
            credentials,
            warmup_concurrency_level,
            unique_deploy_id,
            combined_warmup_list,
            diagram_data
        )

    # Wait till are triggers are set up
    deployed_schedule_trigger_targets = yield schedule_trigger_targeting_futures
    sqs_queue_trigger_targets = yield sqs_queue_trigger_targeting_futures
    sns_topic_trigger_targets = yield sns_topic_trigger_targeting_futures

    # Make sure that log table is set up
    # It almost certainly is by this point
    yield project_log_table_future

    raise gen.Return({
        "success": True,
        "project_name": project_name,
        "project_id": project_id,
        "deployment_diagram": diagram_data,
        "project_config": project_config
    })
