# Example Invoke Argument

The following is an example of the payload which is passed to Lambdas invoked in a Refinery pipeline:

```json
{
	"_refinery": {
		"indirect": {
			"type": "redis",
			"key": {{UUID_FOR_KEY}},
		},
		"parallel": true,
	}
}
```

Upon a Lambda that has been deployed by Refinery executing, the base code will automatically check for the existence of the `_refinery` key in the Lambda's input data. If it exists it will be acted upon accordingly, if it does not the main portion of the code will be executed with the `lambda_input` variable set to the value of the payload.

# `_refinery` Keys Explained

## `indirect`

`false` if the invoke data is self-contained. Else it will be some resource data such as the following `redis` example:

```json
{
	"indirect": {
		"type": "redis",
		"key": {{UUID_FOR_KEY}},
	}
}
```

Or in the case of S3:

```json
{
	"indirect": {
		"type": "s3",
		"key": {{UUID_FOR_KEY}},
	}
}
```

## `parallel`

The `parallel` key specifies if the 