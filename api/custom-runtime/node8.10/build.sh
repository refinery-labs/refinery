#!/bin/bash
echo "Building Node 8.10 Refinery custom runtime layer package..."
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cd ./layer-contents/
zip -r custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf /layer-contents/*
#aws s3 cp custom-runtime.zip s3://refinery-custom-runtime-layers-packages-testing/node-810-custom-runtime.zip
#aws lambda publish-layer-version --layer-name refinery-node810-custom-runtime --description "Refinery Node 8.10 custom runtime layer." --content "S3Bucket=refinery-custom-runtime-layers-packages-testing,S3Key=node-810-custom-runtime.zip" --compatible-runtimes "provided" "python2.7"
