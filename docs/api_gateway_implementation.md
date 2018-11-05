# API Gateway Implementation

## Summary

There are two different types of API Gateways which can be used.

* Create an endpoint API Gateway
* Create a corresponding Lambda which will create a reference in redis to be filled out when the execution pipeline completes.
	* This Lambda polls redis every second to check if a response has been created.
	* If the Lambda reaches 27 seconds and no response is returned it will immediately return the following JSON:

	```
	{
		"request_id": {{UUID}},
		"status": "PENDING",
		"msg": "This request has taken longer than the maximum allowed AWS API Gateway timeout. For this reason it is now executing in the background and can be retrieved by hitting this endpoint again ",
	}
	```

	* This `request_id` can now be used against the same endpoint to query 