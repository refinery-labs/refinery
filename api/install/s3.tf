/*
	The S3 bucket used for Lambda log storage. By default this does
	not have an object-expiration policy attached to it.
*/
resource "aws_s3_bucket" "lambda-logging" {
  bucket = "refinery-lambda-logging-${var.s3_bucket_suffix}"
  acl    = "private"

  lifecycle_rule {
    id     = "bucket_root"
    prefix = ""

    enabled = true

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      days = 7
    }

    abort_incomplete_multipart_upload_days = 7
  }

  lifecycle_rule {
    id     = "athena_query_output"
    prefix = "athena/"

    enabled = true

    expiration {
      days = 1
    }

    noncurrent_version_expiration {
      days = 1
    }

    abort_incomplete_multipart_upload_days = 1
  }

  lifecycle_rule {
    id     = "code_block_log_result_pages"
    prefix = "log_pagination_result_pages/"

    enabled = true

    expiration {
      days = 1
    }

    noncurrent_version_expiration {
      days = 1
    }

    abort_incomplete_multipart_upload_days = 1
  }

  lifecycle_rule {
    id     = "temporary_code_block_execution_outputs"
    prefix = "temporary_executions/"

    enabled = true

    expiration {
      days = 1
    }

    noncurrent_version_expiration {
      days = 1
    }

    abort_incomplete_multipart_upload_days = 1
  }

  tags = {
    RefineryResource = "true"
  }
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
      days = 14
    }

    noncurrent_version_expiration {
      days = 14
    }

    abort_incomplete_multipart_upload_days = 1
  }

  tags = {
    RefineryResource = "true"
  }
}

