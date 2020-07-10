"""
Configuration management.

Environment must be set before use.

Call .get() to obtain configuration variable. If the variable does not exist
in the set environment, then
"""


MODULE_NAME = "artemis"
CONFIG_MODULE_NAME = "configs"
CONFIG_KEY = "config_class"
ENV = {}


class EMPTY:

    """
    Signifies that a default value was not set. Should trigger an error if
    default is set to EMPTY and an attribute does not exist.
    """

    pass


class Config:

    """
    Configuration management entity.

    Args:
        name (str): Name of config environment.
        fallback (bool): Indicate if configuration should fallback to base.
    """

    no_config_err = "No such config variable {}"

    def __init__(self, name, fallback):
        from importlib import import_module
        from os import listdir
        from os.path import dirname, join

        self.config_path = join(dirname(__file__), CONFIG_MODULE_NAME)
        self.name = name
        self.fallback = fallback

        # List of config modules available
        self.config_modules = set([
            i.strip(".py")
            for i in listdir(self.config_path)
            if ".py" in i and i != "__init__.py"
        ])

        if name not in self.config_modules:
            err = "Config environment {} does not exist".format(name)

            raise AttributeError(err)

        if self.fallback:
            # Fallback configuration module.
            self.base = import_module(
                "{}.{}.base".format(MODULE_NAME, CONFIG_MODULE_NAME)
            )

        # Desired configuration module.
        self.module = import_module(
            "{}.{}.{}".format(MODULE_NAME, CONFIG_MODULE_NAME, self.name)
        )

    def get(self, name, default):
        """Get config value"""
        value = getattr(self.module, name, default)

        if value != EMPTY:
            return value
        elif value == EMPTY and not self.fallback:
            raise AttributeError(self.no_config_err.format(name))
        elif value == EMPTY and self.fallback:
            value = getattr(self.base, name, default)

            if value == EMPTY:
                raise AttributeError(self.no_config_err.format(name))

            return value


class ConfigMeta(type):
    def __getattr__(self, name):
        return get(name)


class config(metaclass=ConfigMeta):
    @classmethod
    def getenv(cls):
        return getenv()


def getenv():
    return ENV[CONFIG_KEY].name


def setenv(name, fallback=True):
    """Set configuration environment."""
    if CONFIG_KEY in ENV:
        raise AttributeError("Config environment already set.")

    config_class = Config(name, fallback)

    ENV[CONFIG_KEY] = config_class


def get(name):
    """Get configuration variable."""
    if not ENV:
        setenv('base')

    config_class = ENV.get(CONFIG_KEY, None)

    return config_class.get(name, EMPTY)
