# The Refinery Blocks

Refinery supports a number of different node types, this documentation offers an easy reference for each one.

## The Block Types

* [Code Block](#code-block)
* [Timer Block](#timer-block)
* [Topic Block](#topic-block)
* [Queue Block](#queue-block)
* [API Endpoint Block](#api-endpoint-block)
* [API Response Block](#api-response-block)

## Code Block

A `Code Block` is a block which will run some code when it is run or transitioned to. Currently `Code Blocks` support the following languages:

* Node 8.10
* Python 2.7
* PHP 7.3
* Go 1.12

Generally speaking, `Code Blocks` make up the "meat" of a Refinery project. They contain all of the logic of your service and provide functionality that can be exposed by connecting other blocks to them.

### Input & Output

`Code Blocks` can be connected to one another in order to make more complex services. A given `Code Block` can return some data at the end of the script which will be passed as Block Input Data to any block connected to it.

For example, say we have two blocks: `Code Block A` and `Code Block B`. Say that `Code Block A` has the following code:

```python
# Code Block A
def main( lambda_input, context ):
    print( "Let's return some data!" )
    return [1,2,3,4,5]
```

And `Code Block B` has the following code:
```javascript
// Code Block B
async function main( lambda_input, context ) {
	console.log("Let's print out our input:");
	console.log(lambda_input);
	return false;
}
```

The output of the script in `Code Block B` will print the following:

```
Let's print out our input:
[ 1, 2, 3, 4, 5 ]
```

This is because the data returned from `Code Block A` is passed to `Code Block B` as input. By connecting `Code Blocks` together like this you can build highly-scalable microservices. You can imagine your data as water flowing through a pipe, it will come out of one block and go into another.


!!! info
	Note that multiple blocks will only execute in a chain fashion once deployed. In the editor view `Code Block` executions are standalone and do not trigger other blocks.

You also may have noticed that `Code Block A` and `Code Block B` are written in completely different languages. With Refinery you can build services utilizing multiple programming languages passing data to each other via transitions. The only limitation is that the returned data must be JSON-serializable (e.g. not a complex object). This covers all of the basic cases like strings, integers, arrays, etc.

### Block Options

* `Block Name`: The name of the `Code Block`.
* `Block Code`: This is the core code which will execute upon the `Code Block` being invoked. This must include the declaration of the function `main` which accepts two arguments `lambda_input` and `context`. `lambda_input` is the JSON-serializable input the `Code Block` was called with, and `context` contains metadata related to the `Code Block`'s runtime.

<video style="width: 100%" playsinlines controls autoplay muted loop>
	<source src="/blocks/images/running-code-block-fullscreen.webm" type="video/webm" />
	<source src="/blocks/images/running-code-block-fullscreen.mp4" type="video/mp4" />
</video>

You can also use the full screen editor to test and iterate on your scripts. The full screen editor allows for specifying custom Block Input Data to your script as well. This is useful for replaying issues you've encountered in your deployed service. By taking the Block Input Data from the logs and replaying it in the editor you can quickly reproduce problems and fix them accordingly.

* `Block Imported Libraries`: The libraries that should be pulled in for your `Code Block` script. Each language has support for it's own package-manager.
	* `Python 2.7`: [`pip` packages.](https://pypi.org/)
	* `Node 8.10`: [`npm` modules.](https://www.npmjs.com/)
	* `PHP 7.3`: [`composer` packages.](https://packagist.org/)
	* `Go 1.12`: This option is disabled in Go, but you can install packages by simple importing them in your Go script.

<video style="width: 100%" playsinlines controls autoplay muted loop>
	<source src="/blocks/images/adding-library-code-block.webm" type="video/webm" />
	<source src="/blocks/images/adding-library-code-block.mp4" type="video/mp4" />
</video>
	
* `Block Runtime`: The programming language for the `Code Block`. `Node 8.10`, `Python 2.7`, `PHP 7.3` and `Go 1.12` are currently the languages supported.
* `Execution Memory`: This is the allocated memory for the `Code Block` to run with. The CPU power of the `Code Block` is scaled proportional to the amount of memory allocated. If your script is taking too long to execute consider upping this.
* `Max Execution Time`: This refers to the max amount of time a `Code Block` is allowed to execute for. Setting this to a low value allows prevention of "zombie" or "runaway" `Code Block` from costing too much money with execution. The maximum time a block can execute for is 15 minutes.

### Warm & Cold Executions

The `Code Block` has one particularly interesting property that is not immediately apparent. If you execute a `Code Block` for the first time it will take a bit longer than when you execute it the second time. You will notice, especially in long chains of `Code Blocks`, that your execution time decreases significantly when the blocks have executed recently. This is because `Code Blocks` will remain "warm" after execution. The underlying AWS infrastructure will actually leave your `Code Block` scripts loaded in memory for some amount of time after an execution. By doing so, if another execution occurs shortly after, the execution can be completed much more quickly because the `Code Block` does not need to again be loaded into memory.

For more advanced reading on this topic, see [`AWS Lambda Execution Context`](https://docs.aws.amazon.com/lambda/latest/dg/running-lambda-code.html) (`Code Blocks` are AWS Lambda under the hood).

## Timer Block

Executes the `Code Blocks` which are linked to the `Timer Block` at a set interval. This can be something like every two minutes (`rate(2 minutes)`), every day at 5:00 PM, etc. Useful for operations which need to occur on a regular schedule in an a highly-reliable manner (e.g. an uptime checker).

### Settings
* `Block Name`: The name of the `Timer Block`
* `Schedule Expression`: An expression which defines how often the trigger should fire the connected `Code Blocks`. This follows the [AWS CloudWatch expression formats which are described here.](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html) Valid values include `rate(1 minute)` and `cron(*/2 * * * ? *)`.
* `Block Input Data`: JSON-serializable data which can be optionally passed as input to the connected `Code Blocks` when the `Timer Block` fires.

## Topic Block

Execute `Code Blocks` which are linked to it with the contents of the published topic. `Topic Blocks` are useful for situations where you want to execute multiple `Code Blocks` at the same time with the same input. This is often referred to as a ["pub-sub" pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern). In contrast to the `Queue Block`, for example, an `Topic Block` has no concept of retries, queueing or polling.

As an example, if you passed some Block Input Data of `[1,2,3,4,5]` to a `Topic Block` and the block was connected to three `Code Blocks`, every connected `Code Block` would be executed in parallel with the input of `[1,2,3,4,5]`.

### Settings
* `Name`: The name of the `Topic Block`

## Queue Block

Creates an queue which can be linked to a `Code Block` in order to trigger the block when something is put onto the queue. A connected `Code Block` will poll the queue for new items and upon finding some will automatically run with the items as input. The number of concurrent `Code Block` executions will automatically increase to meet demand if the items in the queue are not being emptied fast enough. This is "magic scaling" to meet the demand.

!!! warning
	It is important to know that having multiple `Code Blocks` connected to a single `Queue Block` will likely not work the way you expect. Since `Code Blocks` operate in a "polling" fashion, the messages will not be split up or duplicated across multiple `Code Blocks` connected to the queue. Instead messages will randomly flow into the connected `Code Blocks` in no structured way. For a simple way to invoke multiple `Code Blocks` with the same input, see the `Topic Block` section.
	
### Settings
* `Name`: The name of the `Queue Block`
* `Batch Size`: The number of messages to pass into the connect `Code Blocks` as JSON-serializable input. This can be up to 10 total messages at a time. This is useful when you want to "batch" your processing to save on computation costs or to speed up processing.

## API Endpoint Block

The `API Endpoint Block` represents a single RESTful HTTP endpoint. Upon hitting the generated HTTP endpoint the connected `Code Blocks` will be triggered with the parameters and other HTTP request metadata passed as input. `API Endpoints Block` are useful for situations such as building a REST API on top of serverless, creating pipelines triggered by [webhooks](https://sendgrid.com/blog/whats-webhook/), and more. It's important to note that at a minimum an `API Endpoint Block` must be connected to a `Code Block` and the `Code Block` (or some `Code Block` in the pipeline) must transition into an `API Response` block.

!!! warning
	As of this time, AWS has a [hard limit](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table) of 29 seconds before timing out HTTP requests made to [API Gateways](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) (which are what API Endpoints deploy as). This complicates using API Endpoints for RESTful APIs because of the likelyhood of the computation taking longer than 29 seconds to finish (resulting in the API Gateway timing out).
	
### Settings
* `Name`: The name of the API Endpoint
* `HTTP Method`: The HTTP method for the API Endpoint to accept. Note that there can be multiple endpoints with the same path but with different HTTP methods.
* `Path`: The HTTP path.

## API Response Block

`API Response Block` is a block which will return the data returned from a linked `Code Block` as an HTTP response. An `API Response Block` is used downstream in a chain of `Code Blocks` which started with an API Endpoint trigger. Note that due to the [hard AWS  limit](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table) of 29 seconds before API Endpoints time out, the transition to an API Response must occur in this time frame. If the pipeline execution starts with an API Endpoint and the intermediary `Code Block` executions take longer than 29 seconds the request will time out.

If the data passed as input to the `API Response Block` does not contain the `body` key, then the data will be returned as a JSON blob in a HTTP response with the `Content-Type` set to `application/json`. For finer-grained control over the HTTP response, such as the ability to set headers, status codes, and more, return a JSON structure which complies with the proper format for [AWS HTTP responses](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format).