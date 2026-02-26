from __future__ import annotations

from typing import Iterable

from .base import JobSourceClient
from ..schemas import IncomingJobPosting


class LinkedInSourceClient(JobSourceClient):
    """Reserved parser slot for LinkedIn-specific ingestion."""

    source_name = "linkedin"

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        # TODO: implement robust LinkedIn ingestion strategy.
        return []


class AppleSourceClient(JobSourceClient):
    """Reserved parser slot for Apple careers ingestion."""

    source_name = "apple"

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        # TODO: implement Apple careers parser/API client.
        return []


class GoogleSourceClient(JobSourceClient):
    """Reserved parser slot for Google careers ingestion."""

    source_name = "google"

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        # TODO: implement Google careers parser/API client.
        return []
