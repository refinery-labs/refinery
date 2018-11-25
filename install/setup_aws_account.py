#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
import boto3
import json
import os

IAM_CLIENT = boto3.client(
    "iam",
    aws_access_key_id=os.environ.get( "aws_access_key" ),
    aws_secret_access_key=os.environ.get( "aws_secret_key" ),
    region_name=os.environ.get( "region_name" )
)
		
def setup_lambda_iam():
	iam_role_name = "refinery_aws_lambda_admin_role"
	iam_policy_name = "refinery_aws_lambda_admin_policy"
	
	print( "Creating Lambda IAM policy..." )
	create_policy_response = IAM_CLIENT.create_policy(
		PolicyName=iam_policy_name,
		PolicyDocument=json.dumps({
		"Version": "2012-10-17",
		"Statement": [
				{
					"Action": "*",
					"Effect": "Allow",
					"Resource": "*"
				}
			]
		}),
		Description="refinery AWS Lambda admin runtime IAM policy."
	)
	iam_policy_arn = create_policy_response[ "Policy" ][ "Arn" ]
	print( "Policy ARN: " + iam_policy_arn )
	
	print( "Creating IAM role..." )
	create_role_response = IAM_CLIENT.create_role(
		RoleName=iam_role_name,
		AssumeRolePolicyDocument=json.dumps({
			"Version": "2012-10-17",
			"Statement": [
				{
					"Effect": "Allow",
					"Principal": {
						"Service": "lambda.amazonaws.com"
					},
					"Action": "sts:AssumeRole"
				},
				{
					"Effect": "Allow",
					"Principal": {
						"Service": "events.amazonaws.com"
					},
					"Action": "sts:AssumeRole"
				}
			]
		}),
		Description="refinery AWS Lambda admin runtime IAM role.",
	)
	
	iam_role_arn = create_role_response[ "Role" ][ "Arn" ]
	
	print( "Attaching IAM policy to role..." )
	attach_role_policy_response = IAM_CLIENT.attach_role_policy(
		RoleName=iam_role_name,
		PolicyArn=iam_policy_arn
	)
	
	return iam_role_arn

def setup_events_iam():
	iam_role_name = "refinery_aws_cloudwatch_admin_role"
	iam_policy_name = "refinery_aws_cloudwatch_admin_policy"
	
	print( "Creating Events IAM policy..." )
	create_policy_response = IAM_CLIENT.create_policy(
		PolicyName=iam_policy_name,
		PolicyDocument=json.dumps({
			"Version": "2012-10-17",
			"Statement": [
				{
					"Effect": "Allow",
					"Action": [
						"cloudformation:DescribeChangeSet",
						"cloudformation:DescribeStackResources",
						"cloudformation:DescribeStacks",
						"cloudformation:GetTemplate",
						"cloudformation:ListStackResources",
						"cloudwatch:*",
						"cognito-identity:ListIdentityPools",
						"cognito-sync:GetCognitoEvents",
						"cognito-sync:SetCognitoEvents",
						"dynamodb:*",
						"ec2:DescribeSecurityGroups",
						"ec2:DescribeSubnets",
						"ec2:DescribeVpcs",
						"events:*",
						"iam:GetPolicy",
						"iam:GetPolicyVersion",
						"iam:GetRole",
						"iam:GetRolePolicy",
						"iam:ListAttachedRolePolicies",
						"iam:ListRolePolicies",
						"iam:ListRoles",
						"iam:PassRole",
						"iot:AttachPrincipalPolicy",
						"iot:AttachThingPrincipal",
						"iot:CreateKeysAndCertificate",
						"iot:CreatePolicy",
						"iot:CreateThing",
						"iot:CreateTopicRule",
						"iot:DescribeEndpoint",
						"iot:GetTopicRule",
						"iot:ListPolicies",
						"iot:ListThings",
						"iot:ListTopicRules",
						"iot:ReplaceTopicRule",
						"kinesis:DescribeStream",
						"kinesis:ListStreams",
						"kinesis:PutRecord",
						"kms:ListAliases",
						"lambda:*",
						"logs:*",
						"s3:*",
						"sns:ListSubscriptions",
						"sns:ListSubscriptionsByTopic",
						"sns:ListTopics",
						"sns:Publish",
						"sns:Subscribe",
						"sns:Unsubscribe",
						"sqs:ListQueues",
						"sqs:SendMessage",
						"tag:GetResources",
						"xray:PutTelemetryRecords",
						"xray:PutTraceSegments"
					],
					"Resource": "*"
				}
			]
		}),
		Description="refinery AWS CloudWatch admin runtime IAM policy."
	)
	iam_policy_arn = create_policy_response[ "Policy" ][ "Arn" ]
	
	print( "Policy ARN: " + iam_policy_arn )
	
	print( "Creating IAM role..." )
	create_role_response = IAM_CLIENT.create_role(
		RoleName=iam_role_name,
		AssumeRolePolicyDocument=json.dumps({
			"Version": "2012-10-17",
			"Statement": [
				{
					"Effect": "Allow",
					"Principal": {
						"Service": "events.amazonaws.com"
					},
					"Action": "sts:AssumeRole"
				}
			]
		}),
		Description="refinery AWS CloudWatch admin runtime IAM role.",
	)
	
	iam_role_arn = create_role_response[ "Role" ][ "Arn" ]
	
	print( "Attaching IAM policy to role..." )
	attach_role_policy_response = IAM_CLIENT.attach_role_policy(
		RoleName=iam_role_name,
		PolicyArn=iam_policy_arn
	)
	
	return iam_role_arn

cloudwatch_iam_role_arn = setup_events_iam()
lambda_iam_role_arn = setup_lambda_iam()
print( """

	AWS CONFIGURATION COMPLETE

""" )
print( "CloudWatch IAM policy ARN: " )
print( cloudwatch_iam_role_arn )

print( "Lambda IAM policy ARN: " )
print( lambda_iam_role_arn )