from __future__ import annotations

import re

from .config import Settings
from .schemas import IncomingJobPosting

_TARGET_ROLE_PATTERN = re.compile(r"\b(software engineer|backend engineer)\b", re.IGNORECASE)
_ABOVE_STANDARD_PATTERN = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|vp|v\.p\.|distinguished|fellow|architect|founding|cto|chief)\b|vice president",
    re.IGNORECASE,
)


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _location_matches_preference(location: str | None, preference: str) -> bool:
    location_norm = _normalized_text(location)
    preference_norm = _normalized_text(preference)
    if not location_norm or not preference_norm:
        return False

    if preference_norm in {"nyc", "new york", "new york city"}:
        nyc_tokens = ("new york", "new york city", "nyc", "manhattan", "brooklyn", "queens", "bronx")
        return any(token in location_norm for token in nyc_tokens)

    return preference_norm in location_norm


def _is_standard_software_engineer_title(title: str) -> bool:
    if not _TARGET_ROLE_PATTERN.search(title):
        return False
    if _ABOVE_STANDARD_PATTERN.search(title):
        return False
    return True


def is_match(job: IncomingJobPosting, settings: Settings) -> bool:
    role_match = _is_standard_software_engineer_title(job.title)

    if settings.preference_remote_only:
        location_match = job.is_remote
    else:
        location_match = _location_matches_preference(job.location, settings.preference_location) or job.is_remote

    return role_match and location_match
