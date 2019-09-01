#!/bin/bash
echo "Building Ruby 2.6.4 Refinery custom runtime layer package..."
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cp -r ./ruby/ ./layer-contents/
cp -r ./lib/ ./layer-contents/
cp runtime ./layer-contents/
cd ./layer-contents/
zip -r custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf ./layer-contents/*
aws s3 cp custom-runtime.zip s3://lambdapackagetestingbucket/ruby-2.6.4-custom-runtime.zip
aws lambda publish-layer-version --layer-name refinery-ruby264-custom-runtime --description "Refinery Ruby 2.6.4 custom runtime layer." --content "S3Bucket=lambdapackagetestingbucket,S3Key=ruby-2.6.4-custom-runtime.zip" --compatible-runtimes "provided"