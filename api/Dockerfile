FROM ubuntu:18.04

RUN apt-get update && apt-get -y install zip python python-dev python-pip curl

RUN mkdir /work/
WORKDIR /work/

COPY ./requirements.txt /work/requirements.txt
RUN pip install -r /work/requirements.txt

COPY ./__init__.py /work/
COPY ./models/ /work/models/
COPY ./lambda_bases/ /work/lambda_bases/
COPY ./email_templates/ /work/email_templates/
COPY ./custom-runtime/ /work/custom-runtime/
COPY ./docker-entrypoint.sh /work/

EXPOSE 7777

COPY ./server.py /work/

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]