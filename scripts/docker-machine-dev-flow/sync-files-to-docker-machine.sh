#!/bin/bash

# New style: Push files via lsyncd to the remote box
lsyncd -nodaemon ./lsync-config-local.lua

# Old style: using SSHFS, which "mounts" a remote folder. Unfortunately, the folder is wiped when the machine is restarted... Not super helpful.
#docker-machine ssh machine4 mkdir refinery &

#echo "copying files to box"
#docker-machine scp -r ./refinery machine4:/home/docker
#mkdir "all files copied"

#echo "moving refinery to refinery2 because sshfs is fucked"
#mv refinery refinery2
#mkdir refinery; echo "made refinery directory locally again"

#docker-machine mount machine4:/home/docker/refinery ./refinery

#echo "complete, code is ./refinery and is being autosynced to the docker-machine box"

