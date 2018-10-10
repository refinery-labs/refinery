# The Lambda Baking Process

Lambda Baking is the process of adding in additional functionality to a deployed Lambda outside of the code specified by the user. This is where a lot of the "magic" is added into the process such as initializing helper objects for the runtime, performing logging, and adding in tracing.

## Lambda Execution Steps

* Set up runtime helper objects
	* Set up "Runtime Memory" methods
	* Set up "Config Memory" methods
* Set up Lambda input data
	* Resolve indirect input data if it's not self-contained in Lambda payload body (done if return data size is >5MB)
		* Redis is a possible storage location (depending on pipeline config)
		* S3 is a possible storage location (depending on pipeline config)
	* Convert return data from JSON or MessagePack into native language data types
* Log that the Lambda execution has started at X time
* Log pipeline execution ID and node ID details
* If "Debugging" enabled
	* Log all input data state
* If the Lambda has a JSON schema, validate it and throw an exception if it doesn't match.
* Monkeypatch runtime to capture all output (e.g. `print` statements, etc) for debugging.
* Set up global exception handling for Lambda code.
* Run the user's Lambda code until completion
* Log that Lambda has finished executing
* If "Debugging" enabled
	* Log all output data state
* Run transition/conditional transition code if exists. Set Lambda to be invoked next based off of the result.
* Log the next Lambda which will be invoked
* Serialize return data as JSON
	* If >5MB, delete JSON, re-serialize as MessagePack and store in either Redis/S3 to be passed to next Lambda. Set return data to be a JSON structure indicating indirect storage in a third party datastore.
* If a next Lambda is set, invoke it with return data.