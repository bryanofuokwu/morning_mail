"""Fetches all 18 RSS feeds (plus YouTube channel feeds — same format) in parallel."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from html import unescape
import re

import feedparser

from ingestion.base import Item, SourceResult, USER_AGENT, trim_items_to_word_cap
from sources import RSS_SOURCES, Source


MAX_ITEMS_PER_FEED = 10

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(_TAG_RE.sub("", text)).strip()


def _parse_feed(source: Source) -> SourceResult:
    parsed = feedparser.parse(source.endpoint, agent=USER_AGENT)
    if parsed.bozo and not parsed.entries:
        return SourceResult(
            source_name=source.name,
            section=source.section,
            error=f"feedparser bozo: {parsed.bozo_exception!r}",
        )

    items: list[Item] = []
    for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
        title = _clean(getattr(entry, "title", ""))
        if not title:
            continue
        summary = _clean(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        items.append(
            Item(
                title=title,
                summary=summary[:500],
                url=getattr(entry, "link", ""),
                published=getattr(entry, "published", "") or getattr(entry, "updated", ""),
            )
        )

    return SourceResult(
        source_name=source.name,
        section=source.section,
        items=trim_items_to_word_cap(items),
    )


async def fetch_all_rss() -> list[SourceResult]:
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=8) as pool:
        return await asyncio.gather(
            *(loop.run_in_executor(pool, _parse_feed, src) for src in RSS_SOURCES)
        )


if __name__ == "__main__":
    results = asyncio.run(fetch_all_rss())
    for r in results:
        if r.error:
            print(f"[ERROR] {r.source_name}: {r.error}")
        else:
            print(f"[{r.source_name}] {len(r.items)} items")
            for item in r.items[:2]:
                print(f"  - {item.title[:80]}")
