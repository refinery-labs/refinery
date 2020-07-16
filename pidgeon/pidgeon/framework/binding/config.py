from pidgeon.framework.util.config import Config
from pidgeon.framework.constants import ENV
from pinject import BindingSpec, provides


class ConfigBindingSpec(BindingSpec):
    @provides('config')
    def provide_app_config(self):
        return Config(ENV, set_env_vars=ENV == "production")
