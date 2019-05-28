#!/usr/bin/env bash
# This quits out after the first non-successful execution
set -e

echo "Loading Python virtualenv..."
source env/bin/activate
echo "Launching AWS account creator..."
./setup_new_account.py
echo "We must wait 60 seconds for the account to stabilize before setting up the infrastructure..."
echo "*deepest sigh ever sighed*"
sleep 60
echo "Initializing Terraform..."
terraform init
echo "Applying Terraform diagram..."
terraform apply -auto-approve -var-file refinery-customer-aws-config.json
echo "Writing environment details..."
terraform output -json > terraform-refinery-customer-aws-account-details.json
echo "Minted a new Refinery customer AWS account :)"