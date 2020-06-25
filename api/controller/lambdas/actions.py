from tornado import gen

from utils.block_libraries import generate_libraries_dict


@gen.coroutine
def is_build_package_cached(task_spawner, credentials, language, libraries):
    # If it's an empty list just return True
    if len(libraries) == 0:
        raise gen.Return(True)

    libraries_dict = generate_libraries_dict(libraries)

    # Get the final S3 path
    final_s3_package_zip_path = yield task_spawner.get_final_zip_package_path(
        language,
        libraries_dict,
    )

    # Get if the package is already cached
    is_already_cached = yield task_spawner.s3_object_exists(
        credentials,
        credentials["lambda_packages_bucket"],
        final_s3_package_zip_path
    )

    raise gen.Return(is_already_cached)
