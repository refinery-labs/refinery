# Fan Out Design

## Summary

Fan-out design refers to when you want to return a list of JSON-serializable objects and have each object 
in the list be spawned into its own Lambda as the argument. This is a **new** transition type which allows for quick processing of a large list of items.

# Diagram

```

        [λ] <-- Lambda returns an array with a fan-out transition
		 |
		 |
		/|\
	   / | \
	  /  |  \
	 /   |   \
   [λ]  [λ]  [λ] <-- len(return_array) number of Lambda(s) execute with
 	\    |    /      each element of the array as a single input.
	 \   |   /
	  \  |  /
	   \ | /
        \|/
		[λ] <-- An array of the Lambda(s) return values is input to the
                fan-in Lambda.

```

## How it works

* The Lambda returns an array of results
* The Lambda generates a fan-out UUID `fan_out_id` and appends it to the `fan_out_ids` list to keep track of the fan-out process.
* The Lambda writes an integer of the number of input(s) to Redis under `FAN_IN_COUNTER_{{fan_out_id}}`
	* This will be decremented each time one of the fanned functions completes using a transaction.
* Using Redis pipelining each item in the array is:
	* JSON-serialized, with `_refinery` metadata added to indicate it is part of a fan-out execution.
		* `_fan_out_id` is added to the input data of the fan-out Lambda(s). This is used during the execution of each fanned-out Lambda.
	* Stored in redis with an expiration time of `self.return_data_timeout` (16 minutes)
* All of the Lambdas will then be invoked async with the data previously stored

# Lambda Fan-Out Execution(s)
* The Lambda checks for the `_fan_out_id`, if it exists then the Lambda executes in "fan-out" mode.
* The Lambda executes using the input as usual.
* Upon finishing the Lambda does the following (in a redis pipeline/transaction). This happens in exceptions as well.
	* Pushes its JSON-serialized result data to `{{fan_out_id}}_RESULTS`
	* Decrements `{{fan_out_id}}_FAN_OUT_COUNTER`
	* Checks the value of the `{{fan_out_id}}_FAN_OUT_COUNTER` to see if it equals zero.
		* If it's equal to zero then the "Last Fan-Out Lambda Execution" is performed.

# Last Fan-Out Lambda Execution

Upon the final Lambda in the fan-out finishing execution the following steps occur in one redis transaction.

* The `{{fan_out_id}}_FAN_OUT_COUNTER` is deleted
* The ARN retrieved from `{{fan_out_id}}_FAN_IN_ARN` is invoked with the `["_refinery"]["indirect"]["key"]` set to the key `{{fan_out_id}}_RESULTS`. This will result in the next Lambda taking the result(s) array as input (may be a type-issue here) and then it will be deleted after the next Lambda is invoked.