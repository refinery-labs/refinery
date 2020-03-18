FROM ubuntu:18.04

RUN apt-get update && apt-get -y install zip python python-dev python-pip curl wget unzip
RUN apt-get -y install git

RUN mkdir /work/
WORKDIR /work/

COPY ./requirements.txt /work/requirements.txt
RUN pip install -r /work/requirements.txt

COPY ./ /work/

WORKDIR /work/install/
RUN chmod +x /work/install/terraform
RUN /work/install/terraform init
WORKDIR /work/

EXPOSE 7777
EXPOSE 3333

COPY ./server.py /work/

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
