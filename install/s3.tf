/*
	The S3 bucket used for Lambda log storage. By default this does
	not have an object-expiration policy attached to it.
*/
resource "aws_s3_bucket" "lambda-logging" {
    bucket = "refinery-lambda-logging-${var.s3_bucket_suffix}"
    acl    = "private"
}

/*
	S3 bucket for built Lambda packages, this is where the zip files
	of all of the npm/pip/etc packages are stored. This bucket has an
	object expiration policy of 1-day to automatically clear uploaded
	packages after a day. This is important as it allows for package
	updates to be loaded after the object falls out of the cache. For
	example if the requests library gets an update then the latest
	version will be included after the previously-cached zip is expired
	from the cache.
*/
resource "aws_s3_bucket" "lambda-build-packages" {
    bucket = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
    acl    = "private"
    
	lifecycle_rule {
		enabled = true
		
		expiration {
			days = 1
		}
		
		noncurrent_version_expiration {
			days = 1
		}
		
		abort_incomplete_multipart_upload_days = 1
	}
}