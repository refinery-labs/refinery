#!/bin/bash
rm -rf ./tmp/
rm elastic-beanstack-package.zip
mkdir tmp/
cp -r ./api/ ./tmp/
cp -r ./gui/ ./tmp/
cp docker-entrypoint.sh ./tmp/
cp Dockerrun.aws.json ./tmp/
cp Dockerfile ./tmp/
cp nginx-config ./tmp/
cd ./tmp/
zip -r elastic-beanstack-package.zip *
cp elastic-beanstack-package.zip ../
cd ../
# rm -rf ./tmp/
