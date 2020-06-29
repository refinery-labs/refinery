import os

from setuptools import setup


NAME = 'custom-runtime'
VERSION = '0.0.1'


def get_requirements(name):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), name)

    if not os.path.exists(path):
        err = 'Requirements file "{}" does not exist'

        raise FileNotFoundError(err.format(path))

    return open(path).read().split()


setup(
    name=NAME,
    version=VERSION,
    author="Refinery Labs",
    description="Custom runtime for refinery",
    license="Proprietary",
    packages=["custom_runtime"],
    install_requires=get_requirements('requirements.txt'),
)
