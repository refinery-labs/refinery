#!/bin/bash

# Setup environment for build
[ ! -d "./layer-contents" ] && mkdir layer-contents
sudo rm -rf ./layer-contents/*
rm -rf ./layer-contents.zip

# Download and install Git and SSH dependencies using Yumda
sudo docker run --rm -v "$PWD"/layer-contents:/lambda/opt lambci/yumda:1 yum install -y git openssh

sudo chmod -R 0777 ./layer-contents/*

# Copy Golang into the directory
cp -R go ./layer-contents/bin/

# Zip up the layer
cd layer-contents
zip -yr ../layer-contents .
cd ..

if [ -n "$DEVELOPMENT_REFINERY_BUILD" ]
then
    # For development, package up the zip and ship it.
    aws s3 cp layer-contents.zip s3://refinery-lambda-bucket-testing/go-git-ssh-layer.zip
    LAYER_VERSION=$(aws lambda publish-layer-version --layer-name go-git-ssh-layer --description "Refinery Go, Git, and SSH lambda layer." --content "S3Bucket=refinery-lambda-bucket-testing,S3Key=go-git-ssh-layer.zip" --compatible-runtimes "provided" "python2.7" | jq .Version)
    echo "Publishing layer $LAYER_VERSION"
    aws lambda add-layer-version-permission \
        --layer-name go-git-ssh-layer \
        --version-number $LAYER_VERSION \
        --statement-id public \
        --action lambda:GetLayerVersion \
        --principal "*" \
        --region us-west-2
fi
