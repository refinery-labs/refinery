## What
This folder includes utilities to delete logs for a given ARN in a Refinery account's log buckets.

## Why
If there are ever extraneous logs in an S3 bucket that you want to delete, the process of deleting them is not simple.

You have to perform the following steps:
- Login to the customer account and view the project
- Grab the ARN of the Lambda for the "bad logs" from the errors in the console
- Log into the root account for the given customer account (requires password reset)
- Query Athena to get the logs for the given ARN and return the S3 $path
- Get AWS credentials for the AWS-CLI to get access to the S3 bucket
- Iterate over the list of $path for every log
- Run a delete operation in the S3 bucket

It's kind of a pain.

## How to use this

Follow the steps above. A few of them have scripts to help.

### Logging into Root AWS Athena console
Grab the customer's AWS email account from the production database with the following query:
```genericsql
SELECT aws_account_email FROM aws_accounts
JOIN users ON aws_accounts.organization_id = users.organization_id 
WHERE users.email LIKE '<CUSTOMER_EMAIL>';
```

Example Values:
```
CUSTOMER_EMAIL=foobar@foo.com
```

### Athena query to generate CSV of S3 paths
```genericsql
SELECT "$path", arn, function_name FROM "refinery"."<S3_PROJECT_LOG_PATH>"
WHERE project_id = '<PROJECT_ID>' 
  AND arn = '<BAD_ARN>';
```

Example Values:
```
S3_PROJECT_LOG_PATH=prj_c23014a1_4c4a_4610_9b2f_5c46faf23592
PROJECT_ID=c23014a1-4c4a-4610-9b2f-5c46faf23592
BAD_ARN=arn:aws:lambda:us-west-2:888864892313:function:DO_EVERY_MORNING240574c1-77ab-471f-9b2b-126668a20247
```

You can down a CSV from the results in the Athena console after.

### Converting the CSV to Sqlite
Make sure you run `pipenv install` to get the dependencies for this folder.
When you run the script, make sure it is run in this folder alongside the `delete-s3-logs-from-db.py` script.

```shell script
pipenv run csv-to-sqlite -f <PATH_TO_CSV>
```

That should generate a file called `s3-log-deleter.db` which is used in the next scripts.

### Fill in blanks in the script
In the file `delete-s3-logs-from-db.py` fill in the blanks for variables.

You'll have to generate an IAM key pair from the root account to allow Boto3 to access the bucket.
This can be done in the AWS console.

### Run the script
You should be able to run `pipenv run ./delete-s3-logs-from-db.py` and it'll print if it's successful.
