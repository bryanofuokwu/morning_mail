"""Hacker News Firebase API — get top story IDs, then fetch each story in parallel."""
from __future__ import annotations

import asyncio

from ingestion.base import Item, SourceResult, make_async_client, trim_items_to_word_cap
from sources import HN_SOURCE


TOP_N = 15  # fetch top 15 ids; trimmer will cut to word cap


async def _fetch_story(client, story_id: int) -> Item | None:
    try:
        resp = await client.get(f"{HN_SOURCE.endpoint}/item/{story_id}.json")
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception:
        return None
    title = (data.get("title") or "").strip()
    if not title:
        return None
    return Item(
        title=title,
        summary="",
        url=data.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
        published=str(data.get("time", "")),
    )


async def fetch_hn() -> SourceResult:
    async with make_async_client() as client:
        try:
            resp = await client.get(f"{HN_SOURCE.endpoint}/topstories.json")
            resp.raise_for_status()
            ids = resp.json()[:TOP_N]
        except Exception as e:
            return SourceResult(source_name=HN_SOURCE.name, section=HN_SOURCE.section, error=str(e))

        stories = await asyncio.gather(*(_fetch_story(client, sid) for sid in ids))

    items = [s for s in stories if s is not None]
    return SourceResult(
        source_name=HN_SOURCE.name,
        section=HN_SOURCE.section,
        items=trim_items_to_word_cap(items),
    )


if __name__ == "__main__":
    result = asyncio.run(fetch_hn())
    if result.error:
        print(f"[ERROR] {result.source_name}: {result.error}")
    else:
        print(f"[{result.source_name}] {len(result.items)} items")
        for item in result.items[:5]:
            print(f"  - {item.title[:80]}")
