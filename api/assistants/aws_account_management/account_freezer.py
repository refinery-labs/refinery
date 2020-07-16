import json
import time

import botocore
from tornado.concurrent import run_on_executor

from utils.base_spawner import BaseSpawner
from utils.general import logit
from utils.general import get_urand_password
from utils.aws_client import get_aws_client
from models.aws_accounts import AWSAccount


class AwsAccountFreezer(BaseSpawner):
    def __init__(self, aws_cloudwatch_client, logger, db_session_maker, app_config):
        super().__init__(self, aws_cloudwatch_client, logger, app_config=app_config)

        self.db_session_maker = db_session_maker

    @run_on_executor
    def freeze_aws_account( self, credentials ):
        return AwsAccountFreezer._freeze_aws_account(self.app_config, self.db_session_maker, credentials)

    @staticmethod
    def _freeze_aws_account( app_config, db_session_maker, credentials ):
        """
        Freezes an AWS sub-account when the user exceeds their free-tier
        monthly-quota.
        The steps are as follows:
        * Disable AWS console access by changing the password
        * Revoke all active AWS console sessions
        * Iterate over all deployed Lambdas and throttle them
        * Stop all active CodeBuilds
        """
        logit( "Freezing AWS account..." )

        # Rotate and log out users from the AWS console
        new_console_user_password = AwsAccountFreezer._recreate_aws_console_account(
            app_config,
            credentials,
            True
        )

        # Update the console login in the database
        dbsession = db_session_maker()
        aws_account = dbsession.query( AWSAccount ).filter_by(
            account_id=credentials[ "account_id" ]
        ).first()
        aws_account.iam_admin_password = new_console_user_password
        dbsession.commit()
        dbsession.close()

        # Get Lambda ARNs
        lambda_arn_list = AwsAccountFreezer.get_lambda_arns(credentials)
        lambda_arn_list = AwsAccountFreezer.filter_out_free_tier_limiter(
            lambda_arn_list
        )

        AwsAccountFreezer.set_zero_concurrency_for_lambdas(
            credentials,
            lambda_arn_list
        )

        AwsAccountFreezer.stop_all_codebuilds(
            credentials
        )

        AwsAccountFreezer.stop_all_ec2_instances(
            credentials
        )

        dbsession = db_session_maker()
        aws_account = dbsession.query( AWSAccount ).filter_by(
            account_id=credentials[ "account_id" ]
        ).first()
        aws_account.is_frozen = True
        dbsession.commit()
        dbsession.close()

        logit( "Account freezing complete, stay frosty!" )

        return False

    @staticmethod
    def filter_out_free_tier_limiter( lambda_arn_list ):
        """
        This removes the Free Tier Concurrency Limiter Lambda
        from the ARN list so it's concurrency is not changed.
        That Lambda is a special case because it's used to limit
        the number of concurrent Lambdas a free-tier user can
        execute at the same time.
        """
        return_list = []

        for lambda_arn in lambda_arn_list:
            # If it's the free-tier limiter, skip it.
            if lambda_arn.endswith( ":FreeTierConcurrencyLimiter" ):
                continue

            return_list.append(
                lambda_arn
            )

        return return_list

    @staticmethod
    def stop_all_ec2_instances( credentials ):
        ec2_client = get_aws_client(
            "ec2",
            credentials
        )

        ec2_instance_ids = AwsAccountFreezer.get_ec2_instance_ids(credentials)

        if len(ec2_instance_ids) > 0:
            stop_instance_response = ec2_client.stop_instances(
                InstanceIds=ec2_instance_ids
            )

    @staticmethod
    def stop_all_codebuilds( credentials ):
        codebuild_client = get_aws_client(
            "codebuild",
            credentials
        )

        # List all CodeBuild builds and stop any that are running
        codebuild_build_ids = []
        codebuild_list_params = {}

        while True:
            codebuild_list_response = codebuild_client.list_builds(
                **codebuild_list_params
            )

            for build_id in codebuild_list_response[ "ids" ]:
                codebuild_build_ids.append(
                    build_id
                )

            if not ( "nextToken" in codebuild_list_response ):
                break

            codebuild_list_params[ "nextToken" ] = codebuild_list_response[ "nextToken" ]

        # We now scan these builds to see if they are currently running.
        # We can do this in batches of 100
        active_build_ids = []
        chunk_size = 100

        while len( codebuild_build_ids ) > 0:
            chunk_of_build_ids = codebuild_build_ids[:chunk_size]
            remaining_build_ids = codebuild_build_ids[chunk_size:]
            codebuild_build_ids = remaining_build_ids

            # Pull the information for the build ID chunk
            builds_info_response = codebuild_client.batch_get_builds(
                ids=chunk_of_build_ids,
            )

            # Iterate over the builds info response to find live build IDs
            for build_info in builds_info_response[ "builds" ]:
                if build_info[ "buildStatus" ] == "IN_PROGRESS":
                    active_build_ids.append(
                        build_info[ "id" ]
                    )

        # Run through all active builds and stop them in their place
        for active_build_id in active_build_ids:
            stop_build_response = codebuild_client.stop_build(
                id=active_build_id
            )

    @run_on_executor
    def recreate_aws_console_account( self, credentials, rotate_password ):
        return AwsAccountFreezer._recreate_aws_console_account(
            self.app_config,
            credentials,
            rotate_password
        )

    @staticmethod
    def _recreate_aws_console_account( app_config, credentials, rotate_password ):
        iam_client = get_aws_client(
            "iam",
            credentials
        )

        # The only way to revoke an AWS Console user's session
        # is to delete the console user and create a new one.

        # Generate the IAM policy ARN
        iam_policy_arn = "arn:aws:iam::" + credentials[ "account_id" ] + ":policy/RefineryCustomerPolicy"

        logit( "Deleting AWS console user..." )

        try:
            # Delete the current AWS console user
            delete_user_profile_response = iam_client.delete_login_profile(
                UserName=credentials[ "iam_admin_username" ],
            )
        except:
            logit( "Error deleting login profile, continuing...")

        try:
            # Remove the policy from the user
            detach_user_policy = iam_client.detach_user_policy(
                UserName=credentials[ "iam_admin_username" ],
                PolicyArn=iam_policy_arn
            )
        except:
            logit( "Error detaching user policy, continuing..." )

        try:
            # Delete the IAM user
            delete_user_response = iam_client.delete_user(
                UserName=credentials[ "iam_admin_username" ],
            )
        except Exception as e:
            logit( "Error deleting user, continuing..." )
            print(e)

        logit( "Re-creating the AWS console user..." )

        # Create the IAM user again
        delete_user_response = iam_client.create_user(
            UserName=credentials[ "iam_admin_username" ],
        )

        try:
            # Delete the IAM policy
            delete_policy_response = iam_client.delete_policy(
                PolicyArn=iam_policy_arn
            )
        except Exception as e:
            logit( "Error deleting IAM policy, continuing..." )
            print(e)

        # Create IAM policy for the user
        create_policy_response = iam_client.create_policy(
            PolicyName="RefineryCustomerPolicy",
            PolicyDocument=json.dumps( app_config.get("CUSTOMER_IAM_POLICY") ),
            Description="Refinery Labs managed AWS customer account policy."
        )

        # Attach the limiting IAM policy to it.
        attach_policy_response = iam_client.attach_user_policy(
            UserName=credentials[ "iam_admin_username" ],
            PolicyArn=iam_policy_arn
        )

        # Generate a new user console password
        new_console_user_password = get_urand_password( 32 )

        if rotate_password == False:
            new_console_user_password = credentials[ "iam_admin_password" ]

        # Create the console user again.
        create_user_response = iam_client.create_login_profile(
            UserName=credentials[ "iam_admin_username" ],
            Password=new_console_user_password,
            PasswordResetRequired=False
        )

        return new_console_user_password

    @run_on_executor
    def unfreeze_aws_account( self, credentials ):
        return AwsAccountFreezer._unfreeze_aws_account(
            self.db_session_maker,
            credentials
        )

    @staticmethod
    def _unfreeze_aws_account( db_session_maker, credentials ):
        """
        Unfreezes a previously-frozen AWS account, this is for situations
        where a user has gone over their free-trial or billing limit leading
        to their account getting frozen. By calling this the account will be
        re-enabled for regular Refinery use.
        * De-throttle all AWS Lambdas
        * Turn on EC2 instances (redis)
        """
        logit( "Unfreezing AWS account..." )

        # Pull all Lambda ARN(s)
        lambda_arns = AwsAccountFreezer.get_lambda_arns(
            credentials
        )
        lambda_arns = AwsAccountFreezer.filter_out_free_tier_limiter(
            lambda_arns
        )

        AwsAccountFreezer.remove_lambda_concurrency_limits(
            credentials,
            lambda_arns
        )

        # Start EC2 instance(s)
        ec2_instance_ids = AwsAccountFreezer.get_ec2_instance_ids(credentials)

        if len(ec2_instance_ids) > 0:
            AwsAccountFreezer.start_ec2_instances(
                credentials,
                ec2_instance_ids
            )

        dbsession = db_session_maker()
        aws_account = dbsession.query( AWSAccount ).filter_by(
            account_id=credentials[ "account_id" ]
        ).first()
        aws_account.is_frozen = False
        dbsession.commit()
        dbsession.close()

        logit( "Unfreezing of account is complete!" )

        return True

    @staticmethod
    def start_ec2_instances( credentials, ec2_instance_ids ):
        ec2_client = get_aws_client(
            "ec2",
            credentials
        )

        # Max attempts
        remaining_attempts = 20

        # Prevents issue if a freeze happens too quickly after an un-freeze
        while remaining_attempts > 0:
            try:
                start_instance_response = ec2_client.start_instances(
                    InstanceIds=ec2_instance_ids
                )
            except botocore.exceptions.ClientError as boto_error:
                if boto_error.response[ "Error" ][ "Code" ] != "IncorrectInstanceState":
                    raise

                logit( "EC2 instance isn't ready to be started yet!" )
                logit( "Waiting 2 seconds and trying again..." )
                time.sleep(2)

            remaining_attempts = remaining_attempts - 1

    @staticmethod
    def get_lambda_arns( credentials ):
        lambda_client = get_aws_client(
            "lambda",
            credentials
        )

        # Now we throttle all of the user's Lambdas so none will execute
        # First we pull all of the user's Lambdas
        lambda_list_params = {
            "MaxItems": 50,
        }

        # The list of Lambda ARNs
        lambda_arn_list = []

        while True:
            lambda_functions_response = lambda_client.list_functions(
                **lambda_list_params
            )

            for lambda_function_data in lambda_functions_response[ "Functions" ]:
                lambda_arn_list.append(
                    lambda_function_data[ "FunctionArn" ]
                )

            # Only do another loop if we have more results
            if not ( "NextMarker" in lambda_functions_response ):
                break

            lambda_list_params[ "Marker" ] = lambda_functions_response[ "NextMarker" ]

        return lambda_arn_list

    @staticmethod
    def remove_lambda_concurrency_limits( credentials, lambda_arn_list ):
        """
        Note their is a subtle bug here:
        If someone sets reserved concurrency for their Lambda and their
        account is frozen and unfrozen then they will lose the concurrency
        limit upon the account being unfrozen.
        Potential fixes:
        * Prevent setting concurrency for free-accounts (would make sence given
        they'd already have limited concurrency).
        * Consult the deployment diagrams to get the Lambdas pre-freeze concurrency
        limit.
        """
        lambda_client = get_aws_client(
            "lambda",
            credentials
        )

        # Remove function throttle from each Lambda
        for lambda_arn in lambda_arn_list:
            lambda_client.delete_function_concurrency(
                FunctionName=lambda_arn
            )

    @staticmethod
    def set_zero_concurrency_for_lambdas( credentials, lambda_arn_list ):
        lambda_client = get_aws_client(
            "lambda",
            credentials
        )

        # Iterate over list of Lambda ARNs and set concurrency to zero for all
        for lambda_arn in lambda_arn_list:
            lambda_client.put_function_concurrency(
                FunctionName=lambda_arn,
                ReservedConcurrentExecutions=0
            )

        return True

    @staticmethod
    def get_ec2_instance_ids( credentials ):
        ec2_client = get_aws_client(
            "ec2",
            credentials
        )

        ec2_describe_instances_response = ec2_client.describe_instances(
            MaxResults=1000
        )

        if len( ec2_describe_instances_response[ "Reservations" ] ) == 0:
            return []

        # List of EC2 instance IDs
        ec2_instance_ids = []

        for ec2_instance_data in ec2_describe_instances_response[ "Reservations" ][0][ "Instances" ]:
            ec2_instance_ids.append(
                ec2_instance_data[ "InstanceId" ]
            )

        return ec2_instance_ids
