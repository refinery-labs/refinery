#!/usr/bin/env bash

# Required for Golang to function
export GOPATH=/tmp/go:/var/task/go
export GOCACHE=/tmp/gocache
export GOROOT=/opt/go
export PATH=$PATH:$GOROOT/bin

# Create go folder in /tmp for builds, if it doesn't exist
[ ! -d "/tmp/go" ] && mkdir /tmp/go
[ ! -d "/tmp/gocache" ] && mkdir /tmp/gocache

# Only for debug purposes
ls -lisah /var/task

# Check if we're an inline execution or not
if [ -n "$IS_INLINE_EXECUTOR" ]
then
    # We use go run for inline executions
    go run "$@"
else
    # Just execute the binary if it's not inline
    exec "$@"
fi

