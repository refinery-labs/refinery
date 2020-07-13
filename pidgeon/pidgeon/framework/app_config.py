import copy
import os
from six import string_types
from pidgeon.framework.constants import CONFIG_DIR

import yaml


class AppConfig:
    """
    This class holds configuration information for the application to use at runtime.
    Configuration files are stored on disk as YAML files.
    Each configuration file is read and merged in layers -- starting from the `common.yaml` file.
    For the given environment type the configuration file is read as `{ENV}.yaml` and then merged with `common.yaml`.
    The ENV variable is specified via an argument (takes precedence) or setting the `REFINERY_ENV` environment variable.
    Any duplicate values are merged automatically and recursively (if they are a dictionary).
    """

    def __init__(self, environment_type, config_dir=CONFIG_DIR, set_env_vars=True, overrides=None):
        if not isinstance(environment_type, string_types):
            raise InvalidEnvironmentError("Invalid Environment for config loader: " + repr(environment_type))

        self._config_dir = str(config_dir)

        common_config = self._load_named_config("common")
        env_config = self._load_named_config(environment_type)

        self._config = self._merge_configs(common_config, env_config)

        # Grabs and sets the environment variables on the config
        if set_env_vars:
            self._config = self._merge_configs(self._config, dict(os.environ))

        # Add overrides, if specified
        if overrides is not None:
            self._config = self._merge_configs(self._config, overrides)

    def get(self, key):
        """
        Retrieves a key from the configuration file.
        Will throw an exception if the given key does not exist.
        :param key: String to read from the configuration dictionary.
        :return: Value associated with the given key.
        """
        return self._config[key]

    def get_if_exists(self, key):
        """
        Retrieves a key from the configuration file if it exists.
        If it does not exist, None will be returned.
        :param key: String to read from the configuration dictionary.
        :return: Value associated with the given key or None.
        """
        return self._config.get(key)

    def _load_named_config(self, file_name):

        with open(self._config_dir + "/" + file_name + ".yaml", "r") as file_contents:
            return yaml.safe_load(file_contents)["config"]

    @staticmethod
    def _merge_configs(a, b):
        """
        Merges two configurations together. Will attempt to merge duplicate types for lists and dicts.
        For dicts, they are merged recursively (by calling this function again with the dicts).
        Where any duplicate keys of different types exist, the second config will overwrite the value of the first.
        :param a: Base dict to merge
        :param b: Second dict to merge -- any values here will be merged onto the first dict or overwrite the first.
        :return: A new dict with values merged together.
        """
        if a is None:
            return b.copy()

        if b is None:
            return a.copy()

        c = dict()

        all_keys = set(list(a.keys()) + list(b.keys()))

        for key in all_keys:
            c[key] = AppConfig._merge_key(a, b, key)

        return c

    @staticmethod
    def _merge_key(a, b, key):
        """
        Merges individual keys of a dict.
        :param a: Base dict to read key from.
        :param b: Secondary dict to read key from.
        :param key: The string (key) to read from the parent dicts and to merge.
        :return: The new merged value. This will be the value that lives at `input_dict[ key ]`.
        """

        # Key doesn't exist
        if key not in a and key not in b:
            return None

        # Key only in 1st dict
        if key in a and key not in b:
            return copy.deepcopy(a[key])

        # Key only in 2nd dict
        if key not in a and key in b:
            return copy.deepcopy(b[key])

        # Make copies for this function to use
        a_copy = copy.deepcopy(a[key])
        b_copy = copy.deepcopy(b[key])

        # Merge arrays
        if isinstance(a[key], list) and isinstance(b[key], list):
            return a_copy + b_copy

        # Merge dictionaries recursively
        if isinstance(a[key], dict) and isinstance(b[key], dict):
            return AppConfig._merge_configs(a[key], b[key])

        # Otherwise we'll just assume this is a basic type and return B's value
        return b_copy


class InvalidEnvironmentError(Exception):
    pass
