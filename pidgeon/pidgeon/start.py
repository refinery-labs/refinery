from asyncio import get_event_loop
from pidgeon.framework.constants import PROJECT_ROOT
from pidgeon.framework.controller import Controller
from pidgeon.framework.server import start_http_server
from pidgeon.framework.log import log
from pidgeon.framework.util import get_impls
from pidgeon.graph import get_object_graph


def start():
    # TODO read config
    host = "0.0.0.0"
    port = 8080
    loop = get_event_loop()
    controllers = get_impls(Controller, "pidgeon.controller", PROJECT_ROOT)
    object_graph = get_object_graph()
    task = start_http_server(host, port, controllers, object_graph)

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, exiting.")

    loop.close()
