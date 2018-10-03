_VERSION = "1.0.0"

"""
Base redis connection for pulling configs/etc.

Allows for single-millisecond retrieval and setting
of data in the main redis memory cache.
"""
import os
import json
import time
import redis
import pickle

# TODO only initialize connection when used.
class Refinery_Memory:
	json_types = [
		list,
		dict
	]
	
	regular_types = [
		str,
		int,
		float,
		complex,
		bool,
	]
	
	def __init__( self, in_hostname, in_password, namespace ):
		self.redis_client = False
		self.namespace = namespace
		self.hostname = in_hostname
		self.password = in_password
		
	def connect( self ):
		self.redis_client = redis.StrictRedis(
		    host=self.hostname,
		    port=6379,
		    db=0,
		    socket_timeout=2,
		    password=self.password,
		)
		
	def _get_namespace( self, kwargs ):
		if self.namespace == False:
			return ""

		if "raw" in kwargs and kwargs[ "raw" ]:
			return ""
			
		return self.namespace + "."
	
	def set( self, key, input_data, **kwargs ):
		if not self.redis_client:
			self.connect()
		
		namespace = self._get_namespace( kwargs )
			
		if type( input_data ) in self.regular_types:
			self.redis_client.set(
				namespace + key,
				input_data
			)
		elif type( input_data ) in self.json_types:
			self.redis_client.set(
				namespace + key,
				json.dumps(
					input_data
				)
			)
		else:
			self.redis_client.set(
				namespace + key,
				pickle.dumps(
					input_data
				)
			)
			
	def get( self, key, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		data = self.redis_client.get(
			namespace + key
		)
		
		try:
			return json.loads(
				data
			)
		except:
			pass
		
		try:
			return pickle.loads(
				data
			)
		except:
			pass
		
		return data
			
	def exists( self, key, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		return self.redis_client.exists(
			namespace + key
		)
		
	def delete( self, key, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		return self.redis_client.dek(
			namespace + key
		)
		
	def rename( self, key, new_key, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		return self.redis_client.rename(
			namespace + key,
			new_key
		)
		
	def expire_at( self, key, unix_timestamp, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		return self.redis_client.expireat(
			namespace + key,
			unix_timestamp
		)
		
	def expire_in( self, key, seconds, **kwargs ):
		if not self.redis_client:
			self.connect()
			
		namespace = self._get_namespace( kwargs )
		
		return self.redis_client.expire(
			namespace + key,
			seconds
		)

def _init( lambda_input, context ):
	global cmemory
	global gmemory
	
	cmemory = Refinery_Memory(
		"config-memory.refinery.thehackerblog.com",
		"{{REDIS_PASSWORD_REPLACE_ME}}",
		False
	)
	
	gmemory = Refinery_Memory(
		"global-memory.refinery.thehackerblog.com",
		"{{REDIS_PASSWORD_REPLACE_ME}}",
		context.function_name
	)
	
	return main( lambda_input, context )