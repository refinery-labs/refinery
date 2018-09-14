def main( lambda_input, context ):
	from datetime import datetime
	
	# Imports the Google BigQuery client library
	from google.cloud import bigquery
	
	storage_client = get_cloud_storage_client()
	
	bucket_base_path = "bigquery/{:%Y/%m/%d/%H/}".format(
	    datetime.now()
	)
	
	# Get leading number of minute because this runs every 10 minutes
	# to load the data into BigQuery
	leading_digit_of_minute = "{:%M}".format(
		datetime.now()
	)[0]
	
	# Add it to the base path so we can get all items in this range
	bucket_base_path = bucket_base_path + leading_digit_of_minute
	
	bucket = storage_client.get_bucket(
		"refinery_bq_pipeline"
	)
	
	file_blobs = bucket.list_blobs(
		prefix=bucket_base_path
	)
	
	# Get all file paths from bucket
	bucket_file_paths = []
	
	for file_path in file_blobs:
		bucket_file_paths.append(
			file_path.name
		)
		
	# Directories to laod
	directories_to_load = []
		
	# Enumerate all table names
	table_names = []
	for bucket_file_path in bucket_file_paths:
		table_name = bucket_file_path.split( "/" )[6]
		if not table_name in table_names:
			table_names.append(
				table_name
			)
			
		directories_to_load.append({
			"table_name": table_name,
			"path": "/".join(
				bucket_file_path.split(
					"/"
				)[ :-1 ]
			) + "/*"
		})
			
	# Create load job for each table
	bigquery_client = get_bigquery_client()
	
	for directory_to_load_data in directories_to_load:
		uri = "gs://refinery_bq_pipeline/" + directory_to_load_data[ "path" ]
		# Dataset for target
		# refinery_datasets
		dataset_ref = bigquery_client.dataset(
			"refinery_datasets"
		)
		job_config = bigquery.LoadJobConfig()
		job_config.autodetect = True
		job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
		load_job = bigquery_client.load_table_from_uri(
			uri,
			dataset_ref.table(
				directory_to_load_data[ "table_name" ]
			),
			job_config=job_config
		)  # API request
		
		result = load_job.result()  # Waits for table load to complete.
		
		# TODO - Add error checking for result.errors and result.error_results
		# https://googlecloudplatform.github.io/google-cloud-python/latest/bigquery/generated/google.cloud.bigquery.job.LoadJobConfig.html#google.cloud.bigquery.job.LoadJobConfig
		
	return directories_to_load
	
def get_bigquery_client():
	import json

	# Imports the Google BigQuery client library
	from google.cloud import bigquery
	
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
		
	bigquery.Client.from_service_account_dict = from_service_account_dict
	
	# And now we'll use it to set up Google Storage client
	bigquery_client = bigquery.Client.from_service_account_dict(
		rmemory.get( "bigquery_auto_importer_key", raw=True )
		#rmemory.get( "bigquery_auto_importer_key"  )
	)
	
	return bigquery_client
	
def get_cloud_storage_client():
	import json

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
		rmemory.get( "bigquery_auto_importer_key", raw=True )
		#rmemory.get( "bigquery_auto_importer_key"  )
	)
	
	return storage_client