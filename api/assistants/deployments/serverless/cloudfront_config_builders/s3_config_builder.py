from assistants.deployments.serverless.cloudfront_config_builders.aws_config_builder import AwsConfigBuilder


class S3ConfigBuilder(AwsConfigBuilder):

    def build(self, workflow_state):
        bucket_name = workflow_state['bucket_name']
        publish = workflow_state.get('publish')
        cors = workflow_state.get('cors')

        s3_public_properties = {}
        if publish:
            s3_public_properties = {
                "AccessControl": "PublicRead",
                "WebsiteConfiguration": {
                    "IndexDocument": "index.html",
                    "ErrorDocument": "index.html"
                }
            }

        s3_cors = {}
        if cors:
            # TODO (cthompson) make this cors config less permissive
            s3_cors = get_cors_configuration(['*'], ['GET', 'PUT'], ['*'])

        # TODO (cthompson) bucket lifecycle

        bucket_id = self.get_id(bucket_name)
        bucket_resource = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": bucket_id,
                **s3_public_properties,
                **s3_cors
            }
        }

        cloudfront_resource = {}
        if publish is not None and publish:
            cloudfront_resource = build_cloudfront_distribution(bucket_id)

        bucket_policy_resource = build_s3_bucket_policy(bucket_id)

        resources = {
            bucket_id: bucket_resource,
            **bucket_policy_resource,
            **cloudfront_resource
        }
        self.set_resources(resources)

        self.set_outputs({
            id_: {
                "Value": {
                    "Ref": id_
                }
            } for id_ in resources.keys()})


def create_cloudfront_resource(origin_resource, origin):
    return {
        "Type": "AWS::CloudFront::Distribution",
        "Properties": {
            "DistributionConfig": {
                "Origins": [
                    origin_resource
                ],
                "Enabled": "true",
                "DefaultRootObject": "index.html",
                "CustomErrorResponses": [
                    {
                        "ErrorCode": 404,
                        "ResponseCode": 200,
                        "ResponsePagePath": "/index.html"
                    }
                ],
                "DefaultCacheBehavior": {
                    "AllowedMethods": [
                        "HEAD", "DELETE", "POST", "GET", "OPTIONS", "PUT", "PATCH"
                    ],
                    "TargetOriginId": origin,
                    "ForwardedValues": {
                        "QueryString": "false",
                        "Cookies": {
                            "Forward": "none"
                        }
                    },
                    "ViewerProtocolPolicy": "redirect-to-https",
                },
                "ViewerCertificate": {
                    "CloudFrontDefaultCertificate": "true"
                }
            }
        }
    }


def get_cors_configuration(allowed_headers, allowed_methods, allowed_origins):
    return {
        "CorsConfiguration": {
            "CorsRules": [
                {
                    "AllowedHeaders": allowed_headers,
                    "AllowedMethods": allowed_methods,
                    "AllowedOrigins": allowed_origins
                }
            ]
        }
    }


def build_s3_bucket_policy(bucket_id):
    id_ = bucket_id + "Policy"
    policy_statement = {
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": [
            "s3:GetObject"
        ],
        "Resource": f"arn:aws:s3:::{bucket_id}/*"
    }
    bucket_policy_resource = {
        "Type": "AWS::S3::BucketPolicy",
        "Properties": {
            "Bucket": {
                "Ref": bucket_id
            },
            "PolicyDocument": {
                "Statement": [
                    policy_statement
                ]
            }
        }
    }
    return {
        id_: bucket_policy_resource
    }


def build_cloudfront_distribution(bucket_id):
    id_ = bucket_id + "Cloudfront"
    # An identifier for the origin which must be unique within the distribution
    origin = bucket_id + "Origin"

    origin_resource = {
        "DomainName": f"{bucket_id}.s3.amazonaws.com",
        "Id": origin,
        "CustomOriginConfig": {
            "HTTPPort": 80,
            "HTTPSPort": 443,
            "OriginProtocolPolicy": "https-only"
        }
    }

    cloudfront_resource = create_cloudfront_resource(origin_resource, origin)
    return {
        id_: cloudfront_resource
    }

