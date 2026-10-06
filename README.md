# Morning Brief Agent

Pulls 26 free sources (RSS, Reddit, Hacker News, Bluesky, GitHub Trending, YouTube) at 6 AM PST, runs the aggregated content through **Azure OpenAI (GPT-5.4)**, and delivers a structured digest via **Azure Communication Services Email** at ~6:30 AM.

Built to the spec in `morning_brief_free_sources.pdf`. Source registry is in [sources.py](sources.py).

## Local dev

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp deploy/secrets-template.env .env
# Fill in AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY at minimum.
# For a real email send, also fill in ACS_CONNECTION_STRING, ACS_SENDER_ADDRESS, USER_EMAIL.
```

### Smoke-test one fetcher

```bash
python -m ingestion.rss_fetcher
python -m ingestion.reddit_fetcher
python -m ingestion.hn_fetcher
python -m ingestion.bluesky_fetcher
python -m ingestion.github_trending
python -m ingestion.youtube_rss
```

### End-to-end, print-only (no email)

```bash
python main.py --dry-run --force
```

`--force` bypasses the "only run at 6 AM LA" time gate.

### End-to-end with a real email

```bash
python main.py --force   # ACS_* creds + USER_EMAIL must be in .env
```

## Deploy to Azure

```bash
cp deploy/secrets-template.env deploy/secrets.env
# Fill in (or leave AZURE_OPENAI_* / ACS_CONNECTION_STRING blank — the script
# will provision those resources and derive the values itself).
az login
./deploy/deploy.sh
```

The script provisions, in your subscription:
- Resource group `morning-brief-rg`
- Container Registry, builds + pushes the image
- **Azure OpenAI** resource (creates the resource; you deploy the `gpt-5.4` model inside it — one-time portal click)
- **Azure Communication Services + Email** resources, with an Azure-managed domain linked automatically
- Key Vault with all secrets
- Log Analytics workspace
- User-assigned managed identity with Key Vault `get` permission
- Container Apps Job with cron `0 13,14 * * *` UTC (6 AM PDT + 6 AM PST; `main.py` no-ops the off-hour slot)

Set `PROVISION_AOAI=0` or `PROVISION_ACS=0` before running the script if you already created either resource yourself.

### After the script finishes — two manual clicks

The script prints these at the end:

1. **Deploy the `gpt-5.4` model inside the OpenAI resource**
   Portal → `morning-brief-ai` → Model deployments → Create new, pick `gpt-5.4`, name it `gpt-5.4`.

2. **Set the recipient email in Key Vault**
   ```bash
   az keyvault secret set --vault-name morning-brief-kv --name USER_EMAIL --value 'you@example.com'
   ```
   The sender address (`DoNotReply@<guid>.azurecomm.net`) is derived from the Azure-managed domain that `deploy.sh` already provisioned and linked.

### Manual test run after deploy

```bash
az containerapp job start -g morning-brief-rg -n morning-brief-job
az containerapp job execution list -g morning-brief-rg -n morning-brief-job -o table
```

## Config knobs

| Env var | Default | Purpose |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | — | e.g. `https://morning-brief-ai.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | — | Key from the Azure OpenAI resource |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-5.4` | The deployment name you chose when deploying the model |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | Bump to the version required by your chosen model |
| `ACS_CONNECTION_STRING` | — | From ACS resource > Keys |
| `ACS_SENDER_ADDRESS` | — | `DoNotReply@<guid>.azurecomm.net` (from the Email domain linked to ACS) |
| `USER_EMAIL` | — | Recipient email address |
| `BLUESKY_HANDLES` | Karpathy / Mollick / Evans | Comma-separated Bluesky handles |
| `YOUTUBE_CHANNEL_IDS` | MKBHD (placeholder) | To find yours: visit the channel's page, view source, grep for `"channelId":"UC…"` |
| `GITHUB_TRENDING_LANGUAGE` | (all) | E.g. `python`, `rust`, `typescript` |
| `KEY_VAULT_URL` | unset (local) | When set, secrets come from Key Vault; else env/`.env` |
| `SKIP_TIME_GATE` | `false` | Bypass the 6-AM-LA gate (for in-job manual tests) |

## Layout

```
morning_mail/
├── main.py                    # orchestrator (ingest → LLM → SMS)
├── config.py                  # Key Vault + env loader
├── sources.py                 # the 26 sources
├── ingestion/                 # 6 fetchers (RSS, Reddit, HN, Bluesky, GitHub, YouTube)
├── processing/                # prompt_builder + llm_client (Azure OpenAI)
├── delivery/email_sender.py   # Azure Communication Services Email
├── utils/logger.py            # JSON logs → Azure Log Analytics
├── deploy/deploy.sh           # az CLI one-shot
└── Dockerfile
```

## Known: 4 dead sources

These 4 endpoints from the spec doc fail at runtime. The pipeline logs + skips them, so you still get 22 working sources:

- **Reuters** (`feeds.reuters.com/reuters/businessNews`) — DNS doesn't resolve; feed was retired
- **AP Business** (`feeds.apnews.com/rss/business`) — DNS doesn't resolve
- **MIT Technology Review** (Feedburner URL) — returns invalid XML
- **a16z** (`a16z.com/feed/`) — returns invalid XML, likely bot-blocked

Replacements welcome in [sources.py](sources.py).
