# Outputs the AWS account ID
output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

# Outputs the AWS region
output "aws_region" {
  value = var.region
}

# Outputs the S3 prefix
output "s3_suffix" {
  value = var.s3_bucket_suffix
}

# Outputs the Lambda packages S3 bucket ARN
output "lambda_packages_s3_bucket_arn" {
  value = aws_s3_bucket.lambda-build-packages.arn
}

# Outputs the Lambda logging S3 bucket ARN
output "lambda_logging_s3_bucket_arn" {
  value = aws_s3_bucket.lambda-logging.arn
}

# Outputs the Lambda logging S3 bucket ID
output "lambda_logging_s3_bucket_id" {
  value = aws_s3_bucket.lambda-logging.id
}

# Outputs the Lambda packages S3 bucket ID
output "lambda_packages_s3_bucket_id" {
  value = aws_s3_bucket.lambda-build-packages.id
}

//output "serverless_framework_builder_arn" {
//  value = module.serverless_framework_builder.this_lambda_function_arn
//}
//
//output "docker_container_modifier_arn" {
//  value = module.docker_container_modifier.this_lambda_function_arn
//}
