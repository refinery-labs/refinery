FROM ubuntu:16.04

RUN apt-get update && apt-get -y install zip nginx python python-dev python-pip curl

RUN mkdir /work/

# For dev, uncomment when prod
#COPY ./gui/ /work/gui/
#COPY ./api/ /work/api/

WORKDIR /work/api/
COPY ./api/requirements.txt /work/requirements.txt
RUN pip install -r /work/requirements.txt

COPY ./nginx-config /etc/nginx/sites-enabled/default

COPY ./docker-entrypoint.sh /work/

EXPOSE 1234

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
