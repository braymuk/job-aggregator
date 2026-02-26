from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .base import JobSourceClient
from ..schemas import IncomingJobPosting


class SkeletonSourceClient(JobSourceClient):
    """Temporary source for local testing until real integrations are added."""

    source_name = "skeleton"

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        return [
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-001",
                title="Python Backend Engineer",
                company="Example Co",
                location="United States",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-001",
                posted_at=datetime.now(timezone.utc),
                description="Build APIs and backend systems in Python.",
            )
        ]
