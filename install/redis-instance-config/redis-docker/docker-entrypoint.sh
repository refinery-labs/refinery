#!/bin/sh
set -e

redis-server /usr/local/etc/redis/redis.conf --requirepass $REDIS_PASSWORD
