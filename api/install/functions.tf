//module "serverless_framework_builder" {
//  source = "terraform-aws-modules/lambda/aws"
//
//  function_name = "serverless-framework-builder"
//  description   = "Build serverless framework projects."
//  handler       = "index.lambdaHandler"
//  runtime       = "nodejs12.x"
//  timeout       = 900
//
//  create_package = false
//  local_existing_package = "${path.module}/functions/serverless-framework-builder/package.zip"
//
//  vpc_subnet_ids         = module.vpc.intra_subnets
//  vpc_security_group_ids = [module.vpc.default_security_group_id]
//  attach_network_policy  = true
//
//  file_system_arn              = aws_efs_access_point.lambda.arn
//  file_system_local_mount_path = "/mnt/efs"
//
//  # Explicitly declare dependency on EFS mount target.
//  # When creating or updating Lambda functions, mount target must be in 'available' lifecycle state.
//  # Note: depends_on on modules became available in Terraform 0.13
//  depends_on = [aws_efs_mount_target.alpha]
//  attach_policy_json = true
//  policy_json        = <<EOF
//{
//    "Version": "2012-10-17",
//    "Statement": [
//        {
//            "Effect": "Allow",
//            "Action": [
//              "s3:*",
//              "cloudformation:*",
//              "iam:*",
//              "lambda:*",
//              "apigateway:*",
//              "sqs:*",
//              "logs:*"
//            ],
//            "Resource": ["*"]
//        }
//    ]
//}
//EOF
//}
//
//module "docker_container_modifier" {
//  source = "terraform-aws-modules/lambda/aws"
//
//  function_name = "docker-container-modifier"
//  description = "Build serverless framework projects."
//  handler = "main"
//  runtime = "go1.x"
//  timeout = 900
//
//  environment_variables = {
//    REFINERY_RUNTIME_CONTAINER_REPOSITORY: "public.ecr.aws/d7v1k2o3/refinery-container-runtime"
//  }
//
//  create_package = false
//  local_existing_package = "${path.module}/functions/docker-container-modifier/package.zip"
//
//  environment_variables = {}
//
//  attach_policy_json = true
//  policy_json        = <<EOF
//{
//    "Version": "2012-10-17",
//    "Statement": [
//        {
//            "Effect": "Allow",
//            "Action": [
//              "ecr:*"
//            ],
//            "Resource": ["*"]
//        }
//    ]
//}
//EOF
//}
//
//######
//# VPC
//######
//
//data "aws_security_group" "default" {
//  name   = "default"
//  vpc_id = module.vpc.vpc_id
//}
//
//module "vpc" {
//  source = "terraform-aws-modules/vpc/aws"
//
//  name = "lambda-builder-vpc"
//  cidr = "10.10.0.0/16"
//
//  azs           = ["us-west-2a"]
//  intra_subnets = ["10.10.1.0/24"]
//  private_subnets = ["10.10.10.0/24"]
//  public_subnets  = ["10.10.100.0/24"]
//
//  enable_dns_support = true
//  enable_dns_hostnames = true
//  instance_tenancy = "default"
//
//  enable_s3_endpoint = true
//}
//
//######
//# EFS
//######
//
//resource "aws_efs_file_system" "shared" {}
//
//resource "aws_efs_mount_target" "alpha" {
//  file_system_id  = aws_efs_file_system.shared.id
//  subnet_id       = module.vpc.intra_subnets[0]
//  security_groups = [module.vpc.default_security_group_id]
//}
//
//resource "aws_efs_access_point" "lambda" {
//  file_system_id = aws_efs_file_system.shared.id
//
//  posix_user {
//    gid = 1000
//    uid = 1000
//  }
//
//  root_directory {
//    path = "/lambda"
//    creation_info {
//      owner_gid   = 1000
//      owner_uid   = 1000
//      permissions = "0777"
//    }
//  }
//}