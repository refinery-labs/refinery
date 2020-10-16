class CloudwatchRuleTarget:
    def __init__(self, arn):
        self.arn = arn


class TopicSubscription:
    def __init__(self, subscription_arn, endpoint):
        self.subscription_arn = subscription_arn
        self.endpoint = endpoint


class LambdaEventSourceMapping:
    def __init__(self, uuid, event_source_arn, state):
        self.uuid = uuid
        self.event_source_arn = event_source_arn
        self.state = state
