* Add max size of 80 for names of Lambdas, Queues, etc
* Add SQS trigger processing for Step Functions
* Add API Gateway trigger to refinery
* Add conditions to refinery (if/else)
* REQUIRE that all SQS deployed lambdas have a valid JSON Schema for messages (write details in S3).
	* This keeps errors low and makes generating messages more structured.
	* Makes everything more maintainable since you know the exact format required.
* Create service to generate SQS messages for scraping ranges
	* 1-1000 IDs of a web endpoint
* Re-usable quick search function database
	* Fuzzy quick searching
	* Attributes
		* Name
		* Description
		* Code
* Job emailer using Apps Scripts
	* https://developers.google.com/apps-script/guides/services/quotas
* JSON Schema for Step Function and Lambda input formats
	* Tags on SFN and Lambda with S3 link to full schema
* Create Lambda to automatically load data from Google Cloud storage bucket into BigQuery using auto-schema
	* Format of /bigquery/2018/09/10/10/30/hackernews/22b5f6c3-3ca0-4b53-bfb2-39479fd2ef13.json
	* e.g. /bigquery/{YYYY}/{{MM}}/{{DD}}/{{HH}}/{{MM}}/{{TABLE_NAME}}/{{UUID}}.json
	* Lambda runs every ten minutes to load data into BigQuery if data exists to be loaded.
	* Bucket retains objects for only 24 hours before automatic deletion
	* Max 1K loads a day per table
* Create Chrome extension for generating code for refinery from HTTP traffic
* Set up central redis for configs for lambdas
	* Cookies
	* User-Agents