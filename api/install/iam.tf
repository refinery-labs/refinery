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
      "Sid": "VisualEditor1",
      "Effect": "Allow",
      "Action": [
        "sqs:ChangeMessageVisibilityBatch",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes",
        "sqs:DeleteMessageBatch",
        "sqs:SendMessageBatch",
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sns:Publish",
        "lambda:InvokeFunction",
        "lambda:InvokeAsync",
        "logs:CreateLogGroup"
      ],
      "Resource": "*"
    },
    {
        "Sid": "VisualEditor2",
        "Effect": "Allow",
        "Action": [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:log-group:*"
    },
    {
        "Sid": "VisualEditor3",
        "Effect": "Allow",
        "Action": "logs:PutLogEvents",
        "Resource": "arn:aws:logs:*:*:log-group:*:*:*"
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
	IAM policy for the Lambda packages CodeBuild project
*/
resource "aws_iam_role" "codebuild-refinery-builds-service-role" {
    name               = "codebuild-refinery-builds-service-role"
    path               = "/service-role/"
    assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY
}

/*
	IAM policy for trust relationship to CodeBuild
*/
resource "aws_iam_policy" "refinery_codebuild_base_policy" {
    name        = "refinery_codebuild_base_policy"
    path        = "/service-role/"
    description = "Policy used in trust relationship with CodeBuild"
    policy      = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/refinery-builds",
        "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/refinery-builds:*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::codepipeline-${var.region}-*"
      ],
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetBucketAcl",
        "s3:GetBucketLocation"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}",
        "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}/*"
      ],
      "Action": [
        "s3:PutObject",
        "s3:GetBucketAcl",
        "s3:GetBucketLocation"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": [
        "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}/nonexistant.zip",
        "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}/nonexistant.zip/*"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::refinery-lambda-build-packages-${var.s3_bucket_suffix}"
      ],
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketAcl",
        "s3:GetBucketLocation"
      ]
    }
  ]
}
POLICY
}

/*
	This attached the IAM policy to the IAM role for the
	CloudBuild IAM policies.
*/
resource "aws_iam_role_policy_attachment" "refinery_codebuild_builds_attachment" {
  role       = "${aws_iam_role.codebuild-refinery-builds-service-role.id}"
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-role/refinery_codebuild_base_policy"
}