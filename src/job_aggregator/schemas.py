from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IncomingJobPosting:
    source: str
    source_job_id: str | None
    title: str
    company: str
    location: str | None
    is_remote: bool
    apply_url: str
    posted_at: datetime
    description: str | None
