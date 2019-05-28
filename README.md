# Refinery

## Development Configuration

To run your own version of Refinery first clone this repository to your machine.

You must first create a filled-out `docker-compose.yaml` file in order to build the system properly.

Some of the values in this YAML file with have to be obtained from running the AWS account configuration script found at `install/setup_aws_account.py`. The relevant lines are noted via YAML comments.

Once you've properly filled out your `docker-compose.yaml` file you can then build Refinery with the command `docker-compose up --build` (depending on your Docker configuration you may need to use `sudo`). Both `docker` and `docker-compose` are required to do this.

### Using docker-machine
You might not want to run everything on your host OS for a variety of reasons. Because development of this app uses Docker, in order to use Docker without "sudo" you need to add your user to the docker group. Unfortunately, this has the side effect that all code executed as your user now also effectively have Root because Docker allows binding all folder paths via mount. That means that an attacker can bind your /proc and /etc paths to the container, which you probably don't want.

A way to mitigate this is via using docker-machine. This runs Docker in a VM and doesn't require adding your user to the docker group (mitigating RCE). An attacker could still get code execution, but only in the context of the VM. Much safer. :)

Run the following to get setup:
```sh
# install docker-machine however your distro allows
# on Arch that's:
pikaur -S docker docker-machine

# feel free to name your machine anything. I'm putting machine4 because then I can copy paste this and not change build scripts. :P
# You can swap the driver to be whatever you want. Default is virtualbox, but that's hella slow. Might need to install extra packages for kvm or kvm2 to work.
docker-machine create machine4 --driver=kvm2

# ensure machine is started
docker-machine start machine4

# point the environment variables for your shell at docker-machine's docker by running the following:
eval $(docker-machine env)

# from here on our, you can use docker as normal. You can test that with the following
docker ps

# ^^ that should return some valid output. If it shows any errors, you'll have to google.

# after that, you'll need to install lsync for the dev scripts to use
# on Arch that's:
pikaur -S lsyncd
```

From there, you can run the dev script to sync files like so:
```sh
# go to the folder so that the script can use relative paths from here
cd ./scripts/docker-machine-dev-flow

# make any changes to lsync-config.lua for your local docker-machine env
# you'll need to point the IP to the correct one. Get this via:
docker-machine ip machine4

# This will run lsync
./sync-files-to-docker-machine.sh

# output should show lsync sycing stuff properly
```



