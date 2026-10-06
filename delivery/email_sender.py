"""Azure Communication Services Email delivery.

Rich HTML rendering lives in `email_formatter.build_html_body` — this module
just handles auth, recipient list, and the SDK calls. The plain-text body goes
as-is for mail clients that prefer it (or render HTML off).

Each recipient gets a separate send — their own address in To, nobody else's
visible. This is strictly better than BCC for deliverability against fresh
Azure-managed domains (`*.azurecomm.net`): BCC with a generic "To:" header
trips Gmail's bulk-mail heuristics and the message vanishes silently. One
message per recipient lets Gmail score each one on its own, and the recipient
still sees only their own address.
"""
from __future__ import annotations

from datetime import date

from azure.communication.email import EmailClient

from config import Config
from delivery.email_formatter import build_html_body


def _recipient_list(user_email: str) -> list[str]:
    """Split USER_EMAIL on comma so a single secret can carry multiple recipients."""
    return [addr.strip() for addr in user_email.split(",") if addr.strip()]


def send_email(cfg: Config, body: str, edition: str = "morning") -> str:
    """Send the digest to every address in USER_EMAIL — one message per recipient.

    Returns a comma-joined string of ACS message IDs. Raises on the first
    failure so the caller's `email_failed` log captures the offending recipient.
    """
    missing = [
        k for k, v in {
            "ACS_CONNECTION_STRING": cfg.acs_connection_string,
            "ACS_SENDER_ADDRESS": cfg.acs_sender_address,
            "USER_EMAIL": cfg.user_email,
        }.items() if not v
    ]
    if missing:
        raise RuntimeError(f"Missing ACS email config: {', '.join(missing)}")

    addresses = _recipient_list(cfg.user_email)
    if not addresses:
        raise RuntimeError("USER_EMAIL parsed to zero recipients")

    client = EmailClient.from_connection_string(cfg.acs_connection_string)
    subject_label = "Evening Brief" if edition == "evening" else "Morning Brief"
    subject = f"{subject_label} — {date.today().strftime('%B %d, %Y')}"
    html_body = build_html_body(body, edition=edition)

    message_ids: list[str] = []
    for addr in addresses:
        message = {
            "senderAddress": cfg.acs_sender_address,
            "recipients": {"to": [{"address": addr}]},
            "content": {
                "subject": subject,
                "plainText": body,
                "html": html_body,
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        status = result.get("status") if isinstance(result, dict) else getattr(result, "status", None)
        message_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", "")
        if status and str(status).lower() != "succeeded":
            raise RuntimeError(f"ACS email send failed for {addr}: status={status} id={message_id}")
        message_ids.append(message_id or "")
    return ",".join(message_ids)
