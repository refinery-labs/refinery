import os
import time
import json
import tornado
import requests
import subprocess

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen


class NgrokSpawner(object):
	app_config = None

	def __init__(self, app_config, loop=None):
		self.executor = futures.ThreadPoolExecutor( 10 )
		self.loop = loop or tornado.ioloop.IOLoop.current()

		self.app_config = app_config
		
	@run_on_executor
	def start_ngrok_tunnel( self, port ):
		if not self.app_config.get( "ngrok_api_secret" ):
			logit( "No ngrok API secret specified! Please enable one so Lambda callbacks work in dev!" )
			return
		
		process_handler = subprocess.Popen(
			[
				"/work/ngrok",
				"http",
				str( port ),
				"--authtoken",
				self.app_config.get( "ngrok_api_secret" )
			],
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			stdin=subprocess.PIPE,
			shell=False,
			universal_newlines=True,
		)
		stdout, tmp = process_handler.communicate()
		
	@run_on_executor
	def get_ngrok_tunnel_hostname( self ):
		ngrok_url = False
		
		while not ngrok_url:
			logit( "Querying the ngrok API server for exposed endpoint URL..." )
			
			try:
				response = requests.get(
					"http://localhost:4040/api/tunnels"
				)
				response_dict = json.loads(
					response.text
				)
				ngrok_url = response_dict[ "tunnels" ][0][ "public_url" ]
				logit( "ngrok tunnel established successfully, endpoint is " + ngrok_url )
			except Exception as e:
				logit( "API server is not yet up, trying again shortly..." )
				time.sleep(1)

		return ngrok_url

@gen.coroutine
def set_up_ngrok_websocket_tunnel(ngrok_tasks):
	logit( "Creating exposed ngrok tunnel to WebSocket server..." )
	
	# Don't yield, we want to run ngrok in the background
	ngrok_tasks.start_ngrok_tunnel( 3333 )
	
	# Query ngrok API server to get exposed URL
	ngrok_url = yield ngrok_tasks.get_ngrok_tunnel_hostname()
	
	# Now keep trying to query the HTTP API to get the hostname
	raise gen.Return( ngrok_url )