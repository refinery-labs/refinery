import shlex
import sys

from os import _exit
from os.path import join, exists
from setuptools.command.test import test
from setuptools import setup


NAME = 'pidgeon'
VERSION = '0.0.1'


# Suppress unraisable errors if version is python 3.8 or greater
if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
    sys.unraisablehook = lambda i: ()


class RunTests(test):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        test.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from coverage import Coverage
        from pidgeon.framework.constants import PROJECT_ROOT
        from pytest import main

        cov = Coverage(config_file=join(PROJECT_ROOT, '.coveagerc'))
        cov.start()

        exit_code = main(shlex.split(self.pytest_args or ""))

        cov.stop()
        cov.xml_report()

        _exit(exit_code)


def get_requirements(name):
    from pidgeon.framework.constants import PROJECT_ROOT
    path = join(PROJECT_ROOT, name)

    if not exists(path):
        raise FileNotFoundError(f"Requirements file {name} does not exist")

    return open(path).read().split()


setup(
    name=NAME,
    version=VERSION,
    author="Refinery Labs Inc.",
    description="Block result storage api",
    license="Proprietary",
    packages=["pidgeon"],
    cmdclass={
        'test': RunTests
    },
    install_requires=get_requirements('requirements.txt'),
    tests_require=get_requirements('requirements-test.txt')
)
