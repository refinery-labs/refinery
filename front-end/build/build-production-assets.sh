#!/bin/bash

# Create the folder where the output files will go
mkdir front-end-dist

# Build the front-end assets
docker build -t front-end-image .

# Run the container with a specific npm command and mount our output volume
docker run \
  -e AWS_DEFAULT_REGION \
  -e AWS_CONTAINER_CREDENTIALS_RELATIVE_URI \
  -e CLOUDFRONT_URL \
  -e S3_DEPLOY_REGION \
  -e S3_DEPLOY_BUCKET \
  -e S3_DEPLOY_PATH \
  -e APP_API_URL \
  -v "$(pwd)"/front-end-dist:/work/output \
  -t front-end-image build-and-copy
