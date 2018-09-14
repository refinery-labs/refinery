* Add the ability to run code locally for testing
	* Chmod to temporary directory
	* Delete directory after run
* System for managing key/values stored in redis instead of redis-commander
* REQUIRE that all SQS deployed lambdas have a valid JSON Schema for messages (write details in S3).
	* This keeps errors low and makes generating messages more structured.
	* Makes everything more maintainable since you know the exact format required.
* Create service to generate SQS messages for scraping ranges
	* 1-1000 IDs of a web endpoint
* Add code to all lambdas to detect successful and unsuccessful runs
	* Query redis on failures and activate certain actions
		* Email about failure
* Add max size of 80 for names of Lambdas, Queues, etc
* Add SQS trigger processing for Step Functions
* Add API Gateway trigger to refinery
* Add conditions to refinery (if/else)
* Job emailer using Apps Scripts
	* https://developers.google.com/apps-script/guides/services/quotas
* Create Chrome extension for generating code for refinery from HTTP traffic
* Set up central redis for configs for lambdas
	* Cookies
	* User-Agents