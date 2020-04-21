def get_ec2_instance_ids(aws_client_factory, credentials):
    ec2_client = aws_client_factory.get_aws_client(
        "ec2",
        credentials
    )

    # Turn off all EC2 instances (AKA just redis)
    ec2_describe_instances_response = ec2_client.describe_instances(
        MaxResults=1000
    )

    # List of EC2 instance IDs
    ec2_instance_ids = []

    for ec2_instance_data in ec2_describe_instances_response["Reservations"][0]["Instances"]:
        ec2_instance_ids.append(
            ec2_instance_data["InstanceId"]
        )

    return ec2_instance_ids
