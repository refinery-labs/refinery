# Creating an API Endpoint With Refinery

This tutorial will guide you through creating a scalable web API Endpoint in Refinery. It will cover topics like getting HTTP parameters, headers, and other data about a web request to your newly-created endpoint.

<video style="width: 100%" controls autoplay muted loop>
	<source src="/tutorials/api-endpoints/media/adding-api-endpoint-blocks.webm" type="video/webm" />
	<source src="/tutorials/api-endpoints/media/adding-api-endpoint-blocks.mp4" type="video/mp4" />
</video>

In Refinery, you can create an API Endpoint by connecting a `API Endpoint` block to a `Code Block` and then connecting the `Code Block` to an `API Response` block.

Once you've done this, you can then get all of the request information from the `block_input` parameter in your connected `Code Block`.

## Retrieving URL Parameters (e.g. `/?parameter=value`)

In your `Code Block` you can retrieve URL parameters by using the `queryStringParameters` key of the `block_input` object.

The following code snippets demonstrate grabbing the URL parameter `number` and returning a response that multiplies the specified number by `2`:

``` python tab="Python 2.7"

def main(block_input, backpack):
    # Validate that the user passed us the URL parameter "number"
    # If not return an error.
    if not "number" in block_input[ "queryStringParameters" ]:
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