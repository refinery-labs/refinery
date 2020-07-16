#!/bin/bash
echo "Building Python 2.7 Refinery custom runtime layer package..."
mkdir -p ./layer-contents
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../../base-src/* ./layer-contents/
cp runtime ./layer-contents/ 
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf ./layer-contents/*
#aws s3 cp custom-runtime.zip s3://refinery-custom-runtime-layers-packages-testing/php-7.3-custom-runtime.zip
#aws lambda publish-layer-version --layer-name refinery-php73-custom-runtime --description "Refinery PHP 7.3 custom runtime layer." --content "S3Bucket=refinery-custom-runtime-layers-packages-testing,S3Key=php-73-custom-runtime.zip" --compatible-runtimes "provided"
