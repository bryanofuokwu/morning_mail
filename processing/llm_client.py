"""Azure OpenAI client. Sends the assembled prompt and returns the digest text."""
from __future__ import annotations

from openai import AzureOpenAI

from config import Config


MAX_TOKENS = 3500  # Was 1500 (doc §4.3); raised so the digest reaches the DAILY VERSE section
                  # at the end. With 5+5+3 bullets averaging 80 words and a verse + reflection,
                  # 1500 truncated mid-verse-divider. 3500 leaves comfortable headroom.


def _build_client(cfg: Config) -> AzureOpenAI:
    missing = [
        k for k, v in {
            "AZURE_OPENAI_ENDPOINT": cfg.azure_openai_endpoint,
            "AZURE_OPENAI_API_KEY": cfg.azure_openai_api_key,
        }.items() if not v
    ]
    if missing:
        raise RuntimeError(f"Missing Azure OpenAI config: {', '.join(missing)}")
    return AzureOpenAI(
        azure_endpoint=cfg.azure_openai_endpoint,
        api_key=cfg.azure_openai_api_key,
        api_version=cfg.azure_openai_api_version,
    )


def generate_digest(cfg: Config, system_prompt: str, user_message: str) -> str:
    client = _build_client(cfg)
    response = client.chat.completions.create(
        model=cfg.azure_openai_deployment,
        max_completion_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return (response.choices[0].message.content or "").strip()
