import zipfile
import io

from utils.general import logit

SHARED_FILE_PREFIX = "shared_files/"


def add_shared_files_symlink_to_zip( zip_data ):
	virtual_file_handler = io.BytesIO( zip_data )

	with zipfile.ZipFile( virtual_file_handler, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
		# Big shout out to A. Murat Eren: https://www.mail-archive.com/python-list@python.org/msg34223.html
		# Magic to add a soft link to /var/task/shared_files/ to /tmp/shared_files/
		# This allows us to write all of the shared files for inline executions without a re-deploy.
		attr = zipfile.ZipInfo()
		attr.filename = "shared_files"
		attr.create_system = 3
		attr.external_attr = 2716663808L
		zip_file_handler.writestr(attr, "/tmp/shared_files/")

	final_zip_data = virtual_file_handler.getvalue()
	virtual_file_handler.close()

	return final_zip_data


def add_shared_files_to_zip( zip_data, shared_files_list ):
	lambda_package_zip = io.BytesIO(
		zip_data
	)

	with zipfile.ZipFile( lambda_package_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
		for shared_file_metadata in shared_files_list:
			shared_file_name = str( SHARED_FILE_PREFIX + shared_file_metadata[ "name" ] )
			new_zip_file = zipfile.ZipInfo(
				shared_file_name
			)

			new_zip_file.external_attr = 0777 << 16L

			zip_file_handler.writestr(
				new_zip_file,
				str( shared_file_metadata[ "body" ] )
			)

	final_zip_data = lambda_package_zip.getvalue()
	lambda_package_zip.close()

	return final_zip_data


def get_shared_files_for_lambda( lambda_id, diagram_data ):
	if not "workflow_file_links" in diagram_data:
		return []

	workflow_file_ids = get_workflow_file_links_by_node_id(
		lambda_id,
		diagram_data[ "workflow_file_links" ]
	)

	shared_files = []

	for workflow_file_id in workflow_file_ids:
		shared_files.append(
			get_workflow_file_by_id(
				workflow_file_id,
				diagram_data[ "workflow_files" ]
			)
		)

	return shared_files


def get_workflow_file_links_by_node_id( lambda_id, workflow_file_links ):
	workflow_file_ids = []

	for workflow_file_link in workflow_file_links:
		if workflow_file_link[ "node" ] == lambda_id:
			workflow_file_ids.append(
				workflow_file_link["file_id" ]
			)

	return workflow_file_ids


def get_workflow_file_by_id( workflow_file_id, workflow_files ):
	for workflow_file in workflow_files:
		if workflow_file[ "id" ] == workflow_file_id:
			return workflow_file

	raise Exception("No workflow_file found with ID" + workflow_file_id)