# Effortless Serverless Map Reduce

Refinery allows you to do effortless map reduce in order to spread your compute across hundreds (or thousands) of machines. This doesn't require writing any new code or integrating with any API frameworks.

!!! note
	If you don't care about collecting all the results from the map part of your map-reduce you should probably use a [`Queue Block`](/blocks/#queue-block) instead. Queues are a much more efficient and speedy way to process a large number of items when you don't care about merging all of the results immediately at the end.

!!! important
	Refinery makes it very easy to use a large number of machines to do concurrent computation. The ease of use can be problematic in that it also makes it easy to run up a large bill with little effort. While the cost of spinning up and using 1,000 virtual servers in Refinery is an order of magnitude cheaper than conventional hosts, it's not free. You should always carefully consider the resources being used and should calculate your costs appropriately.

## Creating a Serverless Map Reduce Pipeline

A map reduce pipeline in Refinery consists of at least three parts. The following is an example Refinery diagram of this:

<center>
	<img src="/tutorials/fan-out-fan-in/media/fan-out-fan-in-example.png" />
</center>

One Code Block to return an array of items to be distributed to workers, one Code Block to do work on a single item in the array, and one Code Block to get the results as an array.

The following are an example of the `Code Block` for each:

* `Code Block #1`: which returns an array of items to be distributed to the worker machines. This is as simple as return an array like `[1,2,3,4,5]`. The following code is an example of this:

``` python
def main(block_input, backpack):
    return_list = []
    
    # Generate a list of 100 numbers in an array
    for i in range( 0, 100 ):
        return_list.append(
            i
        )
       
    # Return the array
    return return_list
```

* `Code Block #2` (connected to `Code Block #1` via a `fan-out` transition): which does an operation on a single item of the array. This is the `Code Block` which does the computationally-intensive work you would want to use a map reduce for. A very basic example is the following which just takes an item from the above returned number array and doubles it:

``` python
def main(block_input, backpack):
	# Multiply the item by two and return the new value
    return ( block_input * 2 )
```

While this example is trivial (and not a good use-case for `fan-in` and `fan-out`), it demonstrates the format that the `fan-out` data will use when passing data between `Code Blocks`.

* `Code Block #3` (connected to `Code Block #2` via a `fan-in` transition): which is passed an array of the returned values from all of the executions of `Code Block #2`. In our example case, the array passed to this final code block would be `[2,4,6,8,10]`.

## Example Fan-Out & Fan-In Execution

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/tutorials/fan-out-fan-in/media/fan-out-run-example.webm" type="video/webm" />
	<source src="/tutorials/fan-out-fan-in/media/fan-out-run-example.mp4" type="video/mp4" />
</video>

The above video demonstrates an execution of the example mentioned previously. Once we execute the first `Code Block` the second `Code Block` is fanned-out to so that it executes 100 times (1 per each item returned by the first `Code Block`).

Using the `Block Executions` debugging utility we can easily see the input data and output data to each block. The video shows that the first `Code Block` returns an array of 100 numbers. The second `Code Block` (connected to the first via a `fan-out`) executed 100 times which each individual number as an input. Finally, the third `Code Block` (connected to the first via a `fan-in`) received an array of 100 return values from the second `Code Block`.

!!! note
	It's important to note that you don't immediately have to `fan-in` after doing a `fan-out`. You can do multiple `then` transitions and then eventually do a `fan-in` with the results.

!!! important
	It's important to ensure that before doing a `fan-in` you've not increased or decreased the number of parallel executions. For example if you do an `if` transition and only do a `fan-in` with fifty executions instead of the originally fanned-out 100 executions - that won't work. For the same reason, it's important to note that all of your executions between a `fan-out` and a `fan-in` must not result in an uncaught exception. This will break a `fan-in` for the same reason: the number of executions coming to a `fan-in` is less than the number of executions from the previous `fan-out`.

## Limits of Fan-Outs & Fan-Ins (and other considerations)

By default, your Refinery account has an execution limit of 1,000 concurrent executions across all of your projects. This is purely an account-level limit which can be raised if more capacity is required. However, a 1,000 concurrency limit does **not** mean that you are limited to only fanning-out to less than 1,000 items. You can still do a `fan-out` of more than 1,000 items and it will work the same way. This is because, generally speaking, Refinery pipelines will only *slow down* when dealing with extreme load (see the exception to this in the warning below). When the 1,000 concurrent execution limit is hit the additional executions that need to be performed are simply queued up to be retried once more execution capacity is available. In the context of a `fan-out` this just means that the 10,000 executions will take a bit longer to execute.

The following example demonstrates this:

* A `Code Block` does a `fan-out` with an array of 10,000 items.
* While our system executes the connected `Code Block` 10,000 times, the default concurrency limit is hit (1,000 concurrent executions). Instead of failing, the executions are simply queued up to be retried later.
* Some of the previously-running `Code Blocks` finish executing. The queued up `Code Blocks` which couldn't execute previously are now executed since there is available capacity for them.
* Eventually all the `Code Blocks` in the `fan-out` finish executing and the `Code Block` connected via the `fan-in` is executed with the results passed as input.

In this example, the entire pipeline works as expected but at a slightly slower pace.

!!! important
	As a reminder, if you don't need to do the `fan-in` part you should utilize the `Queue Block` instead. The `Queue Block` offers significant advantages in terms of speed, cost, and automatic scaling.

!!! warning
	Currently, doing a `fan-out` that results in hitting your max concurrency limit (default of 1,000 concurrent executions for Refinery accounts) can cause some requests to API Endpoints to fail. This is because API Endpoints need to execute the attached `Code Blocks` to respond to the web request. When the execution capacity is maxed out the `Code Block` execution will fail and an error will be returned for the request. This is unique in Refinery because most pipelines will handle a maxed-out capacity situation by simply slowing down instead of breaking. In future releases of Refinery this problem will be completely fixed but as of this time it is important to note this limitation.
	
	As a temporary workaround, multiple Refinery accounts can be used to avoid this problem. One Refinery account is used for real-time sensitive projects and one Refinery account is used for non-real-time sensitive projects.