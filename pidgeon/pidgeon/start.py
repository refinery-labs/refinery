from asyncio import get_event_loop
from pidgeon.framework.constants import ENV
from pidgeon.framework.util.config import Config
from pidgeon.framework.server import start_http_server
from pidgeon.framework.log import log
from pidgeon.graph import get_object_graph, controllers


def start():
    # TODO figure out how to get this from the object graph instead
    config = Config(ENV)
    host = config.get("http_host")
    port = config.get("http_port")
    loop = get_event_loop()
    object_graph = get_object_graph()
    task = start_http_server(host, port, controllers, object_graph)

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, exiting.")

    loop.close()
