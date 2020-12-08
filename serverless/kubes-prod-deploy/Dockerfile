FROM public.ecr.aws/lambda/python:3.8

ENV BUILD_ENV 'dev'
ENV AWS_DEFAULT_REGION 'us-west-2'
ENV EKS_CLUSTER_NAME 'refinery'
ENV EKS_KUBECTL_ROLE_ARN ''
ENV REPOSITORY_URI ''
ENV GIT_SSH_COMMAND ssh -o UserKnownHostsFile=/var/task/known_hosts -i /var/task/id_rsa

RUN yum update && yum install -y awscli git python-pip openssl tar

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && \
			chmod +x kubectl && \
			mv ./kubectl /usr/local/bin/kubectl && \
      curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 > get_helm.sh && \
      chmod 700 get_helm.sh && \
      ./get_helm.sh

COPY requirements.txt /var/task/

RUN pip install -r /var/task/requirements.txt

COPY app.py known_hosts /var/task/

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "app.handler" ]
