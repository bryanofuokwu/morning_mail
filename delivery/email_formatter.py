"""Parse the plain-text digest and render a styled HTML email.

Inline styles + table layout only — Gmail / Outlook strip flexbox, grid, CSS
variables, and most class-based rules. The parser is defensive: if the digest
doesn't match the expected shape, `build_html_body` falls back to the original
monospace `<pre>` renderer so we never fail to send.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date


DIVIDER_RE = re.compile(r"^━━━\s*(\S+)\s+(.+?)\s*━━━\s*$")
BULLET_RE = re.compile(r"^•\s+(.*)$")
TOPIC_RE = re.compile(r"^\*\*(.+?)\*\*\s*[—\-–]\s*(.*)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


# Substring-matched so morning ("WHAT TO WATCH TODAY") and evening
# ("WHAT TO WATCH TOMORROW") share the same orange accent.
ACCENTS = (
    ("ECONOMY", "#16a34a"),
    ("TECH", "#2563eb"),
    ("WHAT TO WATCH", "#ea580c"),
    ("DAILY VERSE", "#b45309"),
)
DEFAULT_ACCENT = "#475569"


def _accent_for(label: str) -> str:
    upper = label.upper()
    for key, color in ACCENTS:
        if key in upper:
            return color
    return DEFAULT_ACCENT


@dataclass
class Bullet:
    topic: str
    body: str


@dataclass
class Section:
    emoji: str
    label: str
    kind: str  # "bullets" | "paragraph" | "verse"
    bullets: list[Bullet] = field(default_factory=list)
    paragraph: str = ""
    verse: str = ""
    reflection: str = ""


@dataclass
class Digest:
    title: str
    sections: list[Section]


def parse_digest(text: str) -> Digest:
    lines = [ln.rstrip() for ln in text.splitlines()]
    title = ""
    sections: list[Section] = []
    current: Section | None = None
    pending_bullet: Bullet | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        div = DIVIDER_RE.match(line)
        if div:
            if current and pending_bullet:
                current.bullets.append(pending_bullet)
                pending_bullet = None
            emoji, label = div.group(1), div.group(2).strip()
            label_upper = label.upper()
            if "DAILY VERSE" in label_upper:
                kind = "verse"
            elif "FOUNDER" in label_upper:  # legacy section, kept for safety
                kind = "paragraph"
            else:
                kind = "bullets"
            current = Section(emoji=emoji, label=label, kind=kind)
            sections.append(current)
            continue

        if current is None:
            if not title:
                title = line
            continue

        if line.startswith("(") and line.endswith(")"):
            continue

        if current.kind == "paragraph":
            current.paragraph = (current.paragraph + " " + line).strip() if current.paragraph else line
            continue

        if current.kind == "verse":
            # First non-empty line is the verse + citation; subsequent lines are the reflection.
            if not current.verse:
                current.verse = line
            else:
                current.reflection = (current.reflection + " " + line).strip() if current.reflection else line
            continue

        bullet_match = BULLET_RE.match(line)
        if bullet_match:
            if pending_bullet:
                current.bullets.append(pending_bullet)
            content = bullet_match.group(1).strip()
            topic, body = "", content
            topic_match = TOPIC_RE.match(content)
            if topic_match:
                topic, body = topic_match.group(1).strip(), topic_match.group(2).strip()
            pending_bullet = Bullet(topic=topic, body=body)
        elif pending_bullet:
            pending_bullet.body = (pending_bullet.body + " " + line).strip()

    if current and pending_bullet:
        current.bullets.append(pending_bullet)

    return Digest(title=title, sections=sections)


def _inline_bold(text: str) -> str:
    escaped = html.escape(text)
    return BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def _section_card(section: Section) -> str:
    accent = _accent_for(section.label)
    header = (
        f'<tr><td style="padding:22px 24px 12px 24px;">'
        f'<div style="font-size:11px;letter-spacing:1.5px;font-weight:700;color:{accent};'
        f'text-transform:uppercase;margin-bottom:4px;">{html.escape(section.emoji)} &nbsp;'
        f'{html.escape(section.label)}</div>'
        f'<div style="height:2px;background:{accent};border-radius:2px;width:32px;"></div>'
        f'</td></tr>'
    )

    if section.kind == "verse":
        # The model copies the user-supplied VERSE_LINE verbatim:
        #   "verse text..." — Book Ch:V (Translation)
        # Split into the quoted verse and the citation so each gets its own styling.
        m = re.match(r'^[“"\'](.*)[”"\']\s*[—\-–]\s*(.+)$', section.verse.strip())
        if m:
            verse_text, citation = m.group(1).strip(), m.group(2).strip()
        else:
            verse_text = section.verse.strip().strip('"').strip("'")
            citation = ""

        citation_html = (
            f'<div style="font-size:13px;color:#92400e;text-align:right;'
            f'margin-top:10px;font-style:normal;letter-spacing:0.3px;">'
            f'— {html.escape(citation)}</div>'
            if citation else ""
        )
        body = (
            f'<tr><td style="padding:12px 24px 22px 24px;">'
            f'<blockquote style="margin:0 0 16px 0;padding:14px 20px;'
            f'border-left:3px solid {accent};font-style:italic;color:#374151;'
            f'font-size:16px;line-height:1.65;background:#fffaf2;border-radius:0 8px 8px 0;">'
            f'{_inline_bold(verse_text)}'
            f'{citation_html}'
            f'</blockquote>'
            f'<p style="margin:0;font-size:15px;line-height:1.65;color:#1f2937;">'
            f'{_inline_bold(section.reflection)}</p>'
            f'</td></tr>'
        )
    elif section.kind == "paragraph":
        body = (
            f'<tr><td style="padding:12px 24px 24px 24px;">'
            f'<p style="margin:0;font-size:15px;line-height:1.65;color:#1f2937;">'
            f'{_inline_bold(section.paragraph)}</p></td></tr>'
        )
    else:
        rows = []
        for b in section.bullets:
            topic_html = (
                f'<span style="font-weight:700;color:#0f172a;">{_inline_bold(b.topic)}</span> '
                f'<span style="color:#64748b;">·</span> '
                if b.topic else ""
            )
            rows.append(
                f'<tr>'
                f'<td valign="top" style="padding:8px 12px 8px 0;width:10px;">'
                f'<div style="width:6px;height:6px;border-radius:50%;background:{accent};'
                f'margin-top:8px;"></div></td>'
                f'<td valign="top" style="padding:6px 0;font-size:15px;line-height:1.6;color:#1f2937;">'
                f'{topic_html}{_inline_bold(b.body)}</td>'
                f'</tr>'
            )
        bullets_table = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="border-collapse:collapse;">'
            + "".join(rows)
            + "</table>"
        )
        body = f'<tr><td style="padding:8px 24px 20px 24px;">{bullets_table}</td></tr>'

    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="border-collapse:separate;background:#ffffff;border:1px solid #e5e7eb;'
        'border-radius:14px;margin:0 0 16px 0;box-shadow:0 1px 2px rgba(15,23,42,0.04);">'
        + header + body +
        '</table>'
    )


def render_rich_html(digest: Digest, edition: str = "morning") -> str:
    today_label = date.today().strftime("%A · %B %d, %Y")
    fallback_title = "📰 EVENING BRIEF" if edition == "evening" else "📰 MORNING BRIEF"
    title_line = html.escape(digest.title) if digest.title else fallback_title
    page_title = "Evening Brief" if edition == "evening" else "Morning Brief"
    tagline = (
        "Tomorrow's setup before you sleep. Curated at 9 PM PT."
        if edition == "evening"
        else "Signal over noise. Curated at 6 AM PT."
    )

    sections_html = "".join(_section_card(s) for s in digest.sections)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
</head>
<body style="margin:0;padding:0;background:#f6f7fb;-webkit-font-smoothing:antialiased;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f6f7fb;">
  <tr><td align="center" style="padding:32px 16px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;width:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
      <tr><td style="padding:0 4px 20px 4px;">
        <div style="font-size:11px;letter-spacing:2px;font-weight:700;color:#64748b;text-transform:uppercase;">{html.escape(today_label)}</div>
        <div style="font-size:28px;font-weight:800;color:#0f172a;margin-top:6px;line-height:1.2;">{title_line}</div>
        <div style="font-size:14px;color:#64748b;margin-top:6px;">{html.escape(tagline)}</div>
      </td></tr>
      <tr><td>{sections_html}</td></tr>
      <tr><td style="padding:16px 4px 0 4px;font-size:12px;color:#94a3b8;line-height:1.6;">
        Generated {html.escape(today_label)} · Powered by GPT-5.4 &amp; Azure Communication Services.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""


def _monospace_fallback(text: str) -> str:
    escaped = html.escape(text)
    return (
        "<!DOCTYPE html><html><body style=\"margin:0;padding:24px;"
        "background:#0b0d10;color:#e6edf3;\">"
        "<pre style=\"font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
        "font-size:14px;line-height:1.55;white-space:pre-wrap;word-wrap:break-word;"
        "margin:0;\">"
        f"{escaped}"
        "</pre></body></html>"
    )


def build_html_body(digest_text: str, edition: str = "morning") -> str:
    """Primary entry point. Rich HTML on success, monospace fallback on parse failure."""
    try:
        digest = parse_digest(digest_text)
        if digest.sections and any(
            (s.bullets or s.paragraph or s.verse) for s in digest.sections
        ):
            return render_rich_html(digest, edition=edition)
    except Exception:
        pass
    return _monospace_fallback(digest_text)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sample = """📰 MORNING BRIEF — April 24, 2026

