import pinject


class AppConfigHolder:
    app_config = None

    @pinject.copy_args_to_public_fields
    def __init__(self, app_config):
        pass
