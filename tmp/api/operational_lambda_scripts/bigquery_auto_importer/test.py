import uuid

def main( lambda_input, context ):
    """
    Embedded magic

    Refinery memory:
	    Namespace: rmemory.get( "example" )
	    Without namespace: rmemory.get( "example", raw=True )

    SQS message body:
	    First message: lambda_input[ "Records" ][0][ "body" ]
    """
    bs_data_array = []
    
    for i in range( 0, 1000 ):
    	bs_data_array.append({
    		"id": i,
    		"uuid": str( uuid.uuid4() ),
    		"static": "the same",
    		"float": float( i ),
    	})
    	
    send_to_bigquery(
    	"bs_data",
    	bs_data_array
    )

def get_bucket_base_path():
	from datetime import datetime
	
	return "bigquery/{:%Y/%m/%d/%H/%M/}".format(
	    datetime.now()
	)
	
def send_to_bigquery( table_name, input_array_of_flat_dicts ):
	"""
	Send to Refinery's BigQuery data lake.
	
	Set the name of the table to be created and pass a list of
	structure, flat, key-value dicts. Keys become the column names
	and the values become rows in the table.
	
	:param str table_name "Name of table"
	:param list	input_array_of_flat_dicts [{"example": "example"}]
	"""
	import uuid
	import json
	
	file_data = ""
	
	for dict_item in input_array_of_flat_dicts:
		file_data += json.dumps(
			dict_item
		) + "\n"
		
	data_bucket_path = get_bucket_base_path()
	
	data_bucket_path += table_name.replace(
	    "/",
	    "_"
	)

	data_bucket_path += "/" + str( uuid.uuid4() ) + ".json"
	
	storage_client = get_cloud_storage_client()
	
	bucket = storage_client.get_bucket(
		"refinery_bq_pipeline"
	)
	
	response = bucket.blob(
		data_bucket_path
	).upload_from_string(
		file_data
	)
	
	return response

def get_cloud_storage_client():
	import json
	import os
	
	# Imports the Google Cloud client library
	from google.cloud import storage
	
	# Patch in a new method for loading a dict
	@classmethod
	def from_service_account_dict(cls, credentials_info, *args, **kwargs):
		# Need this for the monkeypatch
		from google.oauth2 import service_account
		credentials = service_account.Credentials.from_service_account_info(
			credentials_info
		)
		if cls._SET_PROJECT:
			if "project" not in kwargs:
				kwargs[ "project" ] = credentials_info.get( "project_id" )
		
		kwargs[ "credentials" ] = credentials
		return cls(*args, **kwargs)
		
	storage.Client.from_service_account_dict = from_service_account_dict
	
	# And now we'll use it to set up Google Storage client
	storage_client = storage.Client.from_service_account_dict(
		rmemory.get( "google_cloud_storage_key", raw=True )
	)
	
	return storage_client