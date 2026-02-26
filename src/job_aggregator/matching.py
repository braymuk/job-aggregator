from __future__ import annotations

from .config import Settings
from .schemas import IncomingJobPosting


def is_match(job: IncomingJobPosting, settings: Settings) -> bool:
    haystack = " ".join(
        part for part in (job.title, job.description or "", job.company, job.location or "") if part
    ).lower()

    keyword_match = any(keyword in haystack for keyword in settings.preference_keywords)

    if settings.preference_remote_only:
        location_match = job.is_remote
    else:
        location_text = (job.location or "").lower()
        location_match = settings.preference_location in location_text or job.is_remote

    return keyword_match and location_match
