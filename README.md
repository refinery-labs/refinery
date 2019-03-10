# Refinery

## Development Configuration

To run your own version of Refinery first clone this repository to your machine.

You must first create a filled-out `docker-compose.yaml` file in order to build the system properly.

Some of the values in this YAML file with have to be obtained from running the AWS account configuration script found at `install/setup_aws_account.py`. The relevant lines are noted via YAML comments.

Once you've properly filled out your `docker-compose.yaml` file you can then build Refinery with the command `docker-compose up --build` (depending on your Docker configuration you may need to use `sudo`). Both `docker` and `docker-compose` are required to do this.