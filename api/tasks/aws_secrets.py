from json import loads


def get_secret(client, secret_id, key=None):
    response = client.get_secret_value(SecretID=secret_id)

    if 'SecretString' not in response:
        raise ValueError(f"No such secret {secret_id}")

    response = loads(response['SecretString'])

    if key:
        return response[key]

    return response
