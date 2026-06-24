"""
INDB Custom Exceptions

Standardized exception hierarchy for better error handling.
"""


class INDBException(Exception):
    """Base exception for all INDB errors"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EventNotFoundError(INDBException):
    """Raised when an event is not found in the database"""

    pass


class FusionError(INDBException):
    """Raised when event fusion fails"""

    pass


class TemporalQueryError(INDBException):
    """Raised when temporal query parsing fails"""

    pass


class StorageError(INDBException):
    """Raised when storage operations fail"""

    pass


class AuthenticationError(INDBException):
    """Raised when authentication fails"""

    pass


class AuthorizationError(INDBException):
    """Raised when authorization fails"""

    pass


class ValidationError(INDBException):
    """Raised when input validation fails"""

    pass


class ConfigurationError(INDBException):
    """Raised when configuration is invalid"""

    pass


class ProtocolError(INDBException):
    """Raised when protocol communication fails"""

    pass


class CacheError(INDBException):
    """Raised when cache operations fail"""

    pass
