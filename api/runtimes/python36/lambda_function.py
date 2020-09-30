from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from refinery_main import main


def lambda_handler(event, context):
    block_input = event.get("block input", {})
    backpack = event.get("backpack", {})
    out = StringIO()
    err = StringIO()

    with redirect_stderr(err):
        with redirect_stdout(out):
            result = main(block_input, backpack)

    return {
        "stdout": out.getvalue(),
        "stderr": err.getvalue(),
        "result": result
    }
