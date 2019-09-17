FROM ubuntu:18.04

RUN apt-get update && apt-get -y install zip python python-dev python-pip curl wget unzip

RUN mkdir /work/
WORKDIR /work/

COPY ./requirements.txt /work/requirements.txt
RUN pip install -r /work/requirements.txt

COPY ./__init__.py /work/
COPY ./ngrok /work/
COPY ./install/ /work/install/
COPY ./controller/ /work/controller/
COPY ./services/ /work/services/
COPY ./utils/ /work/utils/
COPY ./models/ /work/models/
COPY ./default_projects/ /work/default_projects/
COPY ./lambda_bases/ /work/lambda_bases/
COPY ./email_templates/ /work/email_templates/
COPY ./custom-runtime/ /work/custom-runtime/
COPY ./docker-entrypoint.sh /work/

WORKDIR /work/install/
RUN chmod +x /work/install/terraform
RUN /work/install/terraform init
WORKDIR /work/

EXPOSE 7777
EXPOSE 3333

COPY ./server.py /work/

ENTRYPOINT [ "/bin/bash", "/work/docker-entrypoint.sh" ]
