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
    # Will not work without .go extension, otherwise Go looks for a package with the name
    cp "$@" /tmp/block-code.go

    # Must be a relative path, so put us into the directory we expect
    cd /tmp

    # Run the copy of the file -- this will compile it and then run it automatically
    go run ./block-code.go
else
    # Just execute the binary if it's not inline
    exec "$@"
fi

