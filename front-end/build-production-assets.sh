#!/bin/bash

# Create the folder where the output files will go
mkdir front-end-dist

# Build the front-end assets
docker build -t front-end-image .

# Run the container with a specific npm command and mount our output volume
docker run -v "$(pwd)"/front-end-dist:/work/output -t front-end-image build-and-copy

