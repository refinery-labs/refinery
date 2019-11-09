#!/bin/bash
echo "Building Go 1.12 Refinery custom runtime layer package..."
rm -rf ./layer-contents/*

# Copy Golang into the custom-runtime layer
mkdir ./layer-contents/go

cp -R ./go/bin ./layer-contents/go/bin
cp -R ./go/pkg ./layer-contents/go/pkg
cp -R ./go/src ./layer-contents/go/src

cp runtime.sh ./layer-contents/runtime
cp -r ../base-src/* ./layer-contents/
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf /layer-contents/*
aws s3 cp custom-runtime.zip s3://refinery-lambda-bucket-testing/go-112-custom-runtime.zip
LAYER_VERSION=$(aws lambda publish-layer-version --layer-name refinery-go112-custom-runtime --description "Refinery Go 1.12 custom runtime layer." --content "S3Bucket=refinery-lambda-bucket-testing,S3Key=go-112-custom-runtime.zip" --compatible-runtimes "provided" "python2.7" | jq .Version)
echo "Publishing layer $LAYER_VERSION"
aws lambda add-layer-version-permission \
    --layer-name refinery-go112-custom-runtime \
    --version-number $LAYER_VERSION \
    --statement-id public \
    --action lambda:GetLayerVersion \
    --principal "*" \
    --region us-west-2
