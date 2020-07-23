
resource "aws_lambda_function" "limiter_lambda" {
  filename      = "FreeTierConcurrencyLimiter.zip"
  function_name = "FreeTierConcurrencyLimiter"
  role          = aws_iam_role.limiter_lambda_iam_role.arn
  handler       = "index.handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = filebase64sha256("FreeTierConcurrencyLimiter.zip")

  runtime = "nodejs10.x"
  memory_size = 128
  timeout = 5

  tags = {
    RefineryResource = "true"
  }

  # We set this to 995 to allow free-tier users to have five
  # free concurrent Lambdas for their usage. This is to limit
  # the amount of abuse possible by executing lots of Lambdas
  # quickly (and to provide an incentive to switch to paid).
  reserved_concurrent_executions = 900

  depends_on = [
    "aws_iam_role_policy_attachment.lambda_logs",
    "aws_cloudwatch_log_group.limiter_lambda_log_group"
  ]
}

# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "limiter_lambda_log_group" {
  name              = "/aws/lambda/FreeTierConcurrencyLimiter"
  retention_in_days = 1
}

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "limiter_lambda_logging_policy" {
  name = "FreeTierConcurrencyLimiterLoggingPolicy"
  path = "/"
  description = "IAM policy for FreeTierConcurrencyLimiter"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role = aws_iam_role.limiter_lambda_iam_role.name
  policy_arn = aws_iam_policy.limiter_lambda_logging_policy.arn
}

resource "aws_iam_role" "limiter_lambda_iam_role" {
  name = "FreeTierConcurrencyLimiterLoggingRole"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}