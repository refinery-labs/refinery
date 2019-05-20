/*
	The source package for the Node builder Lambda
*/
resource "aws_s3_bucket_object" "node-810-builder-lambda-package" {
  bucket = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
  key    = "node8.10-library-builder.zip"
  source = "node8.10-library-builder.zip"
  
  depends_on = ["aws_s3_bucket.lambda-build-packages"]
}

/*
	Builds Node npm packages and creates a zip file which it
	writes to S3 and returns the path of. This zip is used during
	the Refinery Lambda deployment process.
*/
resource "aws_lambda_function" "node-810-builder-lambda" {
  function_name    = "node810-builder-lambda"
  role             = "${aws_iam_role.refinery_builder_aws_lambda_role.arn}"
  handler          = "function.handler"
  runtime          = "provided"
  memory_size	   = "3008"
  timeout		   = "900"
  s3_bucket		   = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
  s3_key		   = "node8.10-library-builder.zip"

  environment {
    variables = {
      BUILD_BUCKET = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
    }
  }
  
  depends_on = ["aws_s3_bucket_object.node-810-builder-lambda-package"]
}

/*
	The source package for the Python builder Lambda
*/
resource "aws_s3_bucket_object" "python-27-builder-lambda-package" {
  bucket = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
  key    = "python2.7-library-builder.zip"
  source = "python2.7-library-builder.zip"
  
  depends_on = ["aws_s3_bucket.lambda-build-packages"]
}

/*
	Builds Python pip packages and creates a zip file which it
	writes to S3 and returns the path of. This zip is used during
	the Refinery Lambda deployment process.
*/
resource "aws_lambda_function" "python-27-builder-lambda" {
  function_name    = "python27-builder-lambda"
  role             = "${aws_iam_role.refinery_builder_aws_lambda_role.arn}"
  handler          = "function.handler"
  runtime          = "provided"
  memory_size	   = "3008"
  timeout		   = "900"
  s3_bucket		   = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
  s3_key		   = "python2.7-library-builder.zip"

  environment {
    variables = {
      BUILD_BUCKET = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
    }
  }
  
  depends_on = ["aws_s3_bucket_object.python-27-builder-lambda-package"]
}