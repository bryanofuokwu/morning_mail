"""Shared types + HTTP client + word-cap trimmer for all fetchers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import httpx

USER_AGENT = "morning-brief-agent/1.0 (personal digest; contact: local)"
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_RETRIES = 2
PER_SOURCE_WORD_CAP = 600  # doc §4.3


@dataclass
class Item:
    """A single piece of content from any source."""

    title: str
    summary: str = ""
    url: str = ""
    published: str = ""  # ISO8601 string or empty


@dataclass
class SourceResult:
    """What a fetcher returns for one source."""

    source_name: str
    section: Literal["economy", "tech"]
    items: list[Item] = field(default_factory=list)
    error: str | None = None


def make_async_client() -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(retries=MAX_RETRIES)
    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


def trim_items_to_word_cap(items: list[Item], cap: int = PER_SOURCE_WORD_CAP) -> list[Item]:
    """Keep newest-first order, drop items once the running word count exceeds cap."""
    kept: list[Item] = []
    words_used = 0
    for item in items:
        words = len((item.title + " " + item.summary).split())
        if words_used + words > cap and kept:
            break
        kept.append(item)
        words_used += words
    return kept
