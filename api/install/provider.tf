provider "aws" {
  assume_role {
    role_arn     = var.assume_role_arn
    session_name = var.role_session_name
  }
  access_key = var.access_key
  secret_key = var.secret_key
  region     = var.region
  token      = var.session_token
  version = "~> 2.28.1"
}

data "aws_caller_identity" "current" {
}