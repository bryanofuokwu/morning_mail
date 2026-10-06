"""Reddit public JSON — no auth, but requires a descriptive User-Agent."""
from __future__ import annotations

import asyncio

from ingestion.base import Item, SourceResult, make_async_client, trim_items_to_word_cap
from sources import REDDIT_SOURCES, Source


POSTS_PER_SUB = 5


async def _fetch_one(client, source: Source) -> SourceResult:
    url = f"https://www.reddit.com/r/{source.endpoint}/top.json?limit={POSTS_PER_SUB}&t=day"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return SourceResult(source_name=source.name, section=source.section, error=str(e))

    items: list[Item] = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title", "").strip()
        if not title:
            continue
        items.append(
            Item(
                title=title,
                summary=(post.get("selftext") or "")[:500].strip(),
                url=f"https://reddit.com{post.get('permalink', '')}",
                published=str(post.get("created_utc", "")),
            )
        )

    return SourceResult(
        source_name=source.name,
        section=source.section,
        items=trim_items_to_word_cap(items),
    )


async def fetch_all_reddit() -> list[SourceResult]:
    async with make_async_client() as client:
        return await asyncio.gather(*(_fetch_one(client, s) for s in REDDIT_SOURCES))


if __name__ == "__main__":
    results = asyncio.run(fetch_all_reddit())
    for r in results:
        if r.error:
            print(f"[ERROR] {r.source_name}: {r.error}")
        else:
            print(f"[{r.source_name}] {len(r.items)} items")
            for item in r.items[:2]:
                print(f"  - {item.title[:80]}")
