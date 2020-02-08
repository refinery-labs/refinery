#!/bin/bash
echo "Building Python 2.7 Refinery custom runtime layer package..."
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cp runtime ./layer-contents/ 
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf ./layer-contents/*
aws s3 cp custom-runtime.zip s3://refinery-lambda-build-packages-pzu0zgo8rgjueseexgrkhdvgwmhnjbtn/python-2.7-custom-runtime.zip
aws lambda publish-layer-version --layer-name refinery-python27-custom-runtime --description "Refinery Python 2.7 custom runtime layer." --content "S3Bucket=refinery-lambda-build-packages-pzu0zgo8rgjueseexgrkhdvgwmhnjbtn,S3Key=python-2.7-custom-runtime.zip" --compatible-runtimes "provided"
