import json
import re
from urllib.parse import urlparse

from tornado import httpclient, gen
from tornado.httpclient import HTTPClientError
from tornado.httpserver import HTTPRequest

from controller import BaseHandler
from controller.decorators import authenticated
from controller.github.decorators import github_authenticated


GIT_ALLOW_HEADERS = [
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
GIT_EXPOSE_HEADERS = [
    'accept-ranges',
    'age',
    'cache-control',
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

DEFAULT_ALLOW_METHODS = [
    'POST',
    'GET',
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


def cors( req, res_headers ):
    origin = '*'
    max_age = 60 * 60 * 24
    allow_methods = DEFAULT_ALLOW_METHODS
    allow_headers = DEFAULT_ALLOW_HEADERS
    allow_credentials = True
    expose_headers = []

    res_headers['Access-Control-Allow-Origin'] = origin
    if allow_credentials:
        res_headers['Access-Control-Allow-Credentials'] = 'true'

    if len( expose_headers ):
        res_headers['Access-Control-Expose-Headers'] = ','.join( expose_headers )

    if req.method == 'OPTIONS':
        res_headers['Access-Control-Allow-Methods'] = ','.join( allow_methods )
        res_headers['Access-Control-Allow-Headers'] = ','.join( allow_headers )
        res_headers['Access-Control-Max-Age'] = str( max_age )


CORS_MAX_AGE = 60 * 60 * 24


class GithubProxy( BaseHandler ):
    http = None  # type: httpclient.AsyncHTTPClient

    def initialize( self, **kwargs ):
        self.http = httpclient.AsyncHTTPClient()

    def set_default_cors( self ):
        self.set_header( 'Access-Control-Allow-Credentials', 'true' )

    @github_authenticated
    async def proxy_request( self, oauth_token, oauth_json_data ):
        headers = {}
        for header in GIT_ALLOW_HEADERS:
            if self.request.headers.get( header ):
                headers[header] = self.request.headers[header]

        print(oauth_json_data)

        username = oauth_json_data['login']
        password = oauth_token

        u = urlparse(self.request.full_url())

        p = u.path
        parts = re.match('^/api/v1/github/proxy/([^/]*)/(.*)$', p)
        remainingpath = parts.group( 2 )

        # TODO support other git servers, we do this to prevent ssrf
        proxy_url = "https://{username}:{password}@github.com/{remainingpath}{params}".format(
            username=username,
            password=password,
            remainingpath=remainingpath,
            params='?' + self.request.query if self.request.query else '',
        )

        try:
            proxy_res: httpclient.HTTPResponse = await self.http.fetch(
                proxy_url,
                method=self.request.method,
                headers=headers,
                body=self.request.body if self.request.method != 'GET' else None
            )

            code = proxy_res.code
            reason = proxy_res.reason

            for header in GIT_EXPOSE_HEADERS:
                if header.lower() in proxy_res.headers:
                    self.set_header( header, proxy_res.headers[header] )

            if proxy_res.code & 300 == 300:
                self.set_header( 'x-redirected-url', proxy_res.effective_url )

            self.set_status( code, reason )
            self.write( proxy_res.body )

        except HTTPClientError as e:
            raise e

    def is_info_refs( self ):
        assert isinstance( self.request, HTTPRequest )

        valid_path = self.request.path.endswith( '/info/refs' )

        request_service = self.request.arguments.get( 'service' )
        if not request_service or len( request_service ) != 1:
            return False

        first_request_service = request_service[0].decode()

        valid_service = (
                first_request_service.endswith( 'git-upload-pack' )
                or first_request_service.endswith( 'git-receive-pack' )
        )

        return valid_path and valid_service

    def is_pull_or_push( self ):
        assert isinstance( self.request, HTTPRequest )

        content_type = self.request.headers.get( 'content-type' )
        if content_type is None:
            return False

        is_push = content_type == 'application/x-git-upload-pack-request' and self.request.path.endswith(
            'git-upload-pack' )
        is_pull = content_type == 'application/x-git-receive-pack-request' and self.request.path.endswith(
            'git-receive-pack' )

        return is_push or is_pull

    @authenticated
    async def get( self, url ):
        self.set_default_cors()
        if self.is_info_refs():
            await self.proxy_request()
        await self.finish()

    @authenticated
    async def post( self, url ):
        self.set_default_cors()
        if self.is_pull_or_push():
            await self.proxy_request()
        await self.finish()

    async def options( self, url ):
        self.set_default_cors()
        self.set_header( 'Access-Control-Allow-Methods', ','.join( DEFAULT_ALLOW_METHODS ) )
        self.set_header( 'Access-Control-Allow-Headers', ','.join( DEFAULT_ALLOW_HEADERS ) )
        self.set_header( 'Access-Control-Max-Age', CORS_MAX_AGE )
        await self.finish()
