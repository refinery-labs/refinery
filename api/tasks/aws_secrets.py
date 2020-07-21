from json import loads


def get_secret(aws_client_factory, credentials, secret_id):
    client = aws_client_factory.get_aws_client(
        "secretsmanager",
        credentials
    )

    response = client.get_secret_value(SecretID=secret_id)

    if 'SecretString' not in response:
        raise ValueError(f"No such secret {secret_id}")

    return loads(response['SecretString'])
