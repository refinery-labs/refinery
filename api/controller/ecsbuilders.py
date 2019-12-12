from tornado import gen
from controller.base import BaseHandler

from utils.ecs_builders import aws_ecs_manager
from utils.general import logit

class GetBuilderECSIP( BaseHandler ):
	@gen.coroutine
	def get( self ):
		credentials = self.get_authenticated_user_cloud_configuration()
		logit( "Pulling builder IP address..." )
		ip_addresses = yield aws_ecs_manager.get_build_container_ips(
			credentials
		)

		self.write({
			"success": True,
			"ip_addresses": ip_addresses
		})