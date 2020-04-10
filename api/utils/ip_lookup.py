import time
import traceback
import requests
import tornado
import socket

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen


class IPLookupSpawner( object ):
	def __init__( self, loop=None ):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

	@run_on_executor
	def get_ipify_ip( self ):
		logit( "Attempting to resolve remote IPv4 IP via api.ipify.org..." )
		response = requests.get(
			"https://api.ipify.org/?format=text",
			timeout=3
		)
		return response.text.strip()

	@run_on_executor
	def get_icanhazip_ip( self ):
		logit( "Attempting to resolve remote IPv4 IP via icanhazip.com..." )
		response = requests.get(
			"https://icanhazip.com/ipv4",
			timeout=3
		)
		return response.text.strip()

	@run_on_executor
	def get_aws_ip( self ):
		logit( "Attempting to resolve remote IPv4 IP via checkip.amazonaws.com..." )
		response = requests.get(
			"https://checkip.amazonaws.com/",
			timeout=3
		)
		return response.text.strip()


ip_lookup_tasks = IPLookupSpawner()

IP_RESOLUTION_FUNCTIONS = [
	ip_lookup_tasks.get_aws_ip,
	ip_lookup_tasks.get_icanhazip_ip,
	ip_lookup_tasks.get_ipify_ip
]


def is_valid_ipv4_ip( input_ip_string ):
	"""
	Uses the socket API to validate that an IP address is indeed in the
	valid IPv4 format and is not malformed.
	"""

	if not input_ip_string:
		return False

	try:
		socket.inet_aton(
			input_ip_string
		)
	except socket.error:
		return False

	return True


@gen.coroutine
def get_external_ipv4_address():
	"""
	This uses a variety of third-party services to resolve the current
	host's external IP address. This is important as the callback needs
	to be to the specific machine and not the LB (which will RR it to
	potentially another box altogether).
	"""

	for _ in xrange(10000):
		for ipv4_resolution_function in IP_RESOLUTION_FUNCTIONS:
			try:
				remote_ipv4_ip = yield ipv4_resolution_function()

				if is_valid_ipv4_ip( remote_ipv4_ip ):
					raise gen.Return( remote_ipv4_ip )

				time.sleep( 0.2 )
			except gen.Return as result:
				raise gen.Return( result.value )
			except:
				logit( "An exception occurred while attempted to get our IPv4 IP, we'll try another site..." )
				traceback.print_exc()

