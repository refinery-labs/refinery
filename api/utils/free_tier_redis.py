import os
import redis
import tornado
import requests

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from utils.base_spawner import BaseSpawner

REDIS_CLIENT = redis.StrictRedis(
	os.environ.get( "free_tier_redis_server_hostname" ),
	6379,
	0
)

REDIS_USER_ACCOUNT_PERMISSIONS = "~* +evalsha +get +del +multi +exec +lpop +lrange +decr +hkeys +hvals +setex +expire +lpush +rpush +hset +hgetall +client +incrby +decrby +acl"

REDIS_SECRET_PREFIX = os.environ.get(
	"free_tier_redis_server_command_prefix"
)

def authenticate_to_redis(username, password):
	logit( "Authentication to free-tier redis server..." )
	auth_result = REDIS_CLIENT.execute_command(
		"AUTH " + username + " " + password
	)

	if not "OK" in auth_result:
		raise Exception("Failed to authenticate to free-tier redis server!")

authenticate_to_redis(
	os.environ.get( "free_tier_redis_server_username" ),
	os.environ.get( "free_tier_redis_server_password" ),
)

class FreeTierRedisManagerSpawner(BaseSpawner):
	@run_on_executor
	def delete_redis_user( self, username ):
		del_user_command = REDIS_SECRET_PREFIX + "ACL DELUSER " + username
		del_user_response = REDIS_CLIENT.execute_command(
			del_user_command
		)

	@run_on_executor
	def add_redis_user( self, username, password ):
		add_user_command = REDIS_SECRET_PREFIX + "ACL SETUSER " + username + " on >" + password + " " + REDIS_USER_ACCOUNT_PERMISSIONS
		add_user_response = REDIS_CLIENT.execute_command(
			add_user_command
		)

free_tier_redis_manager = FreeTierRedisManagerSpawner()