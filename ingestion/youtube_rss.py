"""YouTube channel RSS feeds — same feedparser-compatible format as regular RSS."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from html import unescape
import re

import feedparser

from config import load
from ingestion.base import Item, SourceResult, USER_AGENT, trim_items_to_word_cap
from sources import YOUTUBE_SOURCE_NAME


PER_CHANNEL = 3
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return unescape(_TAG_RE.sub("", text)).strip()


def _parse_channel(channel_id: str) -> list[Item]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    parsed = feedparser.parse(url, agent=USER_AGENT)
    items: list[Item] = []
    author = getattr(parsed.feed, "title", channel_id)
    for entry in parsed.entries[:PER_CHANNEL]:
        title = _clean(getattr(entry, "title", ""))
        if not title:
            continue
        items.append(
            Item(
                title=f"{author}: {title}",
                summary=_clean(getattr(entry, "summary", ""))[:300],
                url=getattr(entry, "link", ""),
                published=getattr(entry, "published", ""),
            )
        )
    return items


async def fetch_youtube() -> SourceResult:
    cfg = load()
    if not cfg.youtube_channel_ids:
        return SourceResult(source_name=YOUTUBE_SOURCE_NAME, section="tech")

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        lists = await asyncio.gather(
            *(loop.run_in_executor(pool, _parse_channel, cid) for cid in cfg.youtube_channel_ids)
        )

    flat = [item for sub in lists for item in sub]
    return SourceResult(
        source_name=YOUTUBE_SOURCE_NAME,
        section="tech",
        items=trim_items_to_word_cap(flat),
    )


if __name__ == "__main__":
    result = asyncio.run(fetch_youtube())
    if result.error:
        print(f"[ERROR] {result.source_name}: {result.error}")
    else:
        print(f"[{result.source_name}] {len(result.items)} items")
        for item in result.items[:3]:
            print(f"  - {item.title[:80]}")
