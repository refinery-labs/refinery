import traceback
import json
import sys

if sys.path[0] != '':
    sys.path.insert(0, '')

OUTPUT_TAG = "REFINERY_OUTPUT_CUSTOM_RUNTIME"

def format_output(data):
    return f"<{OUTPUT_TAG}>{data}</{OUTPUT_TAG}>"

def get_return_data(result, backpack, error):
    return json.dumps({
        "result": result,
        "backpack": backpack,
        "error": error
    })

def print_return_data(result, backpack, error=None):
    serialized_data = get_return_data(result, backpack, error)
    sys.stdout.write(format_output(serialized_data))
    sys.stdout.flush()

def _init():
    raw_input_data = sys.stdin.read()
    input_data = json.loads(raw_input_data)
    block_input = input_data["block_input"]
    backpack = input_data["backpack"]
    import_path = input_data["import_path"]
    function_name = input_data["function_name"]

    try:
        imported_file = __import__(import_path)
        func = getattr(imported_file, function_name)

        result = func(block_input, backpack)

        print_return_data(result, backpack)
    except:
        print_return_data(None, backpack, traceback.format_exc())
        exit(-1)

    exit(0)

_init()
