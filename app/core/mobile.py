import re

from app.core.exceptions import ValidationFailed

_CANONICAL = re.compile(r"^\+947\d{8}$")
_LOCAL = re.compile(r"^07\d{8}$")


def normalize_mobile(raw: str | None) -> str:
    """Trim, drop internal spaces/hyphens, accept 07XXXXXXXX or +947XXXXXXXX -> +947XXXXXXXX."""
    cleaned = re.sub(r"[ \-]", "", (raw or "").strip())
    if _CANONICAL.match(cleaned):
        return cleaned
    if _LOCAL.match(cleaned):
        return "+94" + cleaned[1:]
    raise ValidationFailed("Mobile number must be 07XXXXXXXX or +947XXXXXXXX")
