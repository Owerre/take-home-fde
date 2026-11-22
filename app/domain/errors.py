"""Actionable application failures; source values and secrets stay out of errors."""


class CloudNovaError(Exception):
    """Root for expected application failures."""


class ConfigurationError(CloudNovaError):
    """Invalid or missing configuration."""


class BuildError(CloudNovaError):
    """The build could not satisfy its source or output contracts."""


class RequestError(CloudNovaError):
    """Invalid structured metric request."""


class InterpretationError(CloudNovaError):
    """The model could not supply a safe supported interpretation."""


class QueryError(CloudNovaError):
    """A bounded metric query failed."""
