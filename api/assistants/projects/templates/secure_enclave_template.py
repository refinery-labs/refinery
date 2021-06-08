import json

from assistants.projects.templates.project_template import ProjectTemplate, ProjectSecret, ProjectResource, \
    ProjectSecrets
from pyconstants.project_constants import DOCKER_RUNTIME_PRETTY_NAME


class SecureEnclaveTemplateResources:
    ciphertext_bucket = ProjectResource("ciphertext-bucket")
    secure_frame_backend = ProjectResource("secure-frame-backend")
    secure_frame_bucket = ProjectResource("secure-frame-bucket")
    metadata_kv_table = ProjectResource("tokenizer-metadata")
    keys_kv_table = ProjectResource("tokenizer-keys")
    sessions_kv_table = ProjectResource("tokenizer-sessions")
    secure_frame_api_path = ProjectResource("/frame")
    tokenize_api_path = ProjectResource("/tokenize")
    detokenize_api_path = ProjectResource("/detokenize")
    session_verify_api_path = ProjectResource("/session/verify")
    session_ensure_api_path = ProjectResource("/session/ensure")
    metadata_set_api_path = ProjectResource("/metadata/set")
    metadata_get_api_path = ProjectResource("/metadata/get")


class SecureEnclaveTemplateSecrets(ProjectSecrets):
    secure_frame_keyset = ProjectSecret("secure-frame-keyset", "hybrid")
    secure_frame_signing_keys = ProjectSecret("secure-frame-signing-keys", "asymmetric")


