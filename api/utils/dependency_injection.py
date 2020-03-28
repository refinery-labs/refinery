def merge_dependencies(deps1, deps2):
	out_deps = deps1.copy()
	out_deps.update(deps2)
	return out_deps


def valid_handler_config(handler_config):
	"""
	Enforce that the handler config is of the form:
		("path", handler)
		-- or --
		("path", handler, dependencies)

	:param handler_config:
	:return:
	"""
	if len(handler_config) >= 2 and \
			type(handler_config[0]) is str and \
			type(handler_config[1]) is type:

		# TODO enforce that handler_config[1] is a subclass of BaseHandler?

		# Config only has at least a route and handler class...

		if len(handler_config) == 2:
			# Config only has route and handler class
			return True

		elif len(handler_config) == 3 and \
				type(handler_config[2]) is dict:
			# Config also as dependencies to inject
			return True
		else:
			return False
	return False


def get_deps_from_handler_config(handler_config):
	if len(handler_config) == 3:
		return handler_config[2]
	return dict()


def inject_handler_dependencies(common_dependencies, handler_configs):
	tornado_urls = []
	for handler_config in handler_configs:
		if not valid_handler_config(handler_config):
			raise Exception("provided handler config is not valid {}".format(handler_config))

		deps = get_deps_from_handler_config(handler_config)
		merged_deps = merge_dependencies(common_dependencies, deps)

		url_path = handler_config[0]
		handler_class = handler_config[1]
		tornado_url = (url_path, handler_class, merged_deps)

		tornado_urls.append(tornado_url)

	return tornado_urls
