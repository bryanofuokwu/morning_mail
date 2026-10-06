"""Assembles source content into the prompt.

System prompt is adapted from doc §4.2 but rewritten to stop GPT echoing the
format-description as literal output.
"""
from __future__ import annotations

from datetime import date

from delivery.verses import format_verse_line, todays_verse
from ingestion.base import SourceResult


_SYSTEM_PROMPT_TEMPLATE = """You are a senior analyst and editorial director producing {EDITION_ARTICLE} {EDITION_LOWER} intelligence digest for a tech entrepreneur and investor. Be direct, opinionated, specific. Signal over noise. Never pad.

{EDITION_FRAMING}

Output the digest in EXACTLY this template, replacing the placeholders in ALL CAPS with real content from the user's source feed. Keep every divider, emoji, and bullet character identical to what is shown below.

📰 {EDITION_UPPER} BRIEF — {{DATE}}

━━━ 💰 ECONOMY & MARKETS ━━━
• **TOPIC_LABEL** — One sentence on what happened, then one short sentence on what it means for a tech entrepreneur. Total bullet length: 40-60 words. No third sentence.
• **TOPIC_LABEL** — ...
(3 to 5 bullets total. Lead with the most market-moving item.)

━━━ 🚀 TECH & AI ━━━
• **PAPER_OR_RELEASE_OR_TECHNIQUE** — One sentence stating the concrete technical claim with specifics: paper / repo / model name, the architecture or technique (e.g. MoE, GraphRAG, sparse attention, KV-cache trick, new fine-tuning method), key numbers (parameter count, benchmark score, context length, license), and who's behind it. One follow-up sentence on what it unlocks technically — what problem it actually solves, what it beats, or who needs to read it today. 40-70 words per bullet.
(4 to 5 bullets, REQUIRED depth. Pull HEAVILY from arXiv cs.AI, arXiv cs.LG, Hugging Face Blog, Simon Willison, r/LocalLLaMA, Hacker News technical posts, GitHub Trending. At least 2 bullets must reference a specific paper / preprint / new model / new technique by name. Acceptable: new architectures, novel training methods, retrieval techniques like GraphRAG, agent frameworks, open-weights releases with architecture details, benchmark-shifting results, OS-level dev tools, novel attention variants, quantization methods, inference optimizations. NOT acceptable in this section: IPOs, funding rounds, earnings, license/seat-count enterprise stories, executive moves, regulatory news, layoffs, consumer hardware announcements unless they ship a new technical primitive. Those belong in ECONOMY & MARKETS. If you can't find a concrete technical claim — paper name, model size, benchmark number, technique name, repo name — skip the bullet, don't fill space with business news. Be specific: name the authors, the lab, the score, the license. "OpenAI ships X" is not enough; "OpenAI's Codex now uses tool-interleaved reasoning via /v1/responses (multi-turn function calling preserved across reasoning steps); replaces single-shot tool-use for GPT-5-class models" is the bar.)

━━━ 🔥 {WATCH_HEADER} ━━━
• **ITEM** — one-line description (under 25 words)
({WATCH_GUIDANCE})

━━━ 📖 DAILY VERSE ━━━
<COPY THE EXACT VERSE_LINE PROVIDED IN THE USER MESSAGE HERE — DO NOT PARAPHRASE, DO NOT TRANSLATE, DO NOT CHANGE A WORD OR PUNCTUATION MARK>

REFLECTION (exactly 3 sentences). Do NOT restate or summarize the verse. Use it as a lens on a concrete, recognizable real-life situation — examples: deciding under uncertainty, handling a hard conversation, fatigue, fear of irrelevance, envy at someone else's win, parenting a tired kid, conflict with a co-founder or sibling, the discipline of showing up when nobody's watching. If today's news naturally connects, use it. End the third sentence with a practical takeaway the reader can carry into the next few hours. Speak directly ("you", not "we"). No preaching, no clichés, no "as a founder" / "as a leader" / "as believers" framings.

Formatting rules:
- Replace {{DATE}} with today's date in the form "Month DD, YYYY".
- Replace every TOPIC_LABEL / ITEM placeholder with the real subject.
- For the DAILY VERSE section: the VERSE_LINE in the user message is the canonical source — copy it verbatim as the first non-divider line. Then a single blank line. Then the 3-sentence reflection. Never invent or substitute a different verse.
- Do NOT output the parenthetical guidance lines — those are instructions for you, not content.
- Plain text only. No markdown headings. Keep the ━━━ divider lines exactly as shown. The output is wrapped in a monospace email block, so whitespace and Unicode characters render as-is."""