class SecureEnclaveTemplate(ProjectTemplate):
    TEMPLATE_RESOURCES = SecureEnclaveTemplateResources
    TEMPLATE_SECRETS = SecureEnclaveTemplateSecrets

    def build(self, inputs):
        ciphertext_bucket = self.create_ciphertext_bucket()
        secure_frame_bucket = self.create_secure_frame_bucket()

        metadata_kv_table = self.create_key_value_table(self.TEMPLATE_RESOURCES.metadata_kv_table)
        keys_kv_table = self.create_key_value_table(self.TEMPLATE_RESOURCES.keys_kv_table)
        sessions_kv_table = self.create_key_value_table(self.TEMPLATE_RESOURCES.sessions_kv_table)

        secure_frame_backend = self.create_secure_frame_backend(ciphertext_bucket["bucket_name"])

        diagram_data = {
            "secrets": self.serialize_secrets(),
            "workflow_states": [
                ciphertext_bucket,
                # TODO (cthompson) for the ciphertext bucket, enable versioning and configure lifecycle rules with AWS::S3::Bucket Rule NoncurrentVersionTransition
                secure_frame_backend,
                secure_frame_bucket,
                metadata_kv_table,
                keys_kv_table,
                sessions_kv_table,
                *[
                    self.create_api_endpoint(*api_resource_params, self.TEMPLATE_RESOURCES.secure_frame_backend)
                    for api_resource_params in [
                        (self.TEMPLATE_RESOURCES.secure_frame_api_path, "GET"),
                        (self.TEMPLATE_RESOURCES.tokenize_api_path, "POST"),
                        (self.TEMPLATE_RESOURCES.detokenize_api_path, "POST"),
                        (self.TEMPLATE_RESOURCES.session_verify_api_path, "POST"),
                        (self.TEMPLATE_RESOURCES.session_ensure_api_path, "POST"),
                        (self.TEMPLATE_RESOURCES.metadata_set_api_path, "POST"),
                        (self.TEMPLATE_RESOURCES.metadata_get_api_path, "POST")
                    ]
                ],
            ],
            "workflow_relationships": [],
        }
        return diagram_data

    def tokenizer_policies(self):
        # TODO (cthompson) limit these permissions to just the dynamodb tables and s3 buckets that the lambda uses
        return [{
            "action": [
                "dynamodb:*",
                "s3:*"
            ],
            "resource": '*'
        }]

    def secure_frame_policies(self):
        tokenizer_policies = self.tokenizer_policies()
        return [
            *tokenizer_policies,
            {
                "action": [
                    "secretsmanager:*",
                ],
                "resource": '*'
            }
        ]

    def tokenizer_env_vars(self, ciphertext_bucket, use_jwt_auth=True):
        jwt_private_key_env_var = {}
        if use_jwt_auth:
            jwt_signing_keys_arn = self.TEMPLATE_SECRETS.secure_frame_signing_keys.arn
            jwt_private_key_env_var = {"SIGNING_KEYS_ARN": jwt_signing_keys_arn}

        return {
            "LAMBDA_CALLER": "API_GATEWAY",
            "DOCUMENT_VAULT_S3_BUCKET": ciphertext_bucket,
            **jwt_private_key_env_var
        }

    def create_secure_frame_backend(self, ciphertext_bucket_name):
        # TODO this should not be hard coded here, this ideally should be pulled down dynamically inside
        # the secure frame service if that is supported by the openid auth provider
        auth_provider_public_key = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUFsbjFtVm1vSVJqREdRNHBWY2NzQgo1eUozREZJdFVlOXpMRlU0bmFxc2ZGWUp5d0t5QXNINDh3VUhrQlgwWlJ1cm5FRW9tdHhtajNGOUIrZForVUxGCmUzSm5GcldEak43WE9GeHluM0pmWGp3VmZFZkEyRnhZTEx4Z3daeGZGRnZjV0NoMmpvZEFsUE82NkxCdGVTYkEKcGNsdlNucDc0WkhDU0VyOERGQ3Y3TFU1MGQwb0greGhyTjFoNllMdkxHTGJkRkZacHZ3MWRyQmFWN0tOdk9SOAp0NHFNYmNUZERqNWZXUEJtS1o1YVk0ZTNwS1g4OVNCYzhDdFlmQmNmU003dTRreGRHSXQrbmthMjlTeUtTWUJ4CldMYzRiRk1LT3dXancwZ2UvTGJud3RGRWxRK1J5VG83QVNqK29OSzNDUk9STkFheFkrT3o4cUwwMGN1d3VvM2EKUFFJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="

        tokenizer_env_vars = self.tokenizer_env_vars(ciphertext_bucket_name)
        policies = self.secure_frame_policies()
        keyset_arn = self.TEMPLATE_SECRETS.secure_frame_keyset.arn
        return {
            **self.create_lambda_base(
                self.TEMPLATE_RESOURCES.secure_frame_backend, DOCKER_RUNTIME_PRETTY_NAME, policies),
            "container": {
                "uri": "public.ecr.aws/d7v1k2o3/secure-frame-backend"
            },
            "environment_variables": {
                **tokenizer_env_vars,
                # TODO (cthompson) this should not be hardcoded, we should be able to build lunasec-node-monorepo/service/src/browser
                # and then push the static assets to the secure frame bucket we create in this deployment
                "CDN_CONFIG": json.dumps({
                    "host": "d1bxkirkuveaaf.cloudfront.net",
                    "main_script": "main.dc2fde6210856cfb0d6c.js",
                    "main_style": "main.css"
                }),
                "SECURE_FRAME_KEYSET_ARN": keyset_arn,
                "AUTH_PROVIDER_PUBLIC_KEY": auth_provider_public_key,
                "AUTH_CALLBACK_URL": "http://sound:3000",
            }
        }

    def get_ciphertext_bucket_name(self, ciphertext_bucket_name, ciphertext_bucket_id):
        return ciphertext_bucket_name + ciphertext_bucket_id

    def create_ciphertext_bucket(self):
        ciphertext_bucket = self.TEMPLATE_RESOURCES.ciphertext_bucket
        return {
            "id": ciphertext_bucket.id,
            "name": ciphertext_bucket.name,
            "type": "bucket",
            "bucket_name": self.get_ciphertext_bucket_name(ciphertext_bucket.name, ciphertext_bucket.id),
            "cors": True
        }

    def create_secure_frame_bucket(self):
        secure_frame_bucket = self.TEMPLATE_RESOURCES.secure_frame_bucket
        bucket_name = secure_frame_bucket.name + secure_frame_bucket.id
        return {
            "id": secure_frame_bucket.id,
            "name": secure_frame_bucket.name,
            "type": "bucket",
            "bucket_name": bucket_name,
            "publish": True
        }

    def create_key_value_table(self, table_project_resource: ProjectResource):
        return {
            "id": table_project_resource.id,
            "name": table_project_resource.name,
            "type": "key_value_table"
        }
