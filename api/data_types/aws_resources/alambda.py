class Lambda:
	def __init__(self, **kwargs):
		self.name = kwargs[ "name" ]
		self.language = kwargs[ "language" ]
		self.code = kwargs[ "code" ]
		self.libraries = kwargs[ "libraries" ]
		self.max_execution_time = kwargs[ "max_execution_time" ]
		self.memory = kwargs[ "memory" ]
		self.transitions = kwargs[ "transitions" ]
		self.execution_mode = kwargs[ "execution_mode" ]
		self.execution_pipeline_id = kwargs[ "execution_pipeline_id" ]
		self.execution_log_level = kwargs[ "execution_log_level" ]
		self.environment_variables = kwargs[ "environment_variables" ]
		self.layers = kwargs[ "layers" ]
		self.reserved_concurrency_count = kwargs[ "reserved_concurrency_count" ]
		self.is_inline_execution = kwargs[ "is_inline_execution" ]
		self.shared_files_list = kwargs[ "shared_files_list" ]
		self.transform = kwargs[ "transform" ]
		self.role = ""
		self.vpc_data = {}
		self.tags_dict = {}