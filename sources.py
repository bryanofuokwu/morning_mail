"""The 26 free sources, organized by section and fetcher kind.

Section labels feed the prompt: "ECONOMY & MARKETS" vs "TECH & AI".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Section = Literal["economy", "tech"]
Kind = Literal["rss", "reddit", "hn", "bluesky", "github_trending", "youtube_rss"]


@dataclass(frozen=True)
class Source:
    name: str
    section: Section
    kind: Kind
    endpoint: str


RSS_SOURCES: list[Source] = [
    # --- Economy (10 RSS) ---
    Source("Bloomberg", "economy", "rss", "https://feeds.bloomberg.com/markets/news.rss"),
    Source("Reuters Business", "economy", "rss", "https://feeds.reuters.com/reuters/businessNews"),
    Source("CNBC", "economy", "rss", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    Source("MarketWatch", "economy", "rss", "https://www.marketwatch.com/rss/topstories"),
    Source("Yahoo Finance", "economy", "rss", "https://finance.yahoo.com/news/rssindex"),
    Source("AP Business News", "economy", "rss", "https://feeds.apnews.com/rss/business"),
    Source("Federal Reserve", "economy", "rss", "https://www.federalreserve.gov/feeds/press_all.xml"),
    Source("The Economist", "economy", "rss", "https://www.economist.com/finance-and-economics/rss.xml"),
    Source("Planet Money (NPR)", "economy", "rss", "https://feeds.npr.org/510289/podcast.xml"),
    Source("Axios", "economy", "rss", "https://www.axios.com/feeds/feed.rss"),
    # --- Tech (8 RSS) ---
    Source("The Verge", "tech", "rss", "https://www.theverge.com/rss/index.xml"),
    Source("Ars Technica", "tech", "rss", "https://feeds.arstechnica.com/arstechnica/index"),
    Source("TechCrunch", "tech", "rss", "https://techcrunch.com/feed/"),
    Source("WIRED", "tech", "rss", "https://www.wired.com/feed/rss"),
    Source("MIT Technology Review", "tech", "rss", "https://feeds.feedburner.com/mit-technology-review"),
    Source("a16z Blog", "tech", "rss", "https://a16z.com/feed/"),
    Source("Platformer", "tech", "rss", "https://www.platformer.news/feed"),
    Source("Product Hunt", "tech", "rss", "https://www.producthunt.com/feed"),
    # --- Tech: research & practitioner layer (added v3) ---
    Source("arXiv cs.AI", "tech", "rss", "http://export.arxiv.org/rss/cs.AI"),
    Source("arXiv cs.LG", "tech", "rss", "http://export.arxiv.org/rss/cs.LG"),
    Source("Simon Willison", "tech", "rss", "https://simonwillison.net/atom/everything/"),
    Source("Hugging Face Blog", "tech", "rss", "https://huggingface.co/blog/feed.xml"),
]

REDDIT_SOURCES: list[Source] = [
    Source("r/economics", "economy", "reddit", "economics"),
    Source("r/investing", "economy", "reddit", "investing"),
    Source("r/MachineLearning", "tech", "reddit", "MachineLearning"),
    Source("r/technology", "tech", "reddit", "technology"),
    Source("r/LocalLLaMA", "tech", "reddit", "LocalLLaMA"),
]

HN_SOURCE = Source("Hacker News", "tech", "hn", "https://hacker-news.firebaseio.com/v0")
BLUESKY_SOURCE_NAME = "Bluesky (tech voices)"
GITHUB_TRENDING_SOURCE_NAME = "GitHub Trending"
YOUTUBE_SOURCE_NAME = "YouTube (tech channels)"


def all_sources_for_summary() -> list[tuple[str, Section]]:
    """Flat list of every source name+section for logging and dashboards."""
    out: list[tuple[str, Section]] = [(s.name, s.section) for s in RSS_SOURCES + REDDIT_SOURCES]
    out.append((HN_SOURCE.name, HN_SOURCE.section))
    out.append((BLUESKY_SOURCE_NAME, "tech"))
    out.append((GITHUB_TRENDING_SOURCE_NAME, "tech"))
    out.append((YOUTUBE_SOURCE_NAME, "tech"))
    return out
