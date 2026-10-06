"""Loads secrets from Azure Key Vault with env-var fallback for local dev."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_openai_api_version: str
    # Azure Communication Services (Email)
    acs_connection_string: str
    acs_sender_address: str
    user_email: str
    # Sources
    bluesky_handles: list[str]
    youtube_channel_ids: list[str]
    github_trending_language: str
    # Runtime
    dry_run: bool


def _from_keyvault(name: str) -> str | None:
    kv_url = os.getenv("KEY_VAULT_URL")
    if not kv_url:
        return None
    client = _kv_client(kv_url)
    # Key Vault secret names only allow [0-9a-zA-Z-]; FOO_BAR is stored as FOO-BAR.
    kv_name = name.replace("_", "-")
    try:
        return client.get_secret(kv_name).value
    except Exception:
        return None


@lru_cache(maxsize=1)
def _kv_client(kv_url: str):
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    return SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())


def _get(name: str, default: str | None = None) -> str | None:
    return _from_keyvault(name) or os.getenv(name) or default


@lru_cache(maxsize=1)
def load() -> Config:
    handles = _get("BLUESKY_HANDLES", "karpathy.bsky.social,emollick.bsky.social,benedictevans.bsky.social")
    channels = _get("YOUTUBE_CHANNEL_IDS", "UCBJycsmduvYEL83R_U4JriQ")
    return Config(
        azure_openai_endpoint=_get("AZURE_OPENAI_ENDPOINT", "") or "",
        azure_openai_api_key=_get("AZURE_OPENAI_API_KEY", "") or "",
        azure_openai_deployment=_get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4") or "gpt-5.4",
        azure_openai_api_version=_get("AZURE_OPENAI_API_VERSION", "2024-10-21") or "2024-10-21",
        acs_connection_string=_get("ACS_CONNECTION_STRING", "") or "",
        acs_sender_address=_get("ACS_SENDER_ADDRESS", "") or "",
        user_email=_get("USER_EMAIL", "") or "",
        bluesky_handles=[h.strip() for h in handles.split(",") if h.strip()],
        youtube_channel_ids=[c.strip() for c in channels.split(",") if c.strip()],
        github_trending_language=_get("GITHUB_TRENDING_LANGUAGE", "") or "",
        dry_run=os.getenv("DRY_RUN", "").lower() in {"1", "true", "yes"},
    )
