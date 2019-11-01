import tornado

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

class BaseSpawner(object):
	def __init__(self, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()