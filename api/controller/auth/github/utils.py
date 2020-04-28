import codecs
import json
import os
import re


def decode_response_body(response):
    """ Decodes the JSON-format response body

    :param response: the response object
    :type response: tornado.httpclient.HTTPResponse

    :return: the decoded data
    """
    # Fix GitHub response.
    body = codecs.decode(response.body, 'ascii')
    body = re.sub('"', '\"', body)
    body = re.sub("'", '"', body)
    return json.loads(body)


def generate_redirect_uri(ctx):
    """
    Returns a URI that is the "redirect" distination FROM Github after the user authenticates.
    This URI should point to OUR server.
    :param ctx: Tornado request context.
    :return: URI that the client should return to on our server.
    """
    return "{0}://{1}{2}".format(
        ctx.request.protocol,
        ctx.request.host,
        ctx.reverse_url("auth_github")
    )


def generate_state_token():
    """
    Returns a random "state" token to be used for an OAuth flow.
    :return: The random string
    """
    return os.urandom(16).encode("hex")
