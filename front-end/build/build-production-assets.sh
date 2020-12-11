#!/bin/bash

# Create the folder where the output files will go
mkdir front-end-dist

# Build the front-end assets
docker build -t front-end-image .

# Run the container with a specific npm command and mount our output volume
docker run \
  -e NODE_ENV \
  -e AWS_DEFAULT_REGION \
  -e AWS_CONTAINER_CREDENTIALS_RELATIVE_URI \
  -e CLOUDFRONT_URL \
  -e S3_DEPLOY_REGION \
  -e S3_DEPLOY_BUCKET \
  -e S3_DEPLOY_PATH \
  -e VUE_APP_API_HOST \
  -e VUE_APP_STRIPE_PUBLISHABLE_KEY \
  -v "$(pwd)"/front-end-dist:/work/output \
  -t front-end-image build-and-copy
