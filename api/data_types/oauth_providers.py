import enum


class OAuthProvider(enum.Enum):
    github = 'Github'
    google = 'Google'


class RefineryUserTier(enum.Enum):
    # Free tier, makes use of the shared redis cluster
    FREE = 'free'
    # Paid tier, uses their own dedicated redis instance
    PAID = 'paid'
