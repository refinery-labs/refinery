* BigQuery Auto Importer does too many daily loads! Make every 3 minutes or something...
---
* Create Chrome extension for generating code for refinery from HTTP traffic
* Add the ability to run code locally for testing
	* Chmod to temporary directory
	* Delete directory after run
* Optimize redis client injection to only initialize connect on first use (instead of always connecting)
* System for managing key/values stored in redis instead of redis-commander
* Add code to all lambdas to detect successful and unsuccessful runs
	* Query redis on failures and activate certain actions
		* Email about failure
* Add max size of 80 for names of Lambdas, Queues, etc
* Add SQS trigger processing for Step Functions
* Add API Gateway trigger to refinery
* Add conditions to refinery (if/else)
* Set up central redis for configs for lambdas
	* Cookies
	* User-Agents

NOTE, SQS loading time (for pushing items into the queue in 10 items per request batches):
10K = 4.2 seconds
100K = 34.78 seconds