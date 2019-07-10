# Creating a Highly Scalable API Endpoint

This tutorial will guide you through creating a scalable web API Endpoint in Refinery. It will cover topics like getting HTTP parameters, headers, and other data about a web request to your newly-created endpoint.

**Note**: If you're just looking for a full example object of what request data is passed via block input, [click here](#example-api-request-block-input-data).

<video style="width: 100%" controls autoplay muted loop>
	<source src="/tutorials/api-endpoints/media/adding-api-endpoint-blocks.webm" type="video/webm" />
	<source src="/tutorials/api-endpoints/media/adding-api-endpoint-blocks.mp4" type="video/mp4" />
</video>

In Refinery, you can create an API Endpoint by connecting a `API Endpoint` block to a `Code Block` and then connecting the `Code Block` to an `API Response` block.

Once you've done this, you can then get all of the request information from the block input parameter in your connected `Code Block`.

## An Important Notes About API Endpoint & API Response Blocks

It's important to note that the API Endpoint and API Response blocks are <u>not tied together</u>. You can start a request from any API Endpoint block and end up at any API Response block via your transitions.

For example, it's perfectly fine to have one API Response block and to have three API Endpoints which all eventually transition into it. You may want to add more API Response blocks to make things more aesthetically pleasing, however.

Additionally, if you transition into multiple API Response blocks - that's completely fine. The first API Response block you transition into will cause the API Response to be sent, all future transitions in the course of that pipeline execution will just be ignored.

## Retrieving URL Parameters (e.g. `/?parameter=value`)

In your `Code Block` you can retrieve URL parameters by using the `queryStringParameters` key of the `block_input` object.

The following code snippets demonstrate grabbing the URL parameter `number` and returning a response that multiplies the specified number by `2`:

``` python tab="Python 2.7"
def main(block_input, backpack):
    # Validate that the user passed us the URL parameter "number"
    # If not return an error.
    if not block_input[ "queryStringParameters" ] or not "number" in block_input[ "queryStringParameters" ]:
        return {
            "msg": "You must provide a 'number' parameter for this endpoint!",
            "success": False
        }
    
    # Return the number multiplied by two
    return {
        "success": True,
        "result": int( block_input[ "queryStringParameters" ][ "number" ] ) * 2
    }
```

``` javascript tab="Node 8.10"
async function main(blockInput, backpack) {
    // Ensure the user has set the 'number' parameter
    if(!blockInput.queryStringParameters || blockInput.queryStringParameters.number === undefined) {
        return {
            "success": false,
            "msg": "You must provide a 'number' parameter for this endpoint!"
        }
    }
    
    // Return the number multiplied by two
	return {
	    "success": true,
	    "result": (parseInt(blockInput.queryStringParameters.number) * 2)
	}
}

```

``` php tab="PHP 7.3"
<?php
function main($block_input, $backpack) {
    // Check if user set the 'number' parameter
    // Return an error if they did not
    if(!array_key_exists("number", $block_input["queryStringParameters"])) {
        return array(
            "success" => false,
            "msg" => "You must provide a 'number' parameter for this endpoint!"
        );
    }
    
    // Return the 'number' paramter multiplied by two
	return array(
	    "success" => true,
	    "result" => (intval($block_input["queryStringParameters"]["number"] * 2))
    );
}
```

``` Go tab="Go 1.12"
// Go example is TODO, if you'd like a Go example added please email us at support@refinery.io
// Sorry about that!
```

If there are no URL parameters specified the `queryStringParameters` field of the block input will be `null`.

## Getting Parameters from a JSON POST API Request

For JSON data in a POST request to your API endpoint you can find the request body in the `body` key of the block input object.

The following code snippets demonstrate how to get the `number` parameter out of an example JSON POST API request:

``` python tab="Python 2.7"
import json

def main(block_input, backpack):
    # Placeholder for parsed JSON body data
    body_data = {}
    
    # Validate the body exists, parse as JSON if it does.
    if "body" in block_input and block_input["body"]:
    	try:
        	body_data = json.loads(block_input["body"])
        except ValueError:
        	pass
        
    # Validate that the user passed us the JSON parameter "number"
    # If not return an error.
    if not "number" in body_data:
        return {
            "msg": "You must provide a 'number' parameter for this endpoint!",
            "success": False
        }
    
    # Return the number multiplied by two
    return {
        "success": True,
        "result": (body_data[ "number" ] * 2)
    }
```

``` javascript tab="Node 8.10"
async function main(blockInput, backpack) {
	// Placeholder for parsed JSON body data
    var bodyData = {};
    
    // If the body is set and is JSON, parse it and set bodyData
    if( blockInput.body ) {
        try {
            bodyData = JSON.parse(
                blockInput.body
            );
        } catch( e ) {}
    }
    
    // If the 'number' parameter does not exist, return an error
    if(!("number" in bodyData)) {
        return {
            "success": false,
            "msg": "You must provide a 'number' parameter for this endpoint!"
        }
    }
    
    // Return the number multiplied by two
	return {
	    "success": true,
	    "result": (parseInt(bodyData.number) * 2)
	}
}
```

``` php tab="PHP 7.3"
<?php
function main($block_input, $backpack) {
    $body_data = array();
    
    // Parse the JSON body if it's set
    if(array_key_exists("body", $block_input)) {
        try {
            $body_data = json_decode(
                $block_input["body"],
                true
            );
        } catch (Exception $e) {}
    }
    
    // Ensure the user has set the "number" parameter
    if(!array_key_exists("number", $body_data)) {
        return array(
            "success" => false,
            "msg" => "You must provide a 'number' parameter for this endpoint!"
        );
    }
    
    // Return the 'number' paramter multiplied by two
	return array(
	    "success" => true,
	    "result" => (intval($body_data["number"] * 2))
    );
}

```

``` Go tab="Go 1.12"
// Go example is TODO, if you'd like a Go example added please email us at support@refinery.io
// Sorry about that!
```

## Returning a Custom Response

By default Refinery JSON-encodes the data returned from the `Code Block` which transitioned into the `API Response` block. The following headers are set in this case:

* `Content-Type: application/json`
* `X-Frame-Options: deny`
* `X-Content-Type-Options: nosniff`
* `X-XSS-Protection: 1; mode=block`
* `Cache-Control: no-cache, no-store, must-revalidate`
* `Pragma: no-cache`
* `Expires: 0`
* `Server: refinery`

Of course, these defaults may not make sense for your specific usage. You can customize the returned headers by returning an object in the following format:

``` javascript tab="Annotated JSON"
{
	// The HTTP status code you want to return
	"statusCode": 200,
	// Custom headers you want to set on the response
	"headers": {
		"X-Custom-Header": "Custom-Header-Value"
	},
	// The response body
	"body": "Your response body here!",
	// OPTIONAL: Allows you to return binary data in a
	// base64-encoded format. Your response data will automatically
	// be decoded and the raw binary will be sent as the response body.
	"isBase64Encoded": false
}
```

``` javascript tab="Uncommented Raw JSON"
{
	"statusCode": 200,
	"headers": {
		"X-Custom-Header": "Custom-Header-Value"
	},
	"body": "Your response body here!",
	"isBase64Encoded": false
}
```

### Returning HTML

For example, if you want to return some HTML the following object structure can be used:

``` javascript tab="Annotated JSON"
{
	// Successful status code
	"statusCode": 200,
	// Setting the Content-Type to be HTML
	"headers": {
		"Content-Type": "text/html; charset=utf-8"
	},
	// The HTML you're returning
	"body": "<h1>Neat!</h1>"
}
```

``` javascript tab="Uncommented Raw JSON"
{
	"statusCode": 200,
	"headers": {
		"Content-Type": "text/html; charset=utf-8"
	},
	"body": "<h1>Neat!</h1>"
}
```

### Redirecting to Another URL

The following object structure can be used for redirecting a user to another URL:

``` javascript tab="Annotated JSON"
{
	// 302 status code indicated a temporary redirect
	"statusCode": 302,
	"headers": {
		// The Location header tells the browser where to go
		"Location": "https://www.example.com/"
	},
	// No response body is needed since we're redirecting the user
	"body": ""
}
```

``` javascript tab="Uncommented Raw JSON"
{
	"statusCode": 302,
	"headers": {
		"Location": "https://www.example.com/"
	},
	"body": ""
}
```

## Example API Request Block Input Data

If you need an easy-to-copy example of the full object structure of the request data you get for an API Endpoint, the following is an example. This example specifically uses every field and is a POST request with a body and URL parameters:

``` javascript tab="Annotated JSON"
{
  // The request body data if there was an HTTP body to the request.
  "body": "{ \"example\": \"json\" }",
  // The URL path for the API Endpoint (not including /refinery)
  "resource": "/postexample",
  // Metadata about the request
  "requestContext": {
  	// What stage was used (this is always "refinery")
    "stage": "refinery",
    // The full date and time of when the request occurred
    "requestTime": "08/Jul/2019:06:19:05 +0000",
    // HTTP protocol version
    "protocol": "HTTP/1.1",
    // The hostname the resource came in as
    "domainName": "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com",
    // The resource ID in API Gateway (AWS service Refinery builds to)
    "resourceId": "fmoota",
    // The API ID in API Gateway (AWS Service Refinery builds to)
    "apiId": "xxxxxxxxxx",
    // Name of the operation (always HTTP Method)
    "operationName": "HTTP Method",
    // The URL path for the API Endpoint (not including /refinery)
    "resourcePath": "/postexample",
    // The HTTP method the request came in as (useful for when * is specified for HTTP method)
    "httpMethod": "POST",
    // The prefix to the .execute-api.us-west-2.amazonaws.com
    "domainPrefix": "xxxxxxxxxx",
    // A unique UUID for the request
    "requestId": "49ce8805-a148-11e9-b1ab-fbd3bff4d120",
    // Request ID only usable by AWS support
    "extendedRequestId": "cff-DHY1vHcFQyQ=",
    // The full HTTP path
    "path": "/refinery/postexample",
    // The timestamp in nanoseconds the request occurred
    "requestTimeEpoch": 1562566745950,
    // Metadata about the user making the HTTP request
    "identity": {
      "userArn": null,
      "principalOrgId": null,
      "accessKey": null,
      "caller": null,
      // Browser userr agent.
      "userAgent": "curl/7.52.1",
      "user": null,
      "cognitoIdentityPoolId": null,
      "cognitoIdentityId": null,
      "accountId": null,
      "cognitoAuthenticationType": null,
      // The source IP of the user making the HTTP request
      "sourceIp": "127.0.0.2",
      "cognitoAuthenticationProvider": null
    },
    // Your Refinery managed AWS account ID
    "accountId": "111222333444"
  },
  // A key/value map of the URL parameters passed in the request
  // The below data comes from a URL like the following:
  // http://example.com/?url_param=example
  "queryStringParameters": {
    "url_param": "example"
  },
  // A key/value map of headers where the value is an array of all
  // values for that header name. This is useful for when you have
  // multiple headers set on a request with the same name and want
  // the values from all of them.
  // Some of these headers are added by AWS as metadata via one of the
  // intermediary reverse HTTP proxy servers.
  "multiValueHeaders": {
    "Via": [
      "2.0 3e1333ad4666f388875288877e890589.cloudfront.net (CloudFront)"
    ],
    "CloudFront-Is-Desktop-Viewer": [
      "true"
    ],
    "CloudFront-Is-SmartTV-Viewer": [
      "false"
    ],
    "CloudFront-Forwarded-Proto": [
      "https"
    ],
    "X-Forwarded-For": [
      "127.0.0.2, 70.132.61.152"
    ],
    "CloudFront-Viewer-Country": [
      "US"
    ],
    "Accept": [
      "*/*"
    ],
    "User-Agent": [
      "curl/7.52.1"
    ],
    "X-Amzn-Trace-Id": [
      "Root=1-12345678-7e004456cc33332a6cd44486"
    ],
    "Host": [
      "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com"
    ],
    "X-Forwarded-Proto": [
      "https"
    ],
    "X-Amz-Cf-Id": [
      "H9oPbEB3enWeeOF2g11qaYUBKhp2UE4oDvlEukAVJuVmVEA7myP6gA=="
    ],
    "CloudFront-Is-Tablet-Viewer": [
      "false"
    ],
    "X-Forwarded-Port": [
      "443"
    ],
    "CloudFront-Is-Mobile-Viewer": [
      "false"
    ],
    "content-type": [
      "application/json"
    ]
  },
  // A key/value map of URL parameters where the value is an array of all
  // values for that URL parameter name. This is useful for when you have
  // multiple parameters set on a request with the same name and want the
  // values from all of them.
  "multiValueQueryStringParameters": {
    "url_param": [
      "example"
    ]
  },
  // For RESTful API parameters (not yet implemented in Refinery)
  "pathParameters": null,
  // The HTTP method the request used.
  "httpMethod": "POST",
  // A key/value map of the headers set on the request.
  // Some of these headers are added by AWS as metadata via one of the
  // intermediary reverse HTTP proxy servers.
  "headers": {
    "Via": "2.0 3e1333ad4666f388875288877e890589.cloudfront.net (CloudFront)",
    "CloudFront-Is-Desktop-Viewer": "true",
    "CloudFront-Is-SmartTV-Viewer": "false",
    "CloudFront-Forwarded-Proto": "https",
    "X-Forwarded-For": "136.25.14.44, 70.132.61.152",
    "CloudFront-Viewer-Country": "US",
    "Accept": "*/*",
    "User-Agent": "curl/7.52.1",
    "X-Amzn-Trace-Id": "Root=1-12345678-7e004456cc33332a6cd44486",
    "Host": "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com",
    "X-Forwarded-Proto": "https",
    "X-Amz-Cf-Id": "H9oPbEB3enWeeOF2g11qaYUBKhp2UE4oDvlEukAVJuVmVEA7myP6gA==",
    "CloudFront-Is-Tablet-Viewer": "false",
    "X-Forwarded-Port": "443",
    "CloudFront-Is-Mobile-Viewer": "false",
    "content-type": "application/json"
  },
  "stageVariables": null,
  // The URL path for the API Endpoint (not including /refinery)
  "path": "/postexample",
  // If the body is base64 encoded
  // More information here: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
  "isBase64Encoded": false
}
```

