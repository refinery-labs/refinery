import re
import urllib
from urlparse import urlparse

from tornado import httpclient, httputil, gen
from tornado.httpclient import HTTPClientError
from tornado.httputil import HTTPMessageDelegate, ResponseStartLine, HTTPHeaders
from tornado.routing import Router

from models.initiate_database import DBSession

allowHeaders = [
  'accept-encoding',
  'accept-language',
  'accept',
  'access-control-allow-origin',
  'authorization',
  'cache-control',
  'connection',
  'content-length',
  'content-type',
  'dnt',
  'pragma',
  'range',
  'referer',
  'user-agent',
  'x-authorization',
  'x-http-method-override',
  'x-requested-with',
]
exposeHeaders = [
  'accept-ranges',
  'age',
  'cache-control',
  'content-length',
  'content-language',
  'content-type',
  'date',
  'etag',
  'expires',
  'last-modified',
  'pragma',
  'server',
  'vary',
  'x-github-request-id',
  'x-redirected-url',
]
allowMethods = [
  'POST',
  'GET',
  'OPTIONS'
]

insecure_origins = []


def filter( predicate, middleware ):
  def cors_proxy_middlware( req, res, next ):
    if predicate( req, res ):
      middleware( req, res )
    else:
      next()

  return cors_proxy_middlware


def noop( req, res, next ):
  next()


def predicate( req ):
  u = urlparse( req.url )
  # return allow(req, u)
  return


def send_cors_ok( req, res, next ):
  if req.method == 'OPTIONS':
    # return send(res, 200, '')
    return
  else:
    next()


class CustomRouter( Router ):
  def __init__(self, ):
      super(CustomRouter, self).__init__()

  def find_handler( self, request, **kwargs ):
    return MessageDelegate( request, DBSession() )


class MessageDelegate( HTTPMessageDelegate ):
  request = None  # type: httputil.HTTPServerRequest
  dbsession = None
  body = None

  def __init__( self, request, dbsession ):
    self.request = request
    self.dbsession = dbsession
    self.body = ''

  def data_received(self, chunk):
      self.body += chunk

  @gen.coroutine
  def finish( self ):
    yield proxy_middleware( self.request, self.body, self.dbsession )
    self.request.connection.finish()
    self.dbsession.close()


DEFAULT_ALLOW_METHODS = [
  'POST',
  'GET',
  'PUT',
  'PATCH',
  'DELETE',
  'OPTIONS'
]


DEFAULT_ALLOW_HEADERS = [
  'X-Requested-With',
  'Access-Control-Allow-Origin',
  'X-HTTP-Method-Override',
  'Content-Type',
  'Authorization',
  'Accept'
]


def cors(req, res_headers):
    origin = '*'
    max_age = 60 * 60 * 24
    allow_methods = DEFAULT_ALLOW_METHODS
    allow_headers = DEFAULT_ALLOW_HEADERS
    allow_credentials = True
    expose_headers = []

    #if res and res.finished:
    #    return

    res_headers['Access-Control-Allow-Origin'] = origin
    if allow_credentials:
        res_headers['Access-Control-Allow-Credentials'] = 'true'

    if len(expose_headers):
        res_headers['Access-Control-Expose-Headers'] = ','.join(expose_headers)

    if req.method == 'OPTIONS':
        res_headers['Access-Control-Allow-Methods'] = ','.join(allow_methods)
        res_headers['Access-Control-Allow-Headers'] = ','.join(allow_headers)
        res_headers['Access-Control-Max-Age'] = str(max_age)


@gen.coroutine
def proxy_middleware( req, body, dbsession ):
    res_headers = dict()

    # TODO get auth from header -> user_id

    cors(req, res_headers)

    if req.method == 'OPTIONS':
        req.connection.write_headers(
            ResponseStartLine( "HTTP/1.1", 200, "OK" ),
            HTTPHeaders( res_headers ), b'' )
        raise gen.Return()

    headers = req.headers
    for h in allowHeaders:
        if req.headers.get( h ):
            headers[h] = req.headers[h]

    u = urlparse( req.full_url() )

    p = u.path
    parts = re.match( '/([^/]*)/(.*)', p )
    pathdomain = parts.group(1)
    remainingpath = parts.group(2)
    protocol = 'http' if pathdomain in insecure_origins else 'https'

    headers['host'] = pathdomain

    http = httpclient.AsyncHTTPClient()

    proxy_url = "{protocol}://{pathdomain}/{remainingpath}{params}".format(
        protocol=protocol,
        pathdomain=pathdomain,
        remainingpath=remainingpath,
        params='?' + req.query if req.query else '',
    )

    try:
        proxy_res = yield http.fetch(
            proxy_url,
            method=req.method,
            headers=headers,
            body=body if req.method != 'GET' and req.method != 'HEAD' else None
        )  # type: httpclient.HTTPResponse

        code = proxy_res.code
        reason = proxy_res.reason

        for header in exposeHeaders:
            if header == 'content-length':
                continue
            if header.lower() in proxy_res.headers:
                res_headers[header] = proxy_res.headers[header]

        if proxy_res.code & 300 == 300:
            res_headers['x-redirected-url'] = proxy_res.effective_url

    except HTTPClientError as e:
        code = e.code
        reason = e.message
        raise e

    req.connection.write_headers(
        ResponseStartLine( "HTTP/1.1", code, reason ),
        HTTPHeaders( res_headers ), proxy_res.body )
