FROM golang AS builder

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates

ADD . /code
WORKDIR /code
RUN make

FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /code/bin/main /main

WORKDIR /
ENTRYPOINT ["/main"]
