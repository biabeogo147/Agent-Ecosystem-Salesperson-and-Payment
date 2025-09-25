"""Lightweight stub of :mod:`email_validator` used in tests.

This project only requires basic email validation to satisfy Pydantic's
``EmailStr`` field during testing. Instead of pulling the optional
``email-validator`` dependency we provide the small subset of the interface
used by Pydantic.  The stub simply returns the input email unchanged and raises
``EmailNotValidError`` when the value is clearly empty.
"""

from __future__ import annotations


class EmailNotValidError(ValueError):
    """Exception raised when the email address is invalid."""


class _ValidatedEmail:
    def __init__(self, email: str) -> None:
        self.email = email
        self.normalized = email
        self.local_part = email.split("@", 1)[0]


def validate_email(email: str, *_, **__) -> _ValidatedEmail:
    """Minimal ``validate_email`` implementation for tests.

    Parameters
    ----------
    email:
        Email address supplied by the caller.

    Returns
    -------
    dict[str, str]
        Mapping containing the normalised email address under the ``email`` key.
    """

    if not email:
        raise EmailNotValidError("Email address cannot be empty")
    return _ValidatedEmail(email)


__all__ = ["EmailNotValidError", "validate_email"]

