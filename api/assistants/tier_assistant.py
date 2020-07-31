from models.users import RefineryUserTier

TIER_CONFIG_DEFAULT = "default"

TIER_CONFIG_LOG_RETENTION_DAYS = "log_retention_days"


class TierAssistant:
    def __init__(self, app_config):
        self.tier_config = app_config.get("tier_config")

        self._log_retention_days = self.tier_config[TIER_CONFIG_LOG_RETENTION_DAYS]

    def log_retention_days(self, tier: RefineryUserTier):
        log_retention_days = self._log_retention_days.get(tier.value)
        if log_retention_days is None:
            return self._log_retention_days.get(TIER_CONFIG_DEFAULT)

        return log_retention_days
