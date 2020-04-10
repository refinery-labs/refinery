#!/bin/bash
docker-compose -f docker-compose.yml start postgresdb
docker-compose -f docker-compose.yml -f scripts/docker-compose-dev.yml up -d front-end
docker-compose -f docker-compose.yml -f scripts/docker-compose-dev.yml up -d refinery
docker-compose -f docker-compose.yml -f scripts/docker-compose-dev.yml up -d git-server