``` javascript tab="Uncommented Raw JSON"
{
  "body": "{ \"example\": \"json\" }",
  "resource": "/postexample",
  "requestContext": {
    "stage": "refinery",
    "requestTime": "08/Jul/2019:06:19:05 +0000",
    "protocol": "HTTP/1.1",
    "domainName": "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com",
    "resourceId": "fmoota",
    "apiId": "xxxxxxxxxx",
    "operationName": "HTTP Method",
    "resourcePath": "/postexample",
    "httpMethod": "POST",
    "domainPrefix": "xxxxxxxxxx",
    "requestId": "49ce8805-a148-11e9-b1ab-fbd3bff4d120",
    "extendedRequestId": "cff-DHY1vHcFQyQ=",
    "path": "/refinery/postexample",
    "requestTimeEpoch": 1562566745950,
    "identity": {
      "userArn": null,
      "principalOrgId": null,
      "accessKey": null,
      "caller": null,
      "userAgent": "curl/7.52.1",
      "user": null,
      "cognitoIdentityPoolId": null,
      "cognitoIdentityId": null,
      "accountId": null,
      "cognitoAuthenticationType": null,
      "sourceIp": "127.0.0.2",
      "cognitoAuthenticationProvider": null
    },
    "accountId": "111222333444"
  },
  "queryStringParameters": {
    "url_param": "example"
  },
  "multiValueHeaders": {
    "Via": [
      "2.0 3e1333ad4666f388875288877e890589.cloudfront.net (CloudFront)"
    ],
    "CloudFront-Is-Desktop-Viewer": [
      "true"
    ],
    "CloudFront-Is-SmartTV-Viewer": [
      "false"
    ],
    "CloudFront-Forwarded-Proto": [
      "https"
    ],
    "X-Forwarded-For": [
      "127.0.0.2, 70.132.61.152"
    ],
    "CloudFront-Viewer-Country": [
      "US"
    ],
    "Accept": [
      "*/*"
    ],
    "User-Agent": [
      "curl/7.52.1"
    ],
    "X-Amzn-Trace-Id": [
      "Root=1-12345678-7e004456cc33332a6cd44486"
    ],
    "Host": [
      "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com"
    ],
    "X-Forwarded-Proto": [
      "https"
    ],
    "X-Amz-Cf-Id": [
      "H9oPbEB3enWeeOF2g11qaYUBKhp2UE4oDvlEukAVJuVmVEA7myP6gA=="
    ],
    "CloudFront-Is-Tablet-Viewer": [
      "false"
    ],
    "X-Forwarded-Port": [
      "443"
    ],
    "CloudFront-Is-Mobile-Viewer": [
      "false"
    ],
    "content-type": [
      "application/json"
    ]
  },
  "multiValueQueryStringParameters": {
    "url_param": [
      "example"
    ]
  },
  "pathParameters": null,
  "httpMethod": "POST",
  "headers": {
    "Via": "2.0 3e1333ad4666f388875288877e890589.cloudfront.net (CloudFront)",
    "CloudFront-Is-Desktop-Viewer": "true",
    "CloudFront-Is-SmartTV-Viewer": "false",
    "CloudFront-Forwarded-Proto": "https",
    "X-Forwarded-For": "136.25.14.44, 70.132.61.152",
    "CloudFront-Viewer-Country": "US",
    "Accept": "*/*",
    "User-Agent": "curl/7.52.1",
    "X-Amzn-Trace-Id": "Root=1-12345678-7e004456cc33332a6cd44486",
    "Host": "xxxxxxxxxx.execute-api.us-west-2.amazonaws.com",
    "X-Forwarded-Proto": "https",
    "X-Amz-Cf-Id": "H9oPbEB3enWeeOF2g11qaYUBKhp2UE4oDvlEukAVJuVmVEA7myP6gA==",
    "CloudFront-Is-Tablet-Viewer": "false",
    "X-Forwarded-Port": "443",
    "CloudFront-Is-Mobile-Viewer": "false",
    "content-type": "application/json"
  },
  "stageVariables": null,
  "path": "/postexample",
  "isBase64Encoded": false
}
```
