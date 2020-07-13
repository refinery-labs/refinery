from aiohttp.web import Response, Server, ServerRunner, TCPSite
from asyncio import get_event_loop, sleep
from json import loads, dumps
from pidgeon.framework.constants import ENCODING
from pidgeon.framework.controller import get_path_controller_map
from pidgeon.framework.exc import ApplicationError
from pidgeon.framework.log import log
from sys import maxsize
from traceback import print_exc
from uuid import uuid4

from pidgeon.framework.controller import Controller


DEFAULT_CONTENT_TYPE = "application/json"


class RequestHandler:
    def __init__(self, path_controller_map):
        self.path_controller_map = path_controller_map

    async def on_request(self, request):
        log.info(f"{request.method} {request.path}")

        arguments = loads((await request.read()).decode(ENCODING) or "{}")
        response = {"success": False}
        path = request.path
        status = 200

        try:
            # TODO this may not work behind something like an nginx proxy
            method = self.path_controller_map.get(path)

            if method is None:
                raise ApplicationError("Not found.")

            response['data'] = await method(**arguments)
            response['success'] = True
        except ApplicationError as e:
            log.warn(e)

            status = 400
            response['error'] = e.args[0]
            response['error_code'] = e.code
        except Exception as e:
            error_id = str(uuid4())
            response['error'] = f"Internal server error: {error_id}"
            response['error_code'] = 0

            log.error("{} {}".format(error_id, str(e)))
            print_exc()
        finally:
            return Response(
                text=dumps(response),
                status=status,
                content_type=DEFAULT_CONTENT_TYPE
            )


async def start_http_server(host, port, controllers, object_graph):
    path_controller_map = get_path_controller_map(controllers, object_graph)
    handler = RequestHandler(path_controller_map)
    server = Server(handler.on_request)
    runner = ServerRunner(server)

    await runner.setup()

    site = TCPSite(runner, host, port)

    await site.start()

    log.info(f"HTTP server listening on: {host}:{port}")

    await sleep(maxsize)