_MORNING_FRAMING = "Frame everything for someone reading at 6 AM Pacific before the US trading day opens — what happened overnight, what's hitting the tape today, and what to act on this morning."
_EVENING_FRAMING = "Frame everything for someone reading at 9 PM Pacific the night before — what closed today, and most importantly what to watch tomorrow in markets, tech, and policy. Bias the analysis toward forward-looking signals the reader can sleep on and act on first thing tomorrow."


def build_system_prompt(edition: str = "morning") -> str:
    edition = "evening" if edition == "evening" else "morning"
    if edition == "evening":
        return _SYSTEM_PROMPT_TEMPLATE.format(
            EDITION_ARTICLE="an",
            EDITION_LOWER="evening",
            EDITION_UPPER="EVENING",
            EDITION_FRAMING=_EVENING_FRAMING,
            WATCH_HEADER="WHAT TO WATCH TOMORROW",
            WATCH_GUIDANCE="2-3 items: tomorrow's scheduled events, earnings, data releases, or developing stories likely to move markets at the open.",
        )
    return _SYSTEM_PROMPT_TEMPLATE.format(
        EDITION_ARTICLE="a",
        EDITION_LOWER="morning",
        EDITION_UPPER="MORNING",
        EDITION_FRAMING=_MORNING_FRAMING,
        WATCH_HEADER="WHAT TO WATCH TODAY",
        WATCH_GUIDANCE="2-3 items: scheduled events, earnings, regulatory decisions, developing stories breaking today.",
    )


# Backwards-compat: the morning prompt is the historical default exposed as SYSTEM_PROMPT.
SYSTEM_PROMPT = build_system_prompt("morning")


def build_user_message(results: list[SourceResult], today: date | None = None, edition: str = "morning") -> str:
    """Stitch all fetched items into a single user message, grouped by section."""
    today = today or date.today()
    econ = [r for r in results if r.section == "economy" and r.items]
    tech = [r for r in results if r.section == "tech" and r.items]
    errors = [r for r in results if r.error]

    edition_label = "EVENING BRIEF" if edition == "evening" else "MORNING BRIEF"
    verse_line = format_verse_line(todays_verse(today))
    lines: list[str] = [
        f"Today's date: {today.strftime('%B %d, %Y')}",
        "",
        "VERSE_LINE for today's DAILY VERSE section (copy this line VERBATIM, do not change a single character):",
        verse_line,
        "",
        f"Source feed follows. Produce the {edition_label} per your system prompt template.",
        "",
        "=== ECONOMY & BUSINESS SOURCES ===",
    ]
    lines.extend(_format_section(econ))
    lines.append("")
    lines.append("=== TECH & AI SOURCES ===")
    lines.extend(_format_section(tech))

    if errors:
        lines.append("")
        lines.append(f"(Note: {len(errors)} source(s) failed to fetch and are omitted.)")

    return "\n".join(lines)


def _format_section(results: list[SourceResult]) -> list[str]:
    out: list[str] = []
    for r in results:
        out.append("")
        out.append(f"--- {r.source_name} ---")
        for item in r.items:
            title = item.title.strip()
            line = f"• {title}"
            if item.summary and item.summary.strip() and item.summary.strip() != title:
                line += f" — {item.summary.strip()[:300]}"
            out.append(line)
    return out
