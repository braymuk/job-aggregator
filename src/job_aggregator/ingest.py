from __future__ import annotations

from sqlalchemy.orm import Session

from .config import Settings
from .matching import is_match
from .models import JobPosting
from .sources.accel import AccelSourceClient
from .sources.base import JobSourceClient
from .sources.placeholders import AppleSourceClient, GoogleSourceClient, LinkedInSourceClient
from .sources.skeleton import SkeletonSourceClient
from .sources.vc_board import VCBoardSourceClient, VCBoardSourceConfig


def build_default_clients(settings: Settings) -> list[JobSourceClient]:
    clients: list[JobSourceClient] = []

    if settings.ingest_enable_skeleton_source:
        clients.append(SkeletonSourceClient())

    if settings.ingest_enable_real_sources:
        timeout = settings.ingest_request_timeout_seconds
        clients.extend(
            [
                VCBoardSourceClient(
                    VCBoardSourceConfig(
                        source_name="sequoia",
                        board_url="https://jobs.sequoiacap.com/jobs/?postedSince=P7D&jobTypes=Software+Engineer&locations=New+York",
                        company_fallback="Sequoia Portfolio",
                        timeout_seconds=timeout,
                        api_search_url="https://jobs.sequoiacap.com/api-boards/search-jobs",
                        api_board_id="sequoia-capital",
                        api_job_types=("software-engineer",),
                        api_locations=("New York",),
                        api_posted_since="P7D",
                        api_page_size=15,
                    )
                ),
                VCBoardSourceClient(
                    VCBoardSourceConfig(
                        source_name="a16z",
                        board_url="https://jobs.a16z.com/jobs/?postedSince=P7D&jobTypes=Software+Engineer&locations=New+York",
                        company_fallback="a16z Portfolio",
                        timeout_seconds=timeout,
                        api_search_url="https://jobs.a16z.com/api-boards/search-jobs",
                        api_job_types=("software-engineer",),
                        api_locations=("New York",),
                        api_posted_since="P7D",
                        api_page_size=15,
                    )
                ),
                VCBoardSourceClient(
                    VCBoardSourceConfig(
                        source_name="lsvp",
                        board_url="https://jobs.lsvp.com/jobs?jobTypes=Software+Engineer&locations=New+York&locations=San+Francisco+Bay+Area&postedSince=P1D",
                        company_fallback="Lightspeed Portfolio",
                        timeout_seconds=timeout,
                        api_search_url="https://jobs.lsvp.com/api-boards/search-jobs",
                        api_board_id="lightspeed",
                        api_job_types=("software-engineer",),
                        api_locations=("New York", "San Francisco Bay Area"),
                        api_posted_since="P7D",
                        api_page_size=15,
                        api_grouped=None,
                    )
                ),
            ]
        )
        if settings.ingest_enable_placeholder_sources:
            clients.extend(
                [
                    AccelSourceClient(board_url="https://www.accel.com/jobs"),
                    # Reserved parser slots for future implementation:
                    LinkedInSourceClient(),
                    AppleSourceClient(),
                    GoogleSourceClient(),
                ]
            )

    return clients


def run_ingestion(session: Session, settings: Settings, clients: list[JobSourceClient]) -> int:
    inserted_count = 0
    matched_count = 0

    for client in clients:
        try:
            incoming_jobs = list(client.fetch_recent_jobs())
        except Exception as exc:
            print(f"[ingest:{client.source_name}] fetch failed: {exc}")
            continue

        print(f"[ingest:{client.source_name}] fetched={len(incoming_jobs)}")
        client_inserted = 0
        client_matched = 0

        for incoming in incoming_jobs:
            matched = is_match(incoming, settings)
            job = JobPosting(
                source=incoming.source,
                source_job_id=incoming.source_job_id,
                title=incoming.title,
                company=incoming.company,
                location=incoming.location,
                is_remote=incoming.is_remote,
                apply_url=incoming.apply_url,
                posted_at=incoming.posted_at,
                description=incoming.description,
                matched=matched,
            )
            session.add(job)
            inserted_count += 1
            client_inserted += 1
            if matched:
                matched_count += 1
                client_matched += 1

        print(
            f"[ingest:{client.source_name}] inserted={client_inserted} matched={client_matched}"
        )

    print(f"[ingest] total_inserted={inserted_count} total_matched={matched_count}")

    return inserted_count
