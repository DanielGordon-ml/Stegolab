"""Exception hierarchy. Each error carries the CLI exit code from spec §15/§10.8."""


class StegoLabError(Exception):
    """Base for all StegoLab errors. Generic runtime failure."""

    exit_code: int = 1


class InvalidArguments(StegoLabError):
    exit_code = 2


class CapacityExceeded(StegoLabError):
    exit_code = 3


class NoPayloadFound(StegoLabError):
    exit_code = 4


class CorruptedPayload(StegoLabError):
    exit_code = 4


class IntegrityCheckFailed(StegoLabError):
    exit_code = 4


class WrongKey(StegoLabError):
    exit_code = 4


class UnsupportedFileType(StegoLabError):
    exit_code = 5


class UnsupportedMethod(StegoLabError):
    exit_code = 5


class MissingOptionalDependency(StegoLabError):
    exit_code = 6


class OutputExists(StegoLabError):
    exit_code = 7
