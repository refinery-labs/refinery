from tornado import gen


@gen.coroutine
def is_build_package_cached( local_tasks, credentials, language, libraries ):
	# If it's an empty list just return True
	if len( libraries ) == 0:
		raise gen.Return( True )

	# TODO just accept a dict/object in of an
	# array followed by converting it to one.
	libraries_dict = {}
	for library in libraries:
		libraries_dict[ str( library ) ] = "latest"

	# Get the final S3 path
	final_s3_package_zip_path = yield local_tasks.get_final_zip_package_path(
		language,
		libraries_dict,
	)

	# Get if the package is already cached
	is_already_cached = yield local_tasks.s3_object_exists(
		credentials,
		credentials[ "lambda_packages_bucket" ],
		final_s3_package_zip_path
	)

	raise gen.Return( is_already_cached )



