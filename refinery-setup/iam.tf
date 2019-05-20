/*
	The default AWS IAM policy for Lambdas deployed by Refinery.
	
	This IAM policy needs to be updated upon new resource blocks being
	added to Refinery. Currently the blocks are the following:
	* API Endpoint & API Response blocks (API Gateway)
	* SNS Topic Trigger block (SNS)
	* SQS Queue Trigger block (SQS)
	* Lambda block (Lambda)
	
	For any new core blocks the IAM policy will need to be updated.
	This is because the Lambdas will need new permissions to act against
	new AWS service lines. For example, if in the future we support the
	AWS Kinesis service, it is likely this policy will need to have the
	lowest-possible permissions to interact with the Kinesis API.
*/
resource "aws_iam_policy" "refinery_default_aws_lambda_policy" {
    name        = "refinery_default_aws_lambda_policy"
    path        = "/"
    description = "Default Refinery AWS Lambda runtime IAM policy."
    policy      = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VisualEditor0",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::refinery-lambda-logging-${var.s3_bucket_suffix}/*"
    },
    {
      "Sid": "VisualEditor2",
      "Effect": "Allow",
      "Action": [
        "sqs:DeleteMessage",
        "sns:Publish",
        "lambda:InvokeFunction",
        "sqs:ReceiveMessage",
        "lambda:InvokeAsync",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
}

/*
	Defines the default IAM role for the deployed Refinery
	Lambdas to assume. The assume role policy defines what
	type of AWS resources can assume a given role (EC2, Lambda, etc).
*/
resource "aws_iam_role" "refinery_default_aws_lambda_role" {
  name = "refinery_default_aws_lambda_role"

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

/*
	This attached the IAM policy to the IAM role for the
	default Lambda IAM permissions.
*/
resource "aws_iam_role_policy_attachment" "refinery_default_aws_lambda_attachment" {
  role       = "${aws_iam_role.refinery_default_aws_lambda_role.id}"
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/refinery_default_aws_lambda_policy"
}

/*
	The permissions policy for CloudWatch Events deployed by
	Refinery. This allows CloudWatch to trigger the underlying
	Lambdas built and deployed by Refinery.
*/
resource "aws_iam_policy" "refinery_default_aws_cloudwatch_policy" {
    name        = "refinery_default_aws_cloudwatch_policy"
    path        = "/"
    description = "Default Refinery AWS CloudWatch admin runtime IAM policy."
    policy      = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VisualEditor0",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:InvokeAsync"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
}

/*
	Defines the default IAM role for the deployed Refinery
	CloudWatch Events to assume. The assume role policy defines what
	type of AWS resources can assume a given role (EC2, Lambda, etc).
*/
resource "aws_iam_role" "refinery_default_aws_cloudwatch_role" {
  name = "refinery_default_aws_cloudwatch_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

/*
	This attached the IAM policy to the IAM role for the
	default CloudWatch IAM permissions.
*/
resource "aws_iam_role_policy_attachment" "refinery_default_aws_cloudwatch_attachment" {
  role       = "${aws_iam_role.refinery_default_aws_cloudwatch_role.id}"
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/refinery_default_aws_cloudwatch_policy"
}

/*
	The IAM policy for builder Lambdas. They have special permissions
	for both Heading and Puting to the packages S3 bucket.
	
	Note that the permissions here are odd because of fun bugs in AWS S3:
	https://github.com/aws/aws-cli/issues/1689#issuecomment-167629066
	
	These permissions would be more scoped if they could be - but alas it
	cannot be done at this time.
	
	Why Amazon, why?
*/
resource "aws_iam_policy" "refinery_builder_aws_lambda_policy" {
    name        = "refinery_builder_aws_lambda_policy"
    path        = "/"
    description = "IAM policy for builder Lambdas."
    policy      = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VisualEditor0",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}/*"
    },
    {
      "Sid": "VisualEditor1",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}/*"
    },
    {
        "Sid": "VisualEditor2",
        "Effect": "Allow",
        "Action": "s3:GetAccountPublicAccessBlock",
        "Resource": "*"
    },
    {
      "Sid": "VisualEditor3",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}"
    }
  ]
}
POLICY
}

/*
	IAM role for builder Lambdas to use.
*/
resource "aws_iam_role" "refinery_builder_aws_lambda_role" {
  name = "refinery_builder_aws_lambda_role"

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

/*
	Ties the builder Lambda IAM policy to the IAM role.
*/
resource "aws_iam_role_policy_attachment" "refinery_builder_aws_lambda_attachment" {
  role       = "${aws_iam_role.refinery_builder_aws_lambda_role.id}"
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/refinery_builder_aws_lambda_policy"
}