class DeploymentManager(object):
    aws_client_factory = None
    aws_cloudwatch_client = None
    logger = None

    # noinspection PyUnresolvedReferences
    @pinject.copy_args_to_public_fields
    def __init__(self, aws_client_factory, aws_cloudwatch_client, logger, loop=None):
        self.executor = futures.ThreadPoolExecutor(10)
        self.loop = loop or tornado.ioloop.IOLoop.current()
