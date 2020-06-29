#!/bin/bash
virtualenv -p `which python2.7` env
source env/bin/activate
pip install -r requirements.txt
python setup.py bdist_wheel
unzip dist/custom_runtime-0.0.1-py2-none-any.whl -d dist
cp -r env/lib/python2.7/site-packages runtime
cp -r dist/custom_runtime dist/custom_runtime-0.0.1.dist-info runtime
cp bootstrap runtime
deactivate
rm -rf env dist build custom_runtime.egg-info
