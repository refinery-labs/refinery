vpc_id=$1
# probably a buggy one but just to get you start with something
# ensure your default output is json + you have default region ... 
aws ec2 describe-internet-gateways --filters 'Name=attachment.vpc-id,Values='$vpc_id \
		 | jq -r ".InternetGateways[].InternetGatewayId"
	# terminate all vpc instances
	while read -r instance_id ; do
		 aws ec2 terminate-instances --instance-ids $instance_id
	done < <(aws ec2 describe-instances --filters 'Name=vpc-id,Values='$vpc_id \
		 | jq -r '.Reservations[].Instances[].InstanceId')

	while read -r sg ; do
		 aws ec2 delete-security-group --group-id $sg
	done < <(aws ec2 describe-security-groups --filters 'Name=vpc-id,Values='$vpc_id \
		 | jq -r '.SecurityGroups[].GroupId')

	while read -r rt_id ; do
		 aws ec2 delete-route-table --route-table-id $rt_id ;
	done < <(aws ec2 describe-route-tables --filters 'Name=vpc-id,Values='$vpc_id | \
		 jq -r .RouteTables[].RouteTableId)

	while read -r ig_id ; do
		 aws ec2 detach-internet-gateway --internet-gateway-id $ig_id --vpc-id $vpc_id
	done < <(aws ec2 describe-internet-gateways --filters 'Name=attachment.vpc-id,Values='$vpc_id  \
		 | jq -r ".InternetGateways[].InternetGatewayId")

	while read -r ig_id ; do
		 aws ec2 delete-internet-gateway --internet-gateway-id $ig_id --vpc-id $vpc_id
	done < <(aws ec2 describe-internet-gateways --filters 'Name=attachment.vpc-id,Values='$vpc_id  \
		 | jq -r ".InternetGateways[].InternetGatewayId")

	# delete all vpc subnets
	while read -r subnet_id ; do
		 aws ec2 delete-subnet --subnet-id "$subnet_id"
	done < <(aws ec2 describe-subnets --filters 'Name=vpc-id,Values='$vpc_id | jq -r '.Subnets[].SubnetId')

	# delete the whole vpc
	aws ec2 delete-vpc --vpc-id=$vpc_id
