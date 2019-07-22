# Configuring a Third-Party AWS Account to Work with Refinery

* Sign in to your Root AWS account (any AWS account with Administrative privileges should work as well).
* Navigate to the IAM Roles page: [https://console.aws.amazon.com/iam/home?region=us-west-2#/roles](https://console.aws.amazon.com/iam/home?region=us-west-2#/roles)
* Click the `Create role` button
* Click `Another AWS account`
* Set `Account ID` to `134071937287` (the Refinery root account)
* Click the `Next: Permissions` button.
* Check the `AdministratorAccess` policy
* Click `Next: Tags`
* Click `Next: Review`
* Set the the `Role name` to `DO_NOT_DELETE_REFINERY_SYSTEM_ACCOUNT`
* Click `Create role`

<video style="width: 100%" controls autoplay muted loop>
	<source src="/setup-third-party-aws-account/media/set-up-aws-account-video.webm" type="video/webm" />
	<source src="/setup-third-party-aws-account/media/set-up-aws-account-video.mp4" type="video/mp4" />
</video>

You've now set up your AWS account to work with Refinery! All that's left to do is to send us your AWS Account ID. Navigate to [https://console.aws.amazon.com/billing/home?#/account](https://console.aws.amazon.com/billing/home?#/account) and record the account number next to `Account Id`:

<img src="/setup-third-party-aws-account/media/aws-account-id.png" />

Once you have that just send the AWS Account ID and your Refinery email address to us at `support@refinery.io` and we'll onboard you.