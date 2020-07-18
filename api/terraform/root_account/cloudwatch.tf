resource "aws_iam_role" "lambda_execution_cwl_to_kinesis_role" {
  name = "lambda_execution_cwl_to_kinesis_role"

  assume_role_policy = <<EOF
{
  "Statement": {
    "Effect": "Allow",
    "Principal": { "Service": "logs.us-west-2.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }
}
EOF
}

resource "aws_iam_role_policy" "lambda_execution_policy_for_cwl" {
  name = "permissions_policy_for_cwl"
  role = aws_iam_role.lambda_execution_cwl_to_kinesis_role.id

  policy = <<EOF
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "kinesis:PutRecord",
      "Resource": "${var.kinesis_stream_arn}"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "${aws_iam_role.lambda_execution_cwl_to_kinesis_role.arn}"
    }
  ]
}
EOF
}

resource "aws_cloudwatch_log_destination" "lambda_execution_info_destination" {
  name = "lambda_execution_info_destination"
  role_arn = aws_iam_role.lambda_execution_cwl_to_kinesis_role.arn
  target_arn = var.kinesis_stream_arn
}

data "aws_iam_policy_document" "lambda_execution_destination_policy" {
  statement {
    effect = "Allow"

    principals {
      type = "AWS"

      identifiers = [
        "*",
      ]
    }

    actions = [
      "logs:PutSubscriptionFilter",
    ]

    resources = [
      aws_cloudwatch_log_destination.lambda_execution_info_destination.arn,
    ]

/*
    TODO figure out why this isn't working as expected

    condition {
      test = "ForAnyValue:StringLike"

      variable = "aws:PrincipalOrgPaths"

      values = var.refinery_root_organization_ids
    }
*/
  }
}

resource "aws_cloudwatch_log_destination_policy" "test_destination_policy" {
  destination_name = aws_cloudwatch_log_destination.lambda_execution_info_destination.name
  access_policy = data.aws_iam_policy_document.lambda_execution_destination_policy.json
}