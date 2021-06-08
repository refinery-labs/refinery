import enum


class DeploymentStages(enum.Enum):
    dev = 'dev'
    staging = 'staging'
    prod = 'prod'


class DeploymentStates(enum.Enum):
    not_started = 'not_started'
    in_progress = 'in_progress'
    failed = 'failed'
    succeeded = 'succeeded'
