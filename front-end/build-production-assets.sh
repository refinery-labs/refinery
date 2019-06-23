#!/bin/bash

# Create the folder where the output files will go
mkdir front-end-dist

# Build the front-end assets
docker build -t front-end-image .

# Run the container with a specific npm command and mount our output volume
docker run \
  -e AWS_DEFAULT_REGION \
  -e AWS_CONTAINER_CREDENTIALS_RELATIVE_URI \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -v "$(pwd)"/front-end-dist:/work/output \
  -t front-end-image build-and-copy
