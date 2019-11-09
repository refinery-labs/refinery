#!/usr/bin/env bash

# Required for Golang to function
export GOPATH=/tmp/go:/var/task/go
export GOCACHE=/tmp/gocache
export GOROOT=/opt/go
export PATH=$PATH:$GOROOT/bin

# Create go folder in /tmp for builds, if it doesn't exist
[ ! -d "/tmp/go" ] && mkdir /tmp/go && mkdir /tmp/go/src
[ ! -d "/tmp/gocache" ] && mkdir /tmp/gocache

# Check if we're an inline execution or not
if [ -n "$IS_INLINE_EXECUTOR" ]
then
    cp "$@" /tmp/block-code.go
    # export GO111MODULE=off
    cd /tmp
    # go run $(realpath --relative-to="/tmp" "$@")
    go run ./block-code.go
else
    # Just execute the binary if it's not inline
    exec "$@"
fi

