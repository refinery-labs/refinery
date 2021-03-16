import io
import os
import sys
import tarfile
import uuid
import json
import string
import random
import struct
import logging
import math
from typing import Literal
from zipfile import ZipInfo

import pinject

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO
)


class UtilsBindingSpec(pinject.BindingSpec):

    def configure(self, bind):
        pass

    @pinject.provides('logger')
    def provider_logger(self):
        return logit


def attempt_json_decode(input_data):
    # Try to parse Lambda input as JSON
    try:
        input_data = json.loads(
            input_data
        )
    except BaseException:
        pass

    return input_data


LogLevelTypes = Literal["info", "warning", "error", "debug"]


def logit(message: str, message_type: LogLevelTypes = "info") -> None:
    # Attempt to parse the message as json
    # If we can then prettify it before printing
    try:
        message = json.dumps(
            message,
            sort_keys=True,
            indent=4,
            separators=(",", ": ")
        )
    except BaseException:
        pass

    logging_func = getattr(
        logging,
        message_type,
        logging.info
    )

    logging_func(message)


def split_list_into_chunks(input_list, chunk_size):
    def split_list(inner_input_list, inner_chunk_size):
        for i in range(0, len(inner_input_list), inner_chunk_size):
            yield inner_input_list[i:i + inner_chunk_size]

    return list(
        split_list(
            input_list,
            chunk_size
        )
    )


def get_random_node_id():
    return "n" + str(uuid.uuid4()).replace("-", "")


# For generating crytographically-secure random strings
def get_urand_password(length):
    symbols = string.ascii_letters + string.digits

    return "".join([
        symbols[math.floor(x * len(symbols) / 256)]
        for x in
        struct.unpack("%dB" % (length,), os.urandom(length))
    ])


def get_random_id(length):
    return "".join(
        random.choice(
            string.ascii_letters + string.digits
        ) for _ in range(length)
    )


def get_random_deploy_id():
    return "_RFN" + get_random_id(6)


def get_safe_workflow_state_name(input_name):
    whitelist = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    input_name = input_name.replace(" ", "_")
    return "".join([c for c in input_name if c in whitelist])[:64]


def log_exception(f):
    def wrapped(*args, **kw):
        try:
            result = f(*args, **kw)
        except Exception as e:
            logging.warning("exception", exc_info=True)
            raise e
        return result
    return wrapped


def print_object_graph(object_graph):
    print(object_graph._obj_provider._binding_mapping._binding_key_to_binding)


def add_file_to_zipfile(handler, file_name, contents):
    # Write buildspec.yml defining the build process
    info = ZipInfo(file_name)
    info.external_attr = 0o777 << 16
    handler.writestr(info, contents)


def add_file_to_tar_file(tar_container, filepath, contents):
    tarinfo = tarfile.TarInfo(filepath)
    tarinfo.size = len(contents)
    tarinfo.mode = 0o755
    tar_container.addfile(tarinfo, io.BytesIO(contents))
