from refinery_main import main


def lambda_handler(event, context):
    block_input = event.get("block input", {})
    backpack = event.get("backpack", {})

    return main(block_input, backpack)