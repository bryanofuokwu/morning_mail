"""Curated rotation of canonical NIV verses for the DAILY VERSE section.

The verse text and citation are hand-picked so the LLM never has to recall
scripture from memory — it just renders the verse verbatim and writes the
reflection underneath. This eliminates hallucinated chapter/verse references
and paraphrased text.

Selection is deterministic by date.toordinal() % len(VERSES), so morning and
evening editions on the same calendar day share a verse (different reflections
naturally — the news context differs).

Source: NIV. Verses chosen for wide canonical coverage and unambiguous,
widely-memorized wording. Multi-verse spans (e.g. "Psalm 23:1-3") are quoted
inline with the citation reflecting the range.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Verse:
    ref: str            # e.g. "Romans 8:28"
    text: str           # verse text, no surrounding quote marks
    translation: str = "NIV"


VERSES: list[Verse] = [
    # --- Old Testament ---
    Verse(
        "Genesis 50:20",
        "You intended to harm me, but God intended it for good to accomplish what is now being done, the saving of many lives.",
    ),
    Verse(
        "Exodus 14:14",
        "The LORD will fight for you; you need only to be still.",
    ),
    Verse(
        "Deuteronomy 31:6",
        "Be strong and courageous. Do not be afraid or terrified because of them, for the LORD your God goes with you; he will never leave you nor forsake you.",
    ),
    Verse(
        "Joshua 1:9",
        "Have I not commanded you? Be strong and courageous. Do not be afraid; do not be discouraged, for the LORD your God will be with you wherever you go.",
    ),
    Verse(
        "1 Samuel 16:7",
        "The LORD does not look at the things people look at. People look at the outward appearance, but the LORD looks at the heart.",
    ),
    Verse(
        "Psalm 23:1",
        "The LORD is my shepherd, I lack nothing.",
    ),
    Verse(
        "Psalm 27:1",
        "The LORD is my light and my salvation — whom shall I fear? The LORD is the stronghold of my life — of whom shall I be afraid?",
    ),
    Verse(
        "Psalm 34:18",
        "The LORD is close to the brokenhearted and saves those who are crushed in spirit.",
    ),
    Verse(
        "Psalm 46:1",
        "God is our refuge and strength, an ever-present help in trouble.",
    ),
    Verse(
        "Psalm 46:10",
        "Be still, and know that I am God; I will be exalted among the nations, I will be exalted in the earth.",
    ),
    Verse(
        "Psalm 51:10",
        "Create in me a pure heart, O God, and renew a steadfast spirit within me.",
    ),
    Verse(
        "Psalm 119:105",
        "Your word is a lamp for my feet, a light on my path.",
    ),
    Verse(
        "Psalm 139:14",
        "I praise you because I am fearfully and wonderfully made; your works are wonderful, I know that full well.",
    ),
    Verse(
        "Proverbs 3:5-6",
        "Trust in the LORD with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight.",
    ),
    Verse(
        "Proverbs 16:9",
        "In their hearts humans plan their course, but the LORD establishes their steps.",
    ),
    Verse(
        "Proverbs 27:17",
        "As iron sharpens iron, so one person sharpens another.",
    ),
    Verse(
        "Ecclesiastes 3:1",
        "There is a time for everything, and a season for every activity under the heavens.",
    ),
    Verse(
        "Isaiah 40:31",
        "But those who hope in the LORD will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.",
    ),
    Verse(
        "Isaiah 41:10",
        "So do not fear, for I am with you; do not be dismayed, for I am your God. I will strengthen you and help you; I will uphold you with my righteous right hand.",
    ),
    Verse(
        "Jeremiah 29:11",
        "For I know the plans I have for you, declares the LORD, plans to prosper you and not to harm you, plans to give you hope and a future.",
    ),
    Verse(
        "Lamentations 3:22-23",
        "Because of the LORD's great love we are not consumed, for his compassions never fail. They are new every morning; great is your faithfulness.",
    ),
    Verse(
        "Micah 6:8",
        "He has shown you, O mortal, what is good. And what does the LORD require of you? To act justly and to love mercy and to walk humbly with your God.",
    ),
    # --- Gospels ---
    Verse(
        "Matthew 5:16",
        "In the same way, let your light shine before others, that they may see your good deeds and glorify your Father in heaven.",
    ),
    Verse(
        "Matthew 6:33",
        "But seek first his kingdom and his righteousness, and all these things will be given to you as well.",
    ),
    Verse(
        "Matthew 6:34",
        "Therefore do not worry about tomorrow, for tomorrow will worry about itself. Each day has enough trouble of its own.",
    ),
    Verse(
        "Matthew 11:28-30",
        "Come to me, all you who are weary and burdened, and I will give you rest. Take my yoke upon you and learn from me, for I am gentle and humble in heart, and you will find rest for your souls.",
    ),
    Verse(
        "Mark 12:31",
        "The second is this: Love your neighbor as yourself. There is no commandment greater than these.",
    ),
    Verse(
        "Luke 6:31",
        "Do to others as you would have them do to you.",
    ),
    Verse(
        "John 13:34",
        "A new command I give you: Love one another. As I have loved you, so you must love one another.",
    ),
    Verse(
        "John 14:27",
        "Peace I leave with you; my peace I give you. I do not give to you as the world gives. Do not let your hearts be troubled and do not be afraid.",
    ),
    Verse(
        "John 16:33",
        "I have told you these things, so that in me you may have peace. In this world you will have trouble. But take heart! I have overcome the world.",
    ),
    # --- Epistles ---
    Verse(
        "Romans 5:3-4",
        "Not only so, but we also glory in our sufferings, because we know that suffering produces perseverance; perseverance, character; and character, hope.",
    ),
    Verse(
        "Romans 8:28",
        "And we know that in all things God works for the good of those who love him, who have been called according to his purpose.",
    ),
    Verse(
        "Romans 12:2",
        "Do not conform to the pattern of this world, but be transformed by the renewing of your mind. Then you will be able to test and approve what God's will is — his good, pleasing and perfect will.",
    ),
    Verse(
        "Romans 12:12",
        "Be joyful in hope, patient in affliction, faithful in prayer.",
    ),
    Verse(
        "Romans 12:18",
        "If it is possible, as far as it depends on you, live at peace with everyone.",
    ),
    Verse(
        "1 Corinthians 13:4-5",
        "Love is patient, love is kind. It does not envy, it does not boast, it is not proud. It does not dishonor others, it is not self-seeking, it is not easily angered, it keeps no record of wrongs.",
    ),
    Verse(
        "1 Corinthians 16:13-14",
        "Be on your guard; stand firm in the faith; be courageous; be strong. Do everything in love.",
    ),
    Verse(
        "2 Corinthians 5:7",
        "For we live by faith, not by sight.",
    ),
    Verse(
        "2 Corinthians 12:9",
        "But he said to me, My grace is sufficient for you, for my power is made perfect in weakness. Therefore I will boast all the more gladly about my weaknesses, so that Christ's power may rest on me.",
    ),
    Verse(
        "Galatians 5:22-23",
        "But the fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness, gentleness and self-control. Against such things there is no law.",
    ),
    Verse(
        "Galatians 6:9",
        "Let us not become weary in doing good, for at the proper time we will reap a harvest if we do not give up.",
    ),
    Verse(
        "Ephesians 2:10",
        "For we are God's handiwork, created in Christ Jesus to do good works, which God prepared in advance for us to do.",
    ),
    Verse(
        "Ephesians 4:29",
        "Do not let any unwholesome talk come out of your mouths, but only what is helpful for building others up according to their needs, that it may benefit those who listen.",
    ),
    Verse(
        "Ephesians 4:32",
        "Be kind and compassionate to one another, forgiving each other, just as in Christ God forgave you.",
    ),
    Verse(
        "Philippians 2:3-4",
        "Do nothing out of selfish ambition or vain conceit. Rather, in humility value others above yourselves, not looking to your own interests but each of you to the interests of the others.",
    ),
    Verse(
        "Philippians 4:6-7",
        "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus.",
    ),
    Verse(
        "Philippians 4:8",
        "Finally, brothers and sisters, whatever is true, whatever is noble, whatever is right, whatever is pure, whatever is lovely, whatever is admirable — if anything is excellent or praiseworthy — think about such things.",
    ),
    Verse(
        "Philippians 4:13",
        "I can do all this through him who gives me strength.",
    ),
    Verse(
        "Colossians 3:12",
        "Therefore, as God's chosen people, holy and dearly loved, clothe yourselves with compassion, kindness, humility, gentleness and patience.",
    ),
    Verse(
        "Colossians 3:23",
        "Whatever you do, work at it with all your heart, as working for the Lord, not for human masters.",
    ),
    Verse(
        "1 Thessalonians 5:16-18",
        "Rejoice always, pray continually, give thanks in all circumstances; for this is God's will for you in Christ Jesus.",
    ),
    Verse(
        "2 Timothy 1:7",
        "For the Spirit God gave us does not make us timid, but gives us power, love and self-discipline.",
    ),
    Verse(
        "Hebrews 11:1",
        "Now faith is confidence in what we hope for and assurance about what we do not see.",
    ),
    Verse(
        "Hebrews 12:1",
        "Therefore, since we are surrounded by such a great cloud of witnesses, let us throw off everything that hinders and the sin that so easily entangles. And let us run with perseverance the race marked out for us.",
    ),
    Verse(
        "James 1:2-4",
        "Consider it pure joy, my brothers and sisters, whenever you face trials of many kinds, because you know that the testing of your faith produces perseverance. Let perseverance finish its work so that you may be mature and complete, not lacking anything.",
    ),
    Verse(
        "James 1:19",
        "My dear brothers and sisters, take note of this: Everyone should be quick to listen, slow to speak and slow to become angry.",
    ),
    Verse(
        "James 4:6",
        "But he gives us more grace. That is why Scripture says: God opposes the proud but shows favor to the humble.",
    ),
    Verse(
        "1 Peter 5:7",
        "Cast all your anxiety on him because he cares for you.",
    ),
    Verse(
        "1 John 4:18",
        "There is no fear in love. But perfect love drives out fear, because fear has to do with punishment. The one who fears is not made perfect in love.",
    ),
    Verse(
        "1 John 4:19",
        "We love because he first loved us.",
    ),
]


def todays_verse(today: date | None = None) -> Verse:
    """Pick a verse deterministically by date so morning + evening editions of
    the same day share the same verse — the reflection will differ naturally
    because the news context differs."""
    today = today or date.today()
    return VERSES[today.toordinal() % len(VERSES)]


def format_verse_line(v: Verse) -> str:
    """Single-line representation used both inside the LLM user message and as
    the literal first line of the rendered DAILY VERSE section."""
    return f'"{v.text}" — {v.ref} ({v.translation})'
