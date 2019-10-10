import zipfile
import io

from utils.general import logit

SHARED_FILE_PREFIX = "shared_files/"

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