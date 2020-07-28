FROM pypy:3

RUN mkdir /work/
WORKDIR /work/

COPY ./ /work/
RUN pip3 install -r /work/requirements.txt

EXPOSE 4444

ENTRYPOINT [ "pypy3", "/work/bin/pidgeon" ]
