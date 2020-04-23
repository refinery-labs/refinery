#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import tornado.ioloop
import tornado.web
import sys

import unicodecsv as csv

from app import TornadoBindingSpec, TornadoApp, WebsocketApp
from assistants.aws_account_management.preterraform import PreterraformManager
from assistants.aws_clients.aws_clients_assistant import STSClientBindingSpec, AwsClientFactory
from assistants.billing.billing_assistant import BillingSpawner
from assistants.deployments.api_gateway import ApiGatewayManager
from assistants.deployments.awslambda import LambdaManager
from assistants.deployments.dangling_resources import AwsResourceEnumerator
from assistants.deployments.schedule_trigger import ScheduleTriggerManager
from assistants.deployments.sns import SnsManager
from assistants.deployments.sqs import SqsManager
from assistants.github.github_assistant import GithubAssistant
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from assistants.user_creation_assistant import UserCreationAssistant
from config.provider import ConfigBindingSpec
from controller.auth.github.oauth_provider import GithubOAuthProviderBindingSpec
from services.auth.oauth_service import OAuthServiceBindingSpec

from services.aws.clients import AWSClientBindingSpec
from services.project_inventory.project_inventory_service import ProjectInventoryService
from services.stripe.stripe_service import StripeService
from services.user_management.user_management_service import UserManagementService
from utils.general import logit, UtilsBindingSpec
from assistants.deployments.ecs_builders import BuilderManager, AwsEcsManager

from services.websocket_router import ScheduledHeartbeatRunner, WebsocketRouter

from models.initiate_database import *

try:
	# for Python 2.x
	from StringIO import StringIO
except ImportError:
	# for Python 3.x
	from io import StringIO

# noinspection PyBroadException
try:
	# for Python 2.x
	# noinspection PyCompatibility
	reload( sys )
except Exception:
	# for Python 3.4+
	# noinspection PyUnresolvedReferences
	from importlib import reload
	reload( sys )

sys.setdefaultencoding( "utf8" )

# Increase CSV field size to be the max
csv.field_size_limit( sys.maxsize )


if __name__ == "__main__":
	logit( "Starting the Refinery service...", "info" )

	"""
	NOTE: Classes added here must have camel casing without two capitol letters back to back.
	
	For example, the name "AWSManager" would not be valid as "A" is followed by another uppercase
	letter "W". We would write this class as "AwsManager". Alternatively, you can create a
	BindingSpec which provides "aws_manager" and return an instance of the class (where naming
	will not matter).
	"""
	dep_classes = [
		ApiGatewayManager,
		LambdaManager,
		ScheduleTriggerManager,
		SnsManager,
		SqsManager,
		BuilderManager,
		PreterraformManager,
		AwsEcsManager,
		BillingSpawner,
		UserCreationAssistant,
		AwsClientFactory,
		AwsResourceEnumerator,
		WebsocketRouter,
		TaskSpawner,
		ProjectInventoryService,
		StripeService,
		UserManagementService,
		GithubAssistant
	]

	binding_specs = [
		UtilsBindingSpec(),
		DatabaseBindingSpec(),
		ConfigBindingSpec(),
		AWSClientBindingSpec(),
		STSClientBindingSpec(),
		TornadoBindingSpec(),
		GithubOAuthProviderBindingSpec(),
		OAuthServiceBindingSpec()
	]
	app_object_graph = pinject.new_object_graph(modules=[], classes=dep_classes, binding_specs=binding_specs)

	tornado_app = app_object_graph.provide(TornadoApp)
	server = tornado_app.new_server( app_object_graph )
	server.bind(
		7777
	)

	# Start websocket server
	websocket_app = app_object_graph.provide(WebsocketApp)
	websocket_server = websocket_app.new_server( app_object_graph )
	websocket_server.bind(
		3333
	)

	# Start scheduled heartbeats for WebSocket server
	websocket_heartbeat_runner = app_object_graph.provide(ScheduledHeartbeatRunner)
	websocket_heartbeat_runner.start()

	# Creates tables for any new models
	# This is commented out by default because it makes Alembic autogenerated migrations not work
	# (unless you drop the tables manually before you auto-generate)
	# Base.metadata.create_all( engine )

	server.start()
	websocket_server.start()
	tornado.ioloop.IOLoop.current().start()