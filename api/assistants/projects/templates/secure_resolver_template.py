from uuid import uuid4

from assistants.projects.templates.project_template import ProjectTemplate, ProjectResource


class SecureResolverTemplateInputs:
    container_uri: str = None
    language: str = None
    functions: dict = None


class SecureResolverTemplateResources:
    secure_resolver = ProjectResource("secure-resolver")
    secure_resolver_api_path = ProjectResource("/execute")
    ciphertext_bucket_name = ProjectResource("ciphertext-bucket")


class SecureResolverTemplate(ProjectTemplate):
    TEMPLATE_RESOURCES = SecureResolverTemplateResources

    def build(self, inputs: SecureResolverTemplateInputs):
        # TODO (cthompson) this should be retrieved from "secure_enclave_template", since secure resolver is dependent on that project
        ciphertext_bucket_bucket_name = self.TEMPLATE_RESOURCES.ciphertext_bucket_name

        secure_resolver = self.create_secure_resolver_workflow_state(
            inputs.container_uri,
            inputs.functions,
            inputs.language,
            ciphertext_bucket_bucket_name
        )

        diagram_data = {
            "workflow_states": [
                secure_resolver,
                self.create_api_endpoint(self.TEMPLATE_RESOURCES.secure_resolver_api_path, "POST", secure_resolver),
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

    def tokenizer_env_vars(self, ciphertext_bucket):
        return {
            "DOCUMENT_VAULT_S3_BUCKET": ciphertext_bucket,
        }

    def create_secure_resolver_workflow_state(
            self, container_uri, functions, language, ciphertext_bucket_name
    ):
        tokenizer_env_vars = self.tokenizer_env_vars(ciphertext_bucket_name)
        tokenizer_policies = self.tokenizer_policies()
        return {
            **self.create_lambda_base(
                self.TEMPLATE_RESOURCES.secure_resolver, language, tokenizer_policies),
            "container": {
                "uri": container_uri,
                "functions": functions,
            },
            # TODO how long do we want to wait for this to run?
            "environment_variables": {
                **tokenizer_env_vars
            }
        }
