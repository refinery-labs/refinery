#!/bin/bash
docker build -f docker/Dockerfile.runtime . -t refinery-container-runtime
docker tag refinery-container-runtime public.ecr.aws/d7v1k2o3/refinery-container-runtime
aws ecr-public get-login-password --profile refinery-prod --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/d7v1k2o3
docker push public.ecr.aws/d7v1k2o3/refinery-container-runtime
