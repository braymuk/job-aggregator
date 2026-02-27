from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .base import JobSourceClient
from ..schemas import IncomingJobPosting


class SkeletonSourceClient(JobSourceClient):
    """Temporary source for local testing until real integrations are added."""

    source_name = "skeleton"

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        now = datetime.now(timezone.utc)
        return [
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-001",
                title="Python Backend Engineer",
                company="Example Co",
                location="NYC",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-001",
                posted_at=now,
                description="Build APIs and backend systems in Python.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-002",
                title="Software Engineer",
                company="Atlas Labs",
                location="New York City, NY",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-002",
                posted_at=now,
                description="Product engineering role focused on customer features.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-003",
                title="Software Engineer II",
                company="Northstar Systems",
                location="Manhattan, NY",
                is_remote=False,
                apply_url="https://example.com/jobs/demo-003",
                posted_at=now,
                description="Backend systems and internal tooling.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-004",
                title="Senior Software Engineer",
                company="Pioneer Data",
                location="Brooklyn, NY",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-004",
                posted_at=now,
                description="Senior-level platform engineering role.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-005",
                title="Founding Backend Engineer",
                company="Seedling AI",
                location="San Francisco, CA",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-005",
                posted_at=now,
                description="Founding team role for early product development.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-006",
                title="Backend Engineer",
                company="Rivet Cloud",
                location="Austin, TX",
                is_remote=False,
                apply_url="https://example.com/jobs/demo-006",
                posted_at=now,
                description="Onsite backend role building data pipelines.",
            ),
            IncomingJobPosting(
                source=self.source_name,
                source_job_id="demo-007",
                title="Product Designer",
                company="Palette Tech",
                location="Queens, NY",
                is_remote=True,
                apply_url="https://example.com/jobs/demo-007",
                posted_at=now,
                description="Own design systems and product UX.",
            ),
        ]
