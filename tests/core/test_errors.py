import pytest

from stegolab.core import errors


def test_base_error_default_exit_code():
    assert errors.StegoLabError().exit_code == 1


@pytest.mark.parametrize(
    "exc_cls, code",
    [
        (errors.InvalidArguments, 2),
        (errors.CapacityExceeded, 3),
        (errors.NoPayloadFound, 4),
        (errors.CorruptedPayload, 4),
        (errors.IntegrityCheckFailed, 4),
        (errors.WrongKey, 4),
        (errors.UnsupportedFileType, 5),
        (errors.UnsupportedMethod, 5),
        (errors.MissingOptionalDependency, 6),
        (errors.OutputExists, 7),
    ],
)
def test_exit_codes(exc_cls, code):
    assert exc_cls.exit_code == code
    assert issubclass(exc_cls, errors.StegoLabError)
    assert issubclass(exc_cls, Exception)
