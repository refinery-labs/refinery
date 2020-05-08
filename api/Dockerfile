FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get -y install zip python3 python3-dev python3-pip curl wget libssl-dev unzip libpq-dev pkg-config libcairo2-dev libgirepository1.0-dev

RUN mkdir /work/
WORKDIR /work/

COPY ./requirements.txt /work/requirements.txt
RUN pip3 install -r /work/requirements.txt

COPY ./ /work/

WORKDIR /work/install/
RUN chmod +x /work/install/terraform
RUN /work/install/terraform init
WORKDIR /work/

EXPOSE 7777
EXPOSE 9999
EXPOSE 3333

COPY ./server.py /work/

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
