"""Morning Brief Agent entrypoint — ingest → process → deliver.

Runs once per invocation. Azure Container Apps Job cron calls this at 6 AM PST/PDT.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from config import load
from delivery.email_sender import send_email
from ingestion.base import SourceResult
from ingestion.bluesky_fetcher import fetch_bluesky
from ingestion.github_trending import fetch_github_trending
from ingestion.hn_fetcher import fetch_hn
from ingestion.reddit_fetcher import fetch_all_reddit
from ingestion.rss_fetcher import fetch_all_rss
from ingestion.youtube_rss import fetch_youtube
from processing.llm_client import generate_digest
from processing.prompt_builder import build_system_prompt, build_user_message
from utils.logger import get_logger, log


logger = get_logger("morning_brief")

LA = ZoneInfo("America/Los_Angeles")
MORNING_HOUR_LA = 6   # weekday 6 AM PT
EVENING_HOUR_LA = 21  # 9 PM PT, night before next trading day


async def _run_fetcher(name: str, coro) -> list[SourceResult]:
    """Execute one fetcher, log + return empty list on hard failure (never crash the run)."""
    try:
        result = await coro
    except Exception as e:
        log(logger, logging.ERROR, "fetcher_crashed", fetcher=name, error=str(e))
        return []
    if isinstance(result, list):
        return result
    return [result]


async def gather_all_sources() -> list[SourceResult]:
    lists = await asyncio.gather(
        _run_fetcher("rss", fetch_all_rss()),
        _run_fetcher("reddit", fetch_all_reddit()),
        _run_fetcher("hn", fetch_hn()),
        _run_fetcher("bluesky", fetch_bluesky()),
        _run_fetcher("github_trending", fetch_github_trending()),
        _run_fetcher("youtube", fetch_youtube()),
    )
    return [r for sub in lists for r in sub]


def detect_edition(now_la: datetime) -> str:
    """Morning before noon, evening after — used for prompt + subject framing."""
    return "evening" if now_la.hour >= 12 else "morning"


def is_scheduled_window(force: bool, now_la: datetime) -> tuple[bool, str | None]:
    """Decide whether this invocation should run, and which edition to produce.

    Cron fires at 4, 5, 13, 14 UTC Mon-Fri. Each pair covers one LA hour across
    PST/PDT. The gate then enforces the user's policy:
      * Morning digest: 6 AM PT, Mon-Fri only (skip Sat AM, skip Sun AM).
      * Evening digest: 9 PM PT, Sun-Thu only (skip Fri night, skip Sat night).
    Returns (should_run, edition).
    """
    if force or os.getenv("SKIP_TIME_GATE", "").lower() in {"1", "true"}:
        return True, detect_edition(now_la)
    weekday = now_la.weekday()  # Mon=0 ... Sun=6
    if now_la.hour == MORNING_HOUR_LA and weekday in (0, 1, 2, 3, 4):
        return True, "morning"
    if now_la.hour == EVENING_HOUR_LA and weekday in (6, 0, 1, 2, 3):
        return True, "evening"
    return False, None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Morning Brief Agent")
    p.add_argument("--dry-run", action="store_true", help="print digest to stdout; do not send email")
    p.add_argument("--force", action="store_true", help="run regardless of the LA time gate")
    p.add_argument("--edition", choices=["morning", "evening"], default=None,
                   help="override edition framing (defaults to time-of-day)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load()
    dry_run = args.dry_run or cfg.dry_run

    now_la = datetime.now(LA)
    should_run, gated_edition = is_scheduled_window(args.force, now_la)
    if not should_run:
        log(
            logger,
            logging.INFO,
            "skipped_outside_window",
            now_la=now_la.isoformat(),
            weekday=now_la.weekday(),
            hour=now_la.hour,
        )
        return 0

    edition = args.edition or gated_edition or detect_edition(now_la)
    log(logger, logging.INFO, "run_start", deployment=cfg.azure_openai_deployment, dry_run=dry_run, edition=edition)

    try:
        results = asyncio.run(gather_all_sources())
    except Exception as e:
        log(logger, logging.ERROR, "ingest_fatal", error=str(e))
        return 1

    ok = [r for r in results if not r.error and r.items]
    errored = [r for r in results if r.error]
    total_items = sum(len(r.items) for r in ok)
    log(
        logger,
        logging.INFO,
        "ingest_done",
        sources_ok=len(ok),
        sources_failed=len(errored),
        total_items=total_items,
    )
    for r in errored:
        log(logger, logging.WARNING, "source_failed", source=r.source_name, error=r.error)

    if total_items == 0:
        log(logger, logging.ERROR, "no_items_aborting")
        return 1

    user_msg = build_user_message(results, edition=edition)
    system_prompt = build_system_prompt(edition)
    try:
        digest = generate_digest(cfg, system_prompt, user_msg)
    except Exception as e:
        log(logger, logging.ERROR, "llm_failed", error=str(e))
        return 1
    log(logger, logging.INFO, "digest_generated", length=len(digest), edition=edition)

    if dry_run:
        print("=" * 72)
        print(digest)
        print("=" * 72)
        log(logger, logging.INFO, "dry_run_done")
        return 0

    try:
        mid = send_email(cfg, digest, edition=edition)
    except Exception as e:
        log(logger, logging.ERROR, "email_failed", error=str(e))
        return 1
    log(logger, logging.INFO, "email_sent", message_id=mid, edition=edition)
    return 0


if __name__ == "__main__":
    sys.exit(main())
