from typing import Any


def strip_whitespace(value: Any) -> Any:

    if isinstance(value, str):
        return value.strip()
    elif isinstance(value, dict):
        return {k: strip_whitespace(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [strip_whitespace(item) for item in value]
    return value


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    return email.lower().strip()