━━━ 💰 ECONOMY & MARKETS ━━━
• **Hormuz oil shock** — Brent crude jumped 8% to $94 after escalation near the Strait of Hormuz; futures curve backwardated through Q3. Expect energy-sensitive SaaS budgets to tighten first.
• **Fed minutes** — FOMC signaled one more cut is off the table if CPI re-accelerates. Rate-sensitive growth names got hit, but AI-infra cohort held the bid.
• **Meta layoffs** — 6% cut across non-AI orgs. Capex unchanged at $62B — confirms the "AI is the only line item" thesis for 2026.

━━━ 🚀 TECH & AI ━━━
• **DeepSeek V4 release** — Open-weights 685B MoE at GPT-5.4 parity on MMLU-Pro and SWE-bench. MIT license. Self-host cost ~$0.40 per 1M tokens on 8×H200.
• **Anthropic connectors GA** — Claude can now call any MCP server by URL with per-tool auth. Dev tooling surface for agents just doubled overnight.
• **Qwen in cars** — Tesla + Geely signed multi-year deals for in-vehicle LLMs. Automotive becomes the next edge inference battleground.

━━━ 🔥 WHAT TO WATCH TODAY ━━━
• **Earnings** — MSFT after close. AI revenue breakout is the tell.
• **Fed speaker** — Powell at 2 PM ET, first post-minutes comment.
• **GitHub** — deepseek-ai/V4 just passed vercel/next.js on daily stars.

━━━ 📖 DAILY VERSE ━━━
"For we walk by faith, not by sight." — 2 Corinthians 5:7

Most decisions worth making sit in the fog — partial data, no guaranteed outcome, real cost if you're wrong. Walking by faith isn't ignoring the evidence; it's choosing to keep moving on the values and people you trust when the spreadsheet runs out of certainty. The alternative — refusing to move until you can see everything — is its own kind of failure.
"""
    out_path = Path("/tmp/preview.html")
    out_path.write_text(build_html_body(sample))
    sys.stdout.write(f"wrote {out_path}\n")
