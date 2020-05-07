import os

import pinject

from config.app_config import AppConfig
from config.app_init_config import app_init_config


def load_app_config(app_env=None, overrides=None):
    if app_env is None:
        if "REFINERY_ENV" not in os.environ:
            app_env = "production"
        else:
            app_env = os.environ["REFINERY_ENV"]

    # In production just read the config vars from the env
    set_env_vars = app_env == "production"

    app_config = AppConfig(app_env, overrides=overrides, set_env_vars=set_env_vars)

    # Add dynamic configuration values to app config
    app_init_config(app_config)

    return app_config


class ConfigBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        pass

    @pinject.provides('app_config')
    def provide_app_config(self):
        return load_app_config()
