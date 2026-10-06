"""Scrape github.com/trending — public page, no auth required."""
from __future__ import annotations

import asyncio

from bs4 import BeautifulSoup

from config import load
from ingestion.base import Item, SourceResult, make_async_client, trim_items_to_word_cap
from sources import GITHUB_TRENDING_SOURCE_NAME


TOP_N = 10


async def fetch_github_trending() -> SourceResult:
    cfg = load()
    url = "https://github.com/trending"
    if cfg.github_trending_language:
        url = f"{url}/{cfg.github_trending_language}"

    async with make_async_client() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return SourceResult(source_name=GITHUB_TRENDING_SOURCE_NAME, section="tech", error=str(e))

    soup = BeautifulSoup(html, "html.parser")
    items: list[Item] = []
    for article in soup.select("article.Box-row")[:TOP_N]:
        heading = article.select_one("h2 a")
        if not heading:
            continue
        repo = " ".join(heading.get_text(strip=True).split())
        href = heading.get("href", "")
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""
        items.append(
            Item(
                title=repo,
                summary=description[:400],
                url=f"https://github.com{href}",
            )
        )

    return SourceResult(
        source_name=GITHUB_TRENDING_SOURCE_NAME,
        section="tech",
        items=trim_items_to_word_cap(items),
    )


if __name__ == "__main__":
    result = asyncio.run(fetch_github_trending())
    if result.error:
        print(f"[ERROR] {result.source_name}: {result.error}")
    else:
        print(f"[{result.source_name}] {len(result.items)} items")
        for item in result.items[:5]:
            print(f"  - {item.title[:80]}")
