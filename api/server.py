#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import asyncio

import tornado.ioloop
import tornado.web
import sys

from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from app import TornadoBindingSpec, TornadoApp, WebsocketApp, NodeJsBuilder, PythonBuilder
from assistants.aws_account_management.preterraform import PreterraformManager
from assistants.aws_clients.aws_clients_assistant import STSClientBindingSpec, AwsClientFactory
from assistants.billing.billing_assistant import BillingSpawner
from assistants.deployments.api_gateway import ApiGatewayManager
from assistants.deployments.awslambda import LambdaManager
from assistants.deployments.dangling_resources import AwsResourceEnumerator
from assistants.deployments.schedule_trigger import ScheduleTriggerManager
from assistants.deployments.serverless.build_secure_resolver import BuildSecureResolver
from assistants.deployments.serverless.deploy import ServerlessDeployAssistant
from assistants.deployments.sns import SnsManager
from assistants.deployments.sqs import SqsManager
from assistants.github.github_assistant import GithubAssistant
from assistants.task_spawner.task_spawner_assistant import TaskSpawner
from assistants.user_creation_assistant import UserCreationAssistant
from config.provider import ConfigBindingSpec
from assistants.github.oauth_provider import GithubOAuthProviderBindingSpec
from deployment.deployment_manager import DeploymentManager
from deployment.serverless.module_builder import ServerlessModuleBuilder
from services.auth.oauth_service import OAuthServiceBindingSpec

from services.aws.clients import AWSClientBindingSpec
from services.workflow_manager.workflow_manager_service import WorkflowManagerService
from services.project_inventory.project_inventory_service import ProjectInventoryService
from services.stripe.stripe_service import StripeService
from services.user_management.user_management_service import UserManagementService
from tasks.build.temporal.code_builder_factory import CodeBuilderFactory
from utils.general import logit, UtilsBindingSpec
from assistants.deployments.ecs_builders import BuilderManager, AwsEcsManager

from services.websocket_router import ScheduledHeartbeatRunner, WebsocketRouter

from models.initiate_database import *
from sys import maxsize
from csv import field_size_limit

# Increase CSV field size to be the max
field_size_limit(maxsize)


if __name__ == "__main__":
    #import debugpy
    #debugpy.listen(('0.0.0.0', 5678))
    #logit("Starting the Refinery service...", "info")

    """
    NOTE: Classes added here must have camel casing without two capital letters back to back.

    For example, the name "AWSManager" would not be valid as "A" is followed by another uppercase
    letter "W". We would write this class as "AwsManager". Alternatively, you can create a
    BindingSpec which provides "aws_manager" and return an instance of the class (where naming
    will not matter).
    """
    dep_classes = [
        DeploymentManager,
        ApiGatewayManager,
        BuildSecureResolver,
        ServerlessDeployAssistant,
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
        GithubAssistant,
        WorkflowManagerService,
        CodeBuilderFactory,
        NodeJsBuilder,
        PythonBuilder,
        ServerlessModuleBuilder
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

    # debug object graph
    # print(app_object_graph._obj_provider._binding_mapping._binding_key_to_binding.keys())

    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

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
    #from config.provider import load_app_config
    #from models.initiate_database import get_refinery_engine
    #app_config = load_app_config()
    #engine = get_refinery_engine(app_config)
    #Base.metadata.create_all(engine)

    server.start()
    websocket_server.start()
    tornado.ioloop.IOLoop.current().start()
