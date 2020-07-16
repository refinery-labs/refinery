from os import environ
from os.path import abspath, dirname, realpath, join


PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
CONFIG_DIR = join(PROJECT_ROOT, "config")
ENCODING = "UTF-8"
ENV = environ.get("REFINERY_ENV", "production")
