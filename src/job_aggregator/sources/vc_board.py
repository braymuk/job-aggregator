from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
import ssl
from typing import Any, Iterable
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import certifi

from .base import JobSourceClient
from ..schemas import IncomingJobPosting


@dataclass(frozen=True)
class VCBoardSourceConfig:
    source_name: str
    board_url: str
    company_fallback: str
    timeout_seconds: int = 20
    api_search_url: str | None = None
    api_board_id: str | None = None
    api_job_types: tuple[str, ...] = ("software-engineer",)
    api_locations: tuple[str, ...] = ("New York",)
    api_posted_since: str = "P1D"
    api_page_size: int = 25
    api_grouped: bool | None = True


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("jobs", "results", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = _as_list(value)
                if nested:
                    return nested
    return []


def _flatten_grouped_jobs(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    groups = payload.get("jobs")
    if not isinstance(groups, list):
        return []

    flattened: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue

        company = group.get("company")
        company_name = company.get("name") if isinstance(company, dict) else None
        nested_jobs = group.get("jobs")

        if isinstance(nested_jobs, list):
            for job in nested_jobs:
                if not isinstance(job, dict):
                    continue
                merged = dict(job)
                if company_name:
                    merged.setdefault("companyName", company_name)
                flattened.append(merged)
            continue

        if any(key in group for key in ("title", "applyUrl", "url", "jobId")):
            flattened.append(group)

    return flattened


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _pick_text(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _to_text(record.get(key))
        if value:
            return value
    return None


def _pick_location(record: dict[str, Any]) -> str | None:
    location = _pick_text(record, ("location", "locationName", "city"))
    if location:
        return location

    normalized_locations = record.get("normalizedLocations")
    if isinstance(normalized_locations, list):
        for item in normalized_locations:
            if isinstance(item, dict):
                label = _pick_text(item, ("label", "value", "id"))
                if label:
                    return label
            if isinstance(item, str) and item.strip():
                return item.strip()

    raw_locations = record.get("locations")
    if isinstance(raw_locations, list):
        for item in raw_locations:
            if isinstance(item, dict):
                name = _pick_text(item, ("name", "location"))
                if name:
                    return name
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _origin_from_url(url: str) -> str:
    parts = url.split("/", 3)
    if len(parts) >= 3:
        return f"{parts[0]}//{parts[2]}"
    return url


def _extract_board_id_from_html(html: str) -> str | None:
    patterns = [
        r'"board"\s*:\s*\{\s*"id"\s*:\s*"([^"]+)"',
        r'"fixedBoard"\s*:\s*"([^"]+)"',
        r'"id"\s*:\s*"([^"]+)"\s*,\s*"isParent"\s*:\s*true',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_anchor = False
        self._current_href: str | None = None
        self._current_text_chunks: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = None
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value
                break
        if href:
            self._in_anchor = True
            self._current_href = href
            self._current_text_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._current_text_chunks.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._in_anchor or not self._current_href:
            return
        text = " ".join(chunk for chunk in self._current_text_chunks if chunk).strip()
        self.links.append((self._current_href, text))
        self._in_anchor = False
        self._current_href = None
        self._current_text_chunks = []


def _looks_like_job_link(url: str) -> bool:
    lowered = url.lower()
    return any(
        token in lowered
        for token in ("/jobs/", "/job/", "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com")
    )


def _looks_like_job_title(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered or len(lowered) < 4:
        return False
    banned = {
        "apply",
        "learn more",
        "view all",
        "all jobs",
        "next",
        "previous",
        "read more",
    }
    return lowered not in banned


def _parse_jobs_from_html(
    html: str, source_name: str, board_url: str, company_fallback: str
) -> list[IncomingJobPosting]:
    parser = _AnchorCollector()
    parser.feed(html)

    seen_urls: set[str] = set()
    jobs: list[IncomingJobPosting] = []
    for raw_href, raw_text in parser.links:
        absolute_url = urljoin(board_url, raw_href)
        if absolute_url in seen_urls:
            continue
        if not _looks_like_job_link(absolute_url):
            continue
        if not _looks_like_job_title(raw_text):
            continue

        seen_urls.add(absolute_url)
        jobs.append(
            IncomingJobPosting(
                source=source_name,
                source_job_id=None,
                title=raw_text.strip(),
                company=company_fallback,
                location=None,
                is_remote=False,
                apply_url=absolute_url,
                posted_at=datetime.now(timezone.utc),
                description=None,
            )
        )
    return jobs


class VCBoardSourceClient(JobSourceClient):
    """Generic connector for similar VC portfolio jobs board formats."""

    def __init__(self, config: VCBoardSourceConfig) -> None:
        self.config = config
        self.source_name = config.source_name

    def _fetch_html(self, ssl_context: ssl.SSLContext) -> tuple[str, str, str]:
        request = Request(
            self.config.board_url,
            headers={"User-Agent": "job-aggregator/0.1 (+local-dev)"},
        )
        with urlopen(request, timeout=self.config.timeout_seconds, context=ssl_context) as response:
            body = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            status = getattr(response, "status", "unknown")
            return body, content_type, str(status)

    def _fetch_payload(self, ssl_context: ssl.SSLContext) -> tuple[Any, str, str]:
        if self.config.api_search_url:
            board_id = self.config.api_board_id
            if not board_id:
                html_body, _, _ = self._fetch_html(ssl_context)
                board_id = _extract_board_id_from_html(html_body)
                if not board_id:
                    print(f"[source:{self.source_name}] unable to auto-discover board id")
                    return html_body, "text/html", "200"
                print(f"[source:{self.source_name}] discovered board_id={board_id}")

            request_body = {
                "meta": {"size": self.config.api_page_size},
                "board": {"id": board_id, "isParent": True},
                "query": {
                    "jobTypes": list(self.config.api_job_types),
                    "locations": list(self.config.api_locations),
                    "postedSince": self.config.api_posted_since,
                    "promoteFeatured": True,
                },
            }
            if self.config.api_grouped is not None:
                request_body["grouped"] = self.config.api_grouped
            request = Request(
                self.config.api_search_url,
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "User-Agent": "job-aggregator/0.1 (+local-dev)",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Origin": _origin_from_url(self.config.board_url),
                    "Referer": self.config.board_url,
                },
                method="POST",
            )
            with urlopen(request, timeout=self.config.timeout_seconds, context=ssl_context) as response:
                body = response.read().decode("utf-8", errors="replace")
                content_type = response.headers.get("Content-Type", "")
                status = getattr(response, "status", "unknown")
                print(f"[source:{self.source_name}] api_search status={status} content_type={content_type}")
                return json.loads(body), content_type, str(status)

        body, content_type, status = self._fetch_html(ssl_context)
        if "json" in content_type.lower():
            return json.loads(body), content_type, status
        return body, content_type, status

    def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            payload_or_html, content_type, status = self._fetch_payload(ssl_context)
        except Exception as exc:
            print(f"[source:{self.source_name}] request failed url={self.config.board_url} error={exc}")
            return []

        if isinstance(payload_or_html, str):
            preview = payload_or_html[:180].replace("\n", " ").strip()
            print(
                f"[source:{self.source_name}] html response status={status} "
                f"content_type={content_type or 'unknown'} preview={preview!r}"
            )
            html_jobs = _parse_jobs_from_html(
                payload_or_html,
                source_name=self.source_name,
                board_url=self.config.board_url,
                company_fallback=self.config.company_fallback,
            )
            print(f"[source:{self.source_name}] html_fallback_jobs={len(html_jobs)}")
            return html_jobs
        payload = payload_or_html

        jobs: list[IncomingJobPosting] = []
        records = _flatten_grouped_jobs(payload) or _as_list(payload)
        if not records:
            print(
                f"[source:{self.source_name}] json parsed but no job records found "
                f"(keys={list(payload.keys())[:10] if isinstance(payload, dict) else 'list'})"
            )
            return []

        for record in records:
            title = _pick_text(record, ("title", "name", "text"))
            apply_url = _pick_text(record, ("applyUrl", "url", "jobUrl", "absoluteUrl", "hostedUrl"))
            if apply_url:
                apply_url = urljoin(self.config.board_url, apply_url)

            if not title or not apply_url:
                continue

            company = _pick_text(record, ("company", "companyName", "organizationName")) or self.config.company_fallback
            location = _pick_location(record)
            description = _pick_text(record, ("description", "summary", "snippet"))
            posted_at = _parse_datetime(
                record.get("postedAt")
                or record.get("createdAt")
                or record.get("listedAt")
                or record.get("publicationDate")
                or record.get("timeStamp")
            )

            remote_flag = bool(record.get("isRemote") or record.get("remote"))
            is_remote = remote_flag or ("remote" in (location or "").lower())

            source_job_id = _pick_text(record, ("id", "jobId", "slug", "externalId"))

            jobs.append(
                IncomingJobPosting(
                    source=self.source_name,
                    source_job_id=source_job_id,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=is_remote,
                    apply_url=apply_url,
                    posted_at=posted_at,
                    description=description,
                )
            )
        print(f"[source:{self.source_name}] parsed_jobs={len(jobs)}")
        return jobs
