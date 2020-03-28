from controller import BaseHandler
from models import User


class HealthHandler( BaseHandler ):
	def get( self ):
		# Just run a dummy database query to ensure it's working
		self.dbsession.query( User ).first()
		self.write({
			"success": True,
			"status": "ok"
		})
