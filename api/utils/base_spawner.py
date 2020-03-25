import tornado

from tornado.concurrent import run_on_executor, futures

class BaseSpawner(object):
	def __init__(self, loop=None, app_config=None):
		"""

		:param loop:
		:type app_config: AppConfig
		"""
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()
		self.app_config = app_config
