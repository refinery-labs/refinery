class InvalidModelCreationError(Exception):
    pass

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from . import *
