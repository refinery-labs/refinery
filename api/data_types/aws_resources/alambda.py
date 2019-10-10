class Lambda():
	def __init__(self,
				name,
				language,
				code,
				libraries,
				max_execution_time,
				memory,
				transitions,
				execution_mode,
				execution_pipeline_id,
				execution_log_level,
				environment_variables,
				layers=[],
				reserved_concurrency_count=False,
				is_inline_execution=False,
				shared_files_list=[]
				):
		self.name = name
		self.language = language
		self.code = code
		self.libraries = libraries
		self.max_execution_time = max_execution_time
		self.memory = memory
		self.transitions = transitions
		self.execution_mode = execution_mode
		self.execution_pipeline_id = execution_pipeline_id
		self.execution_log_level = execution_log_level
		self.environment_variables = environment_variables
		self.layers = layers
		self.reserved_concurrency_count = reserved_concurrency_count
		self.is_inline_execution = is_inline_execution
		self.shared_files_list = shared_files_list
		self.role = ""
		self.vpc_data = {}
		self.tags_dict = {}