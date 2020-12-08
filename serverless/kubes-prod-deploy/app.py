import os
import base64
import json
import boto3
from botocore.exceptions import ClientError


def get_secret_string(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            return get_secret_value_response['SecretString']
        return base64.b64decode(get_secret_value_response)


def handler(event, context):
    print(event)
    print("Lambda function ARN:", context.invoked_function_arn)
    print("CloudWatch log stream name:", context.log_stream_name)
    print("CloudWatch log group name:",  context.log_group_name)
    print("Lambda Request ID:", context.aws_request_id)

    os.system('rm -rf /tmp/*')

    secret_name = "refinery-secrets-kubes-prod"
    region_name = os.environ["AWS_DEFAULT_REGION"]
    branch_name = os.environ["REFINERY_BRANCH_NAME"]

    secret_string = get_secret_string(secret_name, region_name)
    secrets = json.loads(secret_string)

    with open('id_rsa', 'wb') as f:
        id_rsa_content = base64.b64decode(secrets['DEPLOY_SSH_KEY'])
        f.write(id_rsa_content)

    os.system('chmod 400 id_rsa')

    os.system(f'git clone -b {branch_name} --depth 1 git@github.com:refinery-labs/refinery.git /tmp/refinery')

    os.system('cd /tmp/refinery/helm/refinery')

    secrets_template = ''
    with open('secrets.example.yaml', 'r') as f:
        secrets_template = f.read()

    with open('secrets.yaml', 'w') as f:
        secrets_template.format(**secrets)

    repo_to_service = {
        'refinery-api-server-kubes': 'apiServer',
        'refinery-nginx-server-kubes': 'frontEnd',
        'workflow-manager': 'workflowManager',
        'workflow-manager-worker': 'workflowManagerWorker'
    }

    repo_name = event['details']['repository-name']
    image_tag = event['details']['image-tag']

    service_name = repo_to_service.get(repo_name)
    if service_name is None:
        print(f"[error] Unable to get service for repo: {repo_name}")
        return ''

    os.system('helm dependencies update')
    os.system(f"""
    helm upgrade \
        --kubeconfig ~/.kube/config \
        --namespace $EKS_CLUSTER_NAME \
        -f ./values.prod.yaml \
        -f ./secrets.yaml \
        --set repositoryURI=$REPOSITORY_URI \
        --set {service_name}.container.tag={image_tag} \
        refinery .
    """)
