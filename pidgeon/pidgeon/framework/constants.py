from os.path import abspath, dirname, realpath, join


PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
CONFIG_DIR = join(PROJECT_ROOT, "pidgeon", "config")
