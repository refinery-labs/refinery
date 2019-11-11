#!/bin/bash

# Setup environment for build
[ ! -d "./layer-contents" ] && mkdir layer-contents
sudo rm -rf ./layer-contents/*
rm -rf ./layer-contents.zip

# Download and install Git and SSH dependencies using Yumda
sudo docker run --rm -v "$PWD"/layer-contents:/lambda/opt lambci/yumda:1 yum install -y git openssh

# Set permissions to be permissive enough to copy the Go binaries in
sudo chmod -R 0777 ./layer-contents/*

# Download Golang package if we don't have it
[ ! -f "./go1.12.13.linux-amd64.tar.gz" ] && wget https://dl.google.com/go/go1.12.13.linux-amd64.tar.gz

# Extract it
tar -xvf go1.12.13.linux-amd64.tar.gz

# Remove extra bloat that isn't needed for the layer
rm -rf go/test
rm -rf go/doc
rm -rf go/misc
rm -rf go/api
rm -rf go/lib.time
rm -rf go/bin/godoc
# Bunch of binaries that don't seem to be needed
rm -rf go/pkg/tool/linux_amd64/cover
rm -rf go/pkg/tool/linux_amd64/dist
rm -rf go/pkg/tool/linux_amd64/doc
rm -rf go/pkg/tool/linux_amd64/nm
rm -rf go/pkg/tool/linux_amd64/pprof
rm -rf go/pkg/tool/linux_amd64/test2json
rm -rf go/pkg/tool/linux_amd64/trace
rm -rf go/pkg/tool/linux_amd64/vet
# Huge amount of stuff in here
rm -rf go/pkg/linux*

# Further shrink everything
strip --strip-all ./go/bin/*
strip --strip-all ./go/pkg/tool/linux_amd64/*

# Set permissions for Golang
sudo chmod -R 0777 ./go/*

# Copy Golang into the layer
mv ./go ./layer-contents/bin

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
