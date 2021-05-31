
def build_iam_role(principal_service, role_name, policies):
    iam_policies = get_iam_role_policies(role_name, policies)

    assume_role_policy_document = {
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": principal_service
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    return {
        "Type": "AWS::IAM::Role",
        "Properties": {
            "RoleName": role_name,
            "AssumeRolePolicyDocument": assume_role_policy_document,
            "Policies": iam_policies
        }
    }


def get_iam_role_policies(role_name, policies):
    base_policy_name = role_name + "Policy"
    role_policies = []
    for n, policy in enumerate(policies):
        action = policy["action"]
        resource = policy["resource"]

        role_policies.append(
            {
                "PolicyName": f"{base_policy_name}{n}",
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": action,
                            "Resource": resource
                        }
                    ]
                }
            }
        )
    return role_policies
