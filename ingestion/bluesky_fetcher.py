"""Bluesky public API — getAuthorFeed for each handle. No auth for public posts."""
from __future__ import annotations

import asyncio

from config import load
from ingestion.base import Item, SourceResult, make_async_client, trim_items_to_word_cap
from sources import BLUESKY_SOURCE_NAME


POSTS_PER_AUTHOR = 5
API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"


async def _fetch_author(client, handle: str) -> list[Item]:
    try:
        resp = await client.get(API, params={"actor": handle, "limit": POSTS_PER_AUTHOR})
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    items: list[Item] = []
    for feed_entry in data.get("feed", []):
        post = feed_entry.get("post", {})
        record = post.get("record", {})
        text = (record.get("text") or "").strip()
        if not text:
            continue
        items.append(
            Item(
                title=f"@{handle}: {text[:120]}",
                summary=text[:500],
                url=f"https://bsky.app/profile/{handle}",
                published=record.get("createdAt", ""),
            )
        )
    return items


async def fetch_bluesky() -> SourceResult:
    cfg = load()
    if not cfg.bluesky_handles:
        return SourceResult(source_name=BLUESKY_SOURCE_NAME, section="tech")

    async with make_async_client() as client:
        lists = await asyncio.gather(*(_fetch_author(client, h) for h in cfg.bluesky_handles))

    flat = [item for sub in lists for item in sub]
    return SourceResult(
        source_name=BLUESKY_SOURCE_NAME,
        section="tech",
        items=trim_items_to_word_cap(flat),
    )


if __name__ == "__main__":
    result = asyncio.run(fetch_bluesky())
    if result.error:
        print(f"[ERROR] {result.source_name}: {result.error}")
    else:
        print(f"[{result.source_name}] {len(result.items)} items")
        for item in result.items[:3]:
            print(f"  - {item.title[:80]}")
