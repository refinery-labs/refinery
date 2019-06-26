# Debugging & Logging

Debugging in serverless environments can often be a complex chore which feels like working with a [black box](https://en.wikipedia.org/wiki/Black_box). Refinery attempts to greately simplify the debugging process through the use of its scalable logging system built on top of S3. The logging system in Refinery is configurable and allows for extreme verbosity when needed to help pinpoint and easily reproduce problems.

## What Refinery Logs

Before we dive into debugging your service, we first have to talk about logging. Refinery logs a large amount of metadata about a `Code Block`'s given execution. For example, some of the data which is logged is the following:

* The full input to the `Code Block`.
* The full returned output of the `Code Block`.
* All `stdout` and `stderr` outputted during execution.
* Time of execution.

The reason for this level of verbosity is to allow easy reproduction of issues. Since development in Refinery is accomplished by building small functional blocks in a pipeline fashion, logging the full input and output allows developers to easy replay the same inputs into the same blocks in the IDE in order to replicate the issue.

## Configuring Your Logging Level

Refinery allows for configuring different levels of logging for when your service is deployed in production. The levels of logging available are:

* `Log all executions`: Every time a `Code Block` is executed a log file is written.
* `Log only errors`: A log file is written only when a `Code Block` encounters an uncaught exception.
* `No logging`: No logs are written under any circumstance.

The major tradeoff with logging all executions, error only logging, and no logging is cost. The `Code Blocks` that Refinery deploys make use of S3 for storing of all of the created log objects. This means that you will incur the appropriate level of cost for each write you do to S3. As of the time of this writing, saving an object to S3 is billed at [$0.005 per 1,000 requests](https://aws.amazon.com/s3/pricing/#S3_Standard). While this may seem inexpensive, it can add up if you're doing full verbosity logging on pipelines with a large number of executions. It's important to always be mindful about the amount of resources you're consuming when using Refinery.

In order to configure your logging level for a given project, navigate to the `Settings` tab for your project. Change the drop-down selection for `Logging Level` to change your logging level.

<video style="width: 100%" controls autoplay muted loop>
	<source src="/debugging/images/changing-logging-level.webm" type="video/webm" />
	<source src="/debugging/images/changing-logging-level.mp4" type="video/mp4" />
</video>

!!! note
	Changes in logging level currently require a re-deploy to take effect. Just changing the setting will not automatically change an existing deployment's logging settings.

## Debugging a Deployment

<video style="width: 100%" controls autoplay muted loop>
	<source src="/debugging/images/finding-errors-with-block-executions.webm" type="video/webm" />
	<source src="/debugging/images/finding-errors-with-block-executions.mp4" type="video/mp4" />
</video>

To debug an existing deployment navigate to the `Deployment` tab of your project. Once you've done so click on the `Block Executions` button on the left side of the page.

The `Block Executions` panel shows a list of executions which have occurred for this deployment. These executions are grouped into "execution pipelines", which means that you can follow a chain of executions from the start to the end of the chain. This allows you to follow the flow of execution in your deployed service and better understand the chain of events that led to a particular error or bug.

Once you select a given execution pipeline from the list you'll see that the `Code Blocks` are marked as successful <img src="/debugging/images/code-block-success.png" style="width: 25px; height: 25px;" /> or unsuccessful <img src="/debugging/images/code-block-error.png" style="width: 25px; height: 25px;" />. These indicate whether or not your `Code Block` encountered an uncaught exception or if it executed successfully without issue.

For ongoing executions the `Code Blocks` will automatically update as the execution continues. As can be seen in the above video the final code block in the execution pipeline automatically updates after its execution completes.

## Investigate a Code Block Execution

To investigate a given `Code Block` in an execution pipeline you can click on the relevant `Code Block` (<img src="/debugging/images/code-block-success.png" style="width: 25px; height: 25px;" />/<img src="/debugging/images/code-block-error.png" style="width: 25px; height: 25px;" />) to see information about its execution. This information is displayed under the `Execution Details` tab of the `Block Execution Logs` pane.

The following information is provided about `Code Block` execution:

* `Time`: The time the `Code Block` executed.
* `Status`: This is the execution status of the selected `Code Block`. For example, this would be `Success` if the block executed successfully or `Uncaught Exception` if an uncaught exception occurred.
* `Block Input Data`: This is the data that was passed to the `Code Block` from a previous block. For example, if the previous `Code Block` returned `[1,2,3,4]` and transitioned to the current block its Block Input Data would be `[1,2,3,4]`.
* `Execution Output`: The execution output is all of the output your `Code Block` produced during its execution. This includes statements intentionally printed or logged as well as full stack-traces when errors occur.
* `Return Data`: The data returned from the selected `Code Block`. If the currently-selected `Code Block` returned the string `"example"`, this would be shown in the return data section.

Additionally you can view read-only information about the deployed `Code Block` (such as the code contents) by selecting the `Selected Block` tab.

## Reproduce a Deployed Code Block Issue in the Editor

<video style="width: 100%" controls autoplay muted loop>
	<source src="/debugging/images/replay-input-in-editor.webm" type="video/webm" />
	<source src="/debugging/images/replay-input-in-editor.mp4" type="video/mp4" />
</video>

Refinery allows you to very easily reproduce errors encountered in deployed `Code Blocks` due to the fact that it can log the full Block Input Data passed to the block at execution time. You can reproduce the bug and fix the problem by copying the `Block Input Data` and pasting it into the `Block Input Data` field when running the same block in the `Editor` tab.

## Execution Pipeline Grouping

These execution pipelines are grouped by the initiating trigger that caused the pipeline to start executing. For example, if a deployed project had a `Timer Block` connected to two `Code Blocks` each attached Code Block would be grouped into it's own execution pipeline. However if a deployed project had a `Timer Block` connected to a `Code Block` which is connected to another `Code Block` - they would all be grouped into the same execution pipeline.