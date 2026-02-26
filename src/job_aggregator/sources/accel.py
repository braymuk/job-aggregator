from __future__ import annotations

from typing import Iterable

from .base import JobSourceClient
from ..schemas import IncomingJobPosting


class AccelSourceClient(JobSourceClient):
    """
    Placeholder for Accel-specific ingestion.

    Accel's format differs from the other VC board URLs in SOURCE_LIST.md,
    so this parser is intentionally separate.
    """

    source_name = "accel"

    def __init__(self, board_url: str) -> None:
        self.board_url = board_url

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        # TODO: implement Accel-specific parser.
        return []
