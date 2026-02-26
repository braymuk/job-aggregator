from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import JobPosting


@dataclass(frozen=True)
class DigestItem:
    title: str
    company: str
    location: str | None
    posted_at: datetime
    apply_url: str


def get_daily_matches(session: Session) -> list[DigestItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    print(f"[digest] querying matched jobs since {cutoff.isoformat()}")
    stmt: Select[tuple[JobPosting]] = (
        select(JobPosting)
        .where(JobPosting.matched.is_(True), JobPosting.posted_at >= cutoff)
        .order_by(JobPosting.posted_at.desc())
    )
    jobs = session.execute(stmt).scalars().all()

    items = [
        DigestItem(
            title=job.title,
            company=job.company,
            location=job.location,
            posted_at=job.posted_at,
            apply_url=job.apply_url,
        )
        for job in jobs
    ]
    print(f"[digest] matched_last_24h={len(items)}")
    for item in items[:5]:
        print(f"[digest] item: {item.title} | {item.company} | {item.apply_url}")
    if len(items) > 5:
        print(f"[digest] ... plus {len(items) - 5} more")
    return items


def build_digest_email(settings: Settings, items: list[DigestItem]) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"Daily Job Digest ({len(items)} new matches)"
    message["From"] = settings.digest_email_from
    message["To"] = settings.digest_email_to

    lines = ["New matching jobs from the last 24 hours:", ""]
    for item in items:
        location = item.location or "Unknown"
        posted = item.posted_at.strftime("%Y-%m-%d %H:%M %Z")
        lines.append(f"- {item.title} | {item.company} | {location} | posted {posted}")
        lines.append(f"  {item.apply_url}")

    message.set_content("\n".join(lines))
    return message


def send_digest(settings: Settings, items: list[DigestItem]) -> bool:
    if not items:
        print("[digest] skipping email send (no matched items)")
        return False

    print(
        f"[digest] sending email to={settings.digest_email_to} via "
        f"{settings.digest_smtp_host}:{settings.digest_smtp_port} items={len(items)}"
    )
    email = build_digest_email(settings, items)
    with smtplib.SMTP(settings.digest_smtp_host, settings.digest_smtp_port, timeout=30) as smtp:
        if settings.digest_use_tls:
            smtp.starttls()
        if settings.digest_smtp_username:
            smtp.login(settings.digest_smtp_username, settings.digest_smtp_password)
        smtp.send_message(email)

    print("[digest] email send complete")
    return True
