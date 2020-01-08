# The image for the Refinery builder agent is hosted on Dockerhub
# Hosting it publically on ECS was expensive and pointless.
docker build -t refinery-builders .
docker tag refinery-builders:latest refinerylabs/refinery-builders:latest
docker push refinerylabs/refinery-builders:latest
