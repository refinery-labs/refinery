import enum


class DeploymentStages(enum.Enum):
    dev = 'dev'
    staging = 'staging'
    prod = 'prod'
