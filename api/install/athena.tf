resource "aws_athena_database" "refinery_athena_db" {
	name   = "refinery"
	bucket = aws_s3_bucket.lambda-logging.id
}

resource "aws_athena_workgroup" "refinery_workgroup" {
	name = "refinery_workgroup"
	
	tags = {
		RefineryResource = "true"
	}
}