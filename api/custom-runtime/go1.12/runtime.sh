#!/usr/bin/env bash

# Required for Golang to function
export GOPATH=/tmp/go:/var/task/go
export GOCACHE=/tmp/gocache
export GOROOT=/opt/bin/go
export PATH=$PATH:$GOROOT/bin
export GO111MODULE=on


# Check if we're an inline execution or not
if [ -n "$IS_INLINE_EXECUTOR" ]
then
    # Create go folder in /tmp for builds, if it doesn't exist
    [ ! -d "/tmp/go" ] && mkdir -p /tmp/go/src/refinery.io/build/output
    [ ! -d "/tmp/gocache" ] && cp -R /var/task/gocache /tmp/gocache

    # Copy over the Go module file that declares our package
    cp /var/task/go.* /tmp/go/src/refinery.io/build/output/

    # Copy symlink to shared_files, while preserving it
    cp -P /var/task/shared_files /tmp/go/src/refinery.io/build/output/shared_files

    # Will not work without .go extension, otherwise Go looks for a package with the name
    cp "$@" /tmp/go/src/refinery.io/build/output/block-code.go

    # Must be a relative path, so put us into the directory we expect
    cd /tmp/go/src/refinery.io/build/output/

    # Run the copy of the file -- this will compile it and then run it automatically
    go run ./block-code.go
else
    # Just execute the binary if it's not inline
    exec "$@"
fi

