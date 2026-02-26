from __future__ import annotations

from typing import Iterable

from ..schemas import IncomingJobPosting


class JobSourceClient:
    """Base interface for source connectors."""

    source_name: str

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        raise NotImplementedError
