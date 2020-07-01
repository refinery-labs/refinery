#!/bin/bash
rm -rf base-src
virtualenv -p `which python2.7` env
source env/bin/activate
pip install -r requirements.txt
python setup.py bdist_wheel
unzip dist/custom_runtime-0.0.1-py2-none-any.whl -d dist
cp -r env/lib/python2.7/site-packages base-src
cp -r dist/custom_runtime dist/custom_runtime-0.0.1.dist-info base-src
cp bootstrap base-src
deactivate
rm -rf env dist build custom_runtime.egg-info
rm -rf base-src/pip
find base-src -name "*.pyc" | xargs rm
