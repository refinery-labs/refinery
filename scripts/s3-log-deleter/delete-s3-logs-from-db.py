#!/bin/python

import sqlite3
from typing import AnyStr, List, Tuple, Dict, Optional

import boto3


def chunker(seq: List, size: int):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def create_s3_client(profile: AnyStr):
    session = boto3.Session(profile_name=profile)

    return session.client('s3')


def delete_s3_files(client, bucket: AnyStr, paths: List[AnyStr]):
    """
    Iterates over the logs in chunks of 1000, as required by the AWS S3 client.
    :param client: S3 client instance
    :param bucket: Name of bucket to delete from
    :param paths: List of logs, of any size
    :return: True if successful, False if any errors
    """
    for chunk in chunker(paths, 1000):
        if not delete_s3_files_chunk(client, bucket, chunk):
            return False

    return True


def delete_s3_files_chunk(client, bucket: AnyStr, paths: List[AnyStr]):

    objects_to_delete = []

    for path in paths:
        objects_to_delete.append({
            "Key": path
        })

    delete_args = {
        "Objects": objects_to_delete,
        "Quiet": True
    }

    response = client.delete_objects(
        Bucket=bucket,
        Delete=delete_args
    )

    if "Errors" in response and len(response["Errors"]) > 0:
        print("S3 Error: " + repr(response))
        return False

    return True


def get_all_paths(connection, table_name: AnyStr):

    row_tuples = run_select_query(connection, 'SELECT "$path" FROM "%s"' % scrub(table_name))

    return [row[0] for row in row_tuples]


def run_select_query(connection, query: AnyStr, values: Optional[Dict[AnyStr, AnyStr]] = None):
    c = connection.cursor()

    output = []

    if values is not None:
        for row in c.execute(query, values):
            output.append(row)
    else:
        for row in c.execute(query):
            output.append(row)

    return output


def scrub(table_name):
    """
    Garbage sanitize function that whitelists only the characters needed for this limited use case
    :param table_name: Name of table to sanitize against SQL injection
    :return: Sanitized table name
    """
    return str(''.join(chr for chr in table_name if (chr.isalnum() or chr == '-')))


def parse_args(argv):
    run_config = dict()
    run_config["db"] = "s3-log-deleter.db"

    opts, args = getopt.getopt(argv, None, ['db=', 'table_name=', 'bucket_name=', 'credentials_profile='])

    for opt in opts:
        if opt[0].startswith('--'):
            run_config[opt[0][2:]] = opt[1]


    assert ("db" in run_config), "Script requires db"
    assert ("table_name" in run_config), "Script requires table_name"
    assert ("bucket_name" in run_config), "Script requires bucket_name"
    assert ("credentials_profile" in run_config), "Script requires AWS credentials_profile"

    return run_config


if __name__ == "__main__":
    """
    May be invoked from the CLI using the following example:
    ./delete-s3-logs-from-db.py --db asdf --table_name asdf2 --bucket_name 33 --credentials_profile asdf5
    """
    import getopt
    import sys

    argv = sys.argv[1:]

    config = parse_args(argv)

    connection = sqlite3.connect(config['db'])

    # TODO: Replace this argument with the name of then table read from cli args
    paths = get_all_paths(connection, config['table_name'])

    print("Deleting %s logs from bucket" % len(paths))

    s3_client = create_s3_client(config['credentials_profile'])

    if not delete_s3_files(s3_client, config['bucket_name'], paths):
        raise Exception("Unable to delete all paths")

    print("Successfully deleted %s logs from bucket" % len(paths))

