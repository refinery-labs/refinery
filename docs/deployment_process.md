# Refinery Deployment Process

## Steps

### Conditional Analysis & Lambda Tagging
* Analyze all transitions between Lambdas
	* Add transitions info to the Lambda nodes metadata, for example "if `return_data["count"] > 0` then execute `start_loop` Lambda". This metadata is read during the "Lambda Baking" portion of the deployment process.
* For any places where a transition invokes multiple Lambdas, create a *Parallel Spawner Lambda* to bridge this and update relationships/flows.

### Create & Configure Preamble Resources
* Create SQS Queues

### Lambda Baking

* Add in pre-execution and post-execution code into each Lambda (see `lambda_baking.md` for more information)

### Create & Configure Postamble Resources
* Create Cloudwatch Events and set target Lambdas as triggers
* Set Lambdas as SQS triggers (if there are multiple Lambdas as targets, then this will be a *Parallel Spawner Lambda*).

# Reference
## Lambda Baking
Lambda Baking is the process of adding in extra logic to the beginning and end of a given Lambda. This extra logic is extra code added after the regular execution to do things like spawning another Lambda, pushing the return data onto an SQS queue, etc.

## Parallel Spawner Lambda
This is a Lambda which purely takes some input and spawns multiple Lambdas with that same input as their input. This has to be a separate Lambda instead of being baked because the 