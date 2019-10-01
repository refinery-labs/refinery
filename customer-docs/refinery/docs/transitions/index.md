# Transitions

Transitions are a large part of what makes Refinery an extremely powerful platform. Transitions allow different block types to be connected in a variety of ways in order to build large services and pipelines.

## Transition Types
* [`then`](#then)
* [`if`](#if)
* [`else`](#else)
* [`exception`](#exception)
* [`fan-out`](#fan-out)
* [`fan-in`](#fan-in)
* [`merge`](#merge)

## `then`

`then` is the most simple of the transitions. It will simply always pass the return data from a block to another block as input. The only time that `then` will not occur is when an exception occurs (which can be caught using the [`exception`](#exception) transition).

## `if`

`if` is useful for situations where you only want to perform a transition if the return data from a `Code Block` matches a certain condition. For example, only transition if the returned `array` or `list` has a length greater than zero. This transition carries the unique property of having a `Conditional Expression`. These are expressions which are written in Python that will cause the transition to occur if the expression evaluates to a value of `True`.

## `else`

`else` is a conditional transition which will execute if no other conditions are valid. For example, if a `Code Block` has a `then` transition along with an `if` transition with a condition expression of `len(return_data) > 0` and the `return_data` has a length of `0`, the `then` transition would be followed.

## `exception`

The `exception` transition is followed when the base `Code Block` raises an exception which is uncaught. This can be useful for situations where alerting on exceptions is necessary, or situations where recovering from a specific exception is necessary.

The following is an example of the data which is returned in an `exception` transition:
```json
{
    "input_data": 0,
    "version": "1.0.0",
    "exception_text": "Traceback (most recent call last):\n  File \"/var/task/lambda.py\", line 1089, in _init\n    return_data = main( block_input, context )\n  File \"/var/task/lambda.py\", line 4, in main\n    return ( 100 / lambda_input )\nZeroDivisionError: integer division or modulo by zero\n"
}
```

You can use this information to react differently depending on the specific details of the exception.

!!! note
	An `exception` transition will result in the `Code Block` execution not being marked as failed in the debugging view.

## `fan-out`

The `fan-out` transition takes a return value of a list of items and invokes the connected block with each item in the list as a single input. For example, if a `Code Block` returned an array of `[1, 2, 3, 4, 5]` the next `Code Block` linked with the `fan-out` transition would be called five times with the inputs of `1`, `2`, `3`, `4`, and `5` respectively. This allows for performing quick and simple concurrent processing of data. It's important to note that you are spinning up a virtual server for each item in the returned array. This is useful for when you need many machines to perform some work (converting 100 images concurrently across many machines) but it's overkill when you're attempting to do simple operations which could be accomplished in a `for` loop, for example.

!!! warning
	The `fan-out` transition is a powerful construct. It allows for developers to easily perform a large number of `Code Block` invocations without much effort. If not used carefully it can result in an excessive usage of `Code Blocks`, causing a higher-than-expected bill.

## `fan-in`

The `fan-in` transition is the sister-transition of the `fan-out` transition. Using `fan-in` you can take the output of all of the concurrently invoked `Code Blocks` and pass the return values as an array to a single `Code Block`. For example, if a `fan-out` transition executes three `Code Blocks` concurrently and they return `1`, `2`, and `3` the input to the `Code Block` connected by the `fan-in` transition will be `[2, 1, 3]`.

!!! warning
	If any uncaught exceptions occur during a `fan-out` chain the `fan-in` transition will fail to execute. It's important to ensure that all exceptions are caught to prevent breaking a down-stream `fan-in` transition.

!!! note
	The order of the returned values in the array is non-deterministic.

!!! note
	You can also have multiple nodes chained together before ending in a `fan-in` transition (instead of just a `fan-out` to a `Code Block` node to a `fan-in`). However, if all of the `Code Blocks` do not `fan-in` properly the transition will fail. This can occur in situations such as a `Code Block` reaching its max execution time, for example.

## `merge`

The `merge` transition allows you to join two separate pipelines of execution. For example, if you spawn two `Code Blocks` using two `then` transitions, you can then use two `merge` transitions to merge the results of both into a single `Code Block`.

!!! warning
	The `merge` transition currently has a known issue with high-concurrency pipelines using the same execution ID. This can occur when a `merge` is done downstream from a `fan-out` or a `Queue Block`. It is recommended that the `merge` transition only be used in non-concurrent pipeline executions for now (this will be fixed in future Refinery updates).