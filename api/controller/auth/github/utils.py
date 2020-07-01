import codecs
import json
import os
import re
from binascii import hexlify
from urllib.parse import urljoin

from utils.general import logit


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


def generate_redirect_uri(ctx, web_origin):
    """
	Returns a URI that is the "redirect" destination FROM Github after the user authenticates.
    This URI should point to OUR server.
    :param ctx: Tornado request context.
    :param web_origin: Origin of the web server.
    :return: URI that the client should return to on our server.
    """
    return urljoin(web_origin, ctx.reverse_url("auth_github"))


def generate_state_token():
    """
    Returns a random "state" token to be used for an OAuth flow.
    :return: The random string
    """
    return hexlify(os.urandom(16))
