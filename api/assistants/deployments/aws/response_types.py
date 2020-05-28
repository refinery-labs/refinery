class CloudwatchRuleTarget:
    def __init__(self, arn):
        self.arn = arn


class TopicSubscription:
    def __init__(self, subscription_arn, endpoint):
        self.subscription_arn = subscription_arn
        self.endpoint = endpoint
