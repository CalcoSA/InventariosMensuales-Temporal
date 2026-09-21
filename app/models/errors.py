class DomainError(Exception):
    status = 400


class AccessDenied(DomainError):
    status = 403


class DuplicateInventory(DomainError):
    status = 409


class GoogleUnavailable(DomainError):
    status = 503


class WriteUncertain(GoogleUnavailable):
    """A write may have reached Google. Never replay it automatically."""


class ConfigurationError(DomainError):
    status = 503
