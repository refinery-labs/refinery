FROM golang AS golang-functions

RUN apt update
RUN apt install -y zip

COPY install/functions/docker-container-modifier/ /build/docker-container-modifier/

WORKDIR /build/docker-container-modifier
RUN make package


FROM node AS node-functions

RUN apt update
RUN apt install -y zip

COPY install/functions/serverless-framework-builder/ /build/serverless-framework-builder/

WORKDIR /build/serverless-framework-builder
RUN npm i --only=dev
RUN npm run package


FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get -y install zip python3 python3-dev python3-pip curl wget libssl-dev unzip libpq-dev pkg-config libcairo2-dev libgirepository1.0-dev git nodejs npm

RUN mkdir /work/
WORKDIR /work/

COPY ./requirements.txt /work/requirements.txt
RUN pip3 install -r /work/requirements.txt

RUN npm install -g serverless

COPY . /work/

WORKDIR /work/install/
RUN chmod +x /work/install/terraform
RUN /work/install/terraform init
COPY --from=golang-functions /build/docker-container-modifier/package.zip ./functions/docker-container-modifier/package.zip
COPY --from=node-functions /build/serverless-framework-builder/package.zip ./functions/serverless-framework-builder/package.zip
WORKDIR /work/

EXPOSE 7777
EXPOSE 3333

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
