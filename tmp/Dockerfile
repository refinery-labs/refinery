FROM ubuntu:16.04

RUN apt-get update && apt-get -y install zip nginx python python-dev python-pip python-virtualenv

RUN mkdir /work/
WORKDIR /work/api/
COPY ./api/requirements.txt /work/requirements.txt
RUN pip install -r /work/requirements.txt

COPY ./nginx-config /etc/nginx/sites-enabled/default

# For dev, uncomment when prod
#COPY ./gui /work/gui/
#COPY ./api /work/api/
COPY ./docker-entrypoint.sh /work/

EXPOSE 1234

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
