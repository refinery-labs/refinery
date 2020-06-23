INTERNAL_ERROR_MSG = 'When deploying this project, Refinery experienced an internal error.\nPlease reach out to the Refinery devs if this problem persists.'


class InvalidDeployment(Exception):
	pass


class DeploymentException(Exception):
	def __init__(self, node_id, name, node_type, internal_error, msg):
		self.id = node_id
		self.name = name
		self.node_type = node_type
		self.internal_error = internal_error
		self.msg = msg

	def __str__(self):
		return f'name: {self.name}, id: {self.id}, type: {self.node_type}, exception:\n{self.msg}'

	def serialize(self):
		msg = self.msg if not self.internal_error else INTERNAL_ERROR_MSG
		return {
			'name': self.name,
			'id': self.id,
			'type': self.node_type,
			'exception': msg
		}


