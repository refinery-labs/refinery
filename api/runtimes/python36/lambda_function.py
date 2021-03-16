import json
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, root)

from refinery_main import main


def lambda_handler(event, context):
    block_input = event.get("block_input", {})
    backpack = event.get("backpack", {})

    result = main(block_input, backpack)

    response = {
        "result": result,
        "backpack": backpack
    }
    return json.dumps(response)
