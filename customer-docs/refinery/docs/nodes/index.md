# Nodes

Refinery supports a number of different node types, this documentation offers an easy reference for each one.

## Node Types

* [Lambda](#lambda)
* [Schedule Trigger](#schedule-trigger)
* [SNS Topic Trigger](#sns-topic-trigger)
* [SQS Queue Trigger](##sqs-queue-trigger)
* [API Endpoint](#api-endpoint)
* [API Response](#api-response)

## Lambda

The Lambda node type is a node which executes code from one of Refinery's supported languages (currently only Python 2.7). This deploys to an [AWS Lambda](https://aws.amazon.com/lambda/). Lambdas can take and return JSON-serializable data structures, and are subject to the limits described in the [AWS Lambda Limits](https://docs.aws.amazon.com/lambda/latest/dg/limits.html). These nodes make up the "meat" of most pipelines, performing small, functional operations as part of a bigger set of actions.

Lambda's can also be saved and re-used easily, click the `Save Lambda in Database` button in the Lambda menu to save a given Lambda for later use.

### Settings

* `Name`: The name of the Lambda node.
* `Language`: The programming language for the Lambda, currently only Python 2.7 is supported.
* `Import(s)`: A list of libraries and packages used by the Lambda.
	* For `Python 2.7` Lambdas, any valid syntax for `pip` requirements files will work here. For more information on the format see [the `pip` documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files).
* `Code`: This is the core code which will execute upon the Lambda being invoked. This must include the declaration of the function `main` which accepts two arguments `lambda_input` and `context`. `lambda_input` is the JSON-serializable input the Lambda was called with, and `context` contains metadata related to the Lambda's runtime.
* `Execution Memory`: This is the allocated memory for the Lambda to run with. The CPU power of the Lambda is scaled proportional to the amount of memory allocated. This factors into the costs of execution a given Lambda.
* `Max Execution Time`: This refers to the max amount of time a Lambda is allowed to execute for. Setting this to a low value allows prevention of "zombie" or "runaway" Lambdas from costing too much money with execution.
* `Layers`: The [Lambda layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html) menu option allows for specifying the ARNs of Lambda layers for the Lambda to be deployed with. This allows for the addition of binaries, libraries, and even custom runtimes into a given Lambda.
* `Environment Variables`: This allows for specifying environment variables for the given Lambda. [Environment variables](https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html) allow for better seperation between configuration and code and can be changed in deployed pipelines without requiring a re-deploy.

### Options

* `Update Lambda`: Saves updates to the selected Lambda. This does not save the project, in order to save the project you must click the `Save Project` button.
* `Environment Variables`: Allows for changing the environment variables of a given Lambda.
* `Delete Lambda`: Deletes the selected Lambda along with any transitions to and from the node.
* `Add Transition`: Adds a transition to the Lambda, for more information on the different transition types see the [`Transitions` section of this documentation.](/transitions/)
* `Run Lambda`: Runs the Lambda with no specified input.
* `Duplicate Lambda`: Duplicates the currently selected Lambda and automatically renames the duplicate Lambda to not conflict with the original.
* `Save Lambda in Database`: Saves the Lambda to the `Saved Lambdas` database. This allows you to add it to other projects by selecting `Saved Lambda` from the `Add New Resource` dropdown.

## Schedule Trigger

Executes the nodes which are linked to the `Schedule Trigger` node at a set interval. This can be something like every minute, every day at 5:00 PM, etc. Useful for operations which need to occur on a schedule in an a highly-reliable manner. This deploys as an [AWS CloudWatch Event](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/WhatIsCloudWatchEvents.html) and can pass an optional JSON-serializable input to the connected nodes.

### Settings
* `Name`: The name of the Schedule Trigger
* `Schedule Expression`: An expression which defines how often the trigger should fire the connected nodes. This follows the [AWS CloudWatch expression formats which are described here.](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html). Valid values include `rate(1 minute)` and `cron(*/2 * * * ? *)`.
* `Description`: A simple description of what the trigger is meant to do. This field is optional but useful for documentation.
* `Input Data`: JSON-serializable data which can be optionally passed as input to the connected nodes when the trigger fires.

### Options
* `Update Schedule Trigger`: Updates the selected node with the updated settings. This does not save the project, in order to save the project you must click the `Save Project` button.
* `Add Transition`: Adds a transition to the node, for more information on the different transition types see the [`Transitions` section of this documentation.](/transitions/)
* `Delete Schedule Trigger`:  Deletes the selected node along with any transitions to and from the node.

## SNS Topic Trigger

Execute nodes which are linked to it with the contents of the published [SNS topic](https://docs.aws.amazon.com/sns/latest/dg/welcome.html). SNS topics are useful for situations where you want to execute multiple Lambdas at the same time with the same input published to a given topic. This is often referred to as a ["pub-sub" pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern). In contrast to the `SQS Queue Trigger`, for example, an SNS topic has no concept of retries, queueing or polling.

### Settings
* `Name`: The name of the SNS Topic Trigger

### Options
* `Update SNS Topic Trigger`: Updates the selected node with the updated settings. This does not save the project, in order to save the project you must click the `Save Project` button.
* `Add Transition`: Adds a transition to the node, for more information on the different transition types see the [`Transitions` section of this documentation.](/transitions/)
* `Delete SNS Topic`:  Deletes the selected node along with any transitions to and from the node.

## SQS Queue Trigger

Creates an [AWS SQS Queue](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html) which can be linked to Lambda nodes in order to set these nodes as ["pollers" of the given SQS queue](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html). Currently only [Standard SQS queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html) can be created as [FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html) do not support Lambda as a trigger. [Click here to read me about the difference between AWS standard and FIFO queues.](https://aws.amazon.com/sqs/features/#Queue_types). This node makes sense for situations where you want automatic retries on messages which result in an exception being thrown on the connected Lambda node. The number of concurrent Lambda executions will scale upwards until the maximum is reached to handle the queue load. This scaling behavior is described in the ["Understanding Scaling Behavior" AWS documentation.](https://docs.aws.amazon.com/lambda/latest/dg/scaling.html).

!!! warning
	It is important to know that having multiple Lambda nodes connected to a single SQS queue will likely not work the way you expect. Since AWS Lambdas operate in a "polling" fashion, the messages will not be split up or duplicated across multiple Lambdas connected to the queue. Instead messages will randomly flow into the connected Lambdas in no structured way. For a simple way to invoke multiple Lambdas with the same input, see the SNS Topic Trigger section. More information on SNS vs SQS can be found here.
	
### Settings
* `Name`: The name of the SQS Queue Trigger
* `Batch Size`: The number of messages to pass into the connect Lambdas as JSON-serializable input. This can be up to 10 total messages.
* `Content-Based De-duplication`: Options to de-duplicate messages placed onto the SQS queue based on their contents. The max de-duplication window is five minutes.

### Options
* `Update SQS Queue`: Updates the selected node with the updated settings. This does not save the project, in order to save the project you must click the `Save Project` button.
* `Add Transition`: Adds a transition to the node, for more information on the different transition types see the [`Transitions` section of this documentation.](/transitions/)
* `Delete SQS Queue`:  Deletes the selected node along with any transitions to and from the node.

## API Endpoint

The API Endpoint node represents a single RESTful HTTP endpoint. Upon hitting the generated HTTP endpoint the connected Lambda nodes will be triggered with the parameters and other HTTP request metadata passed as input. API endpoints are useful for situations such as building a REST API on top of serverless, creating pipelines triggered by [webhooks](https://sendgrid.com/blog/whats-webhook/), and more. It's important to note that at a minimum an API Endpoint must be connected to a Lambda node and the Lambda node (or some Lambda node in the pipeline) must transition into an `API Response` node.

!!! warning
	As of this time, AWS has a [hard limit](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table) of 29 seconds before timing out HTTP requests made to [API Gateways](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) (which are what API Endpoints deploy as). This complicates using API Endpoints for RESTful APIs because of the likelyhood of the computation taking longer than 29 seconds to finish (resulting in the API Gateway timing out).
	
### Settings
* `Name`: The name of the API Endpoint
* `HTTP Method`: The HTTP method for the API Endpoint to accept. Note that there can be multiple endpoints with the same path but with different HTTP methods.
* `Path`: The HTTP path.

### Options
* `Update API Endpoint`: Updates the selected node with the updated settings. This does not save the project, in order to save the project you must click the `Save Project` button.
* `Add Transition`: Adds a transition to the node, for more information on the different transition types see the [`Transitions` section of this documentation.](/transitions/)
* `Delete API Endpoint`:  Deletes the selected node along with any transitions to and from the node.

## API Response

API Response is a node which will return the data returned from a linked Lambda as an HTTP response. An API Response node is used downstream in a chain of Lambdas which started with an API Endpoint trigger. Note that due to the [hard AWS  limit](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table) of 29 seconds before API Endpoints time out, the transition to an API Response must occur in this time frame. If the pipeline execution starts with an API Endpoint and the intermediary node executions take longer than 29 seconds the request will time out.

If the data passed as input to the API Response node does not contain the `body` key, then the data will be returned as a JSON blob in a HTTP response with the `Content-Type` set to `application/json`. For finer-grained control over the HTTP response, such as the ability to set headers, status codes, and more, return a JSON structure which complies with the proper format for [1AWS HTTP responses](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format).