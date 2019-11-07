import zipfile

EMPTY_ZIP_DATA = bytearray( "PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" )


# Given a zip file handler, writes the given contents at the path. Handles setting file permissions.
def write_file_to_zip( zip_file_handler, path, contents ):
	file_info = zipfile.ZipInfo(path)
	file_info.external_attr = 0777 << 16L
	zip_file_handler.writestr(
		file_info,
		contents
	)
