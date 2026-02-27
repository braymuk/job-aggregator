from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .config import get_settings
from .db import create_tables, get_session
from .digest import get_daily_matches, send_digest
from .ingest import build_default_clients, run_ingestion


def _mask_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    if "@" not in parts.netloc:
        return database_url

    _, host_part = parts.netloc.rsplit("@", 1)
    return urlunsplit((parts.scheme, f"***@{host_part}", parts.path, parts.query, parts.fragment))


def run_daily_flow() -> dict[str, int | bool]:
    settings = get_settings()
    print(f"Using DATABASE_URL={_mask_database_url(settings.database_url)}")
    print(
        "[matching-config] "
        f"remote_only={settings.preference_remote_only} "
        f"location={settings.preference_location!r}"
    )
    create_tables()
    clients = build_default_clients(settings)
    print(f"Ingestion clients configured: {', '.join(client.source_name for client in clients)}")

    with get_session() as session:
        inserted = run_ingestion(session, settings, clients=clients)
        # SessionLocal has autoflush=False, so flush before querying digest window.
        session.flush()
        digest_items = get_daily_matches(session)
        sent = send_digest(settings, digest_items)

    return {
        "inserted": inserted,
        "matched_last_24h": len(digest_items),
        "digest_sent": sent,
    }


def main() -> None:
    result = run_daily_flow()
    print(
        "Daily flow complete: "
        f"inserted={result['inserted']} "
        f"matched_last_24h={result['matched_last_24h']} "
        f"digest_sent={result['digest_sent']}"
    )


if __name__ == "__main__":
    main()
