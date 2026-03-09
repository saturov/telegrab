from __future__ import annotations

from telegrab.models import ExitCode, TelegrabError


def ensure_no_control_chars(value: str, field_name: str, code: ExitCode = ExitCode.INVALID_LINK) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise TelegrabError(code, f"{field_name} must not contain control characters.")
    return value
