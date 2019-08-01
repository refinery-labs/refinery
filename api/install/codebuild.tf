/*
	Create the CodeBuild project which Refinery uses to build
	Lambda packages with all of the dependencies.
*/
resource "aws_codebuild_project" "refinery-builds" {
  name          = "refinery-builds"
  description   = "Refinery's build system for Lambda packages."
  build_timeout = "15"
  service_role  = "${aws_iam_role.codebuild-refinery-builds-service-role.arn}"

  artifacts {
    type              = "S3"
    name              = "package.zip"
    namespace_type    = "BUILD_ID"
    location          = "refinery-lambda-build-packages-${var.s3_bucket_suffix}"
    packaging         = "ZIP"
  }

  cache {
    type     = "LOCAL"
    modes    = ["LOCAL_DOCKER_LAYER_CACHE"]
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:2.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true
  }

  source {
    type            = "S3"
    location        = "refinery-lambda-build-packages-${var.s3_bucket_suffix}/nonexistant.zip"
  }

  tags = {
    RefineryResource = "true"
  }
}