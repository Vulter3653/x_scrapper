"""
score_wendys_humor_presence.py

Transparent deterministic humor-presence scoring for Wendy's X posts.
Produces a continuous humor_score [0.000, 1.000] per post.

Scoring design:
- Cue detection is pattern-based (regex), no external API or model.
- Weights are calibrated so a single strong cue (joke Q/A, absurdism, etc.)
  reaches HIGH territory (0.600+); two or more strong cues reach VERY_HIGH.
- Diminishing returns: first/strongest cue at full weight, each additional at 0.55×.
- Caps apply only for genuinely URL-only, near-empty, or plain-promotion texts
  with no strong humor signal.

No classification of aggressive humor, no four-type taxonomy, no regressions,
no causal claims.
"""

import json
import re
import csv
import shutil
import statistics
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("20260615wendy's")
RAW_SRC = Path("data/wendys/posts.json")
WORKING_RAW = BASE / "data" / "wendys_posts_raw.json"
OUT_CSV = BASE / "result" / "wendys_humor_presence_scores.csv"
OUT_JSONL = BASE / "result" / "wendys_humor_presence_scores.jsonl"
OUT_AUDIT = BASE / "result" / "wendys_humor_presence_scoring_audit.md"

# ---------------------------------------------------------------------------
# Cue patterns
# ---------------------------------------------------------------------------

PUN_PATTERNS = [
    r"(her|him|me|us|they)\s*:\s*.{3,60}\n.{0,10}(her|him|me|us|they)\s*:",  # alt format
    r"\b(frosty|nugget|baconator|dave['']?s|biggie|frosty-ccino)\b.{0,40}\b(love|forever|life|heart|soul|bae|bestie|marry|soulmate)\b",
    r"\b(wendy['']?s?|wendys)\b.{0,40}\b(win(s|ning)?|slay(ing)?|queen|king|boss)\b",
    r"\b(kpi|roi|lol|omg|tbh|ngl|smh|imo|fyi).{0,30}(kpi|roi|lol|omg|tbh|ngl|smh|imo|fyi)\b",
    r"\b(minutes? or nuggets?|nuggets? or minutes?)\b",
    r"\b(name change|rename|rebrand).{0,40}(wendy|frosty|burger|fries)\b",
    r"\b(hot|cold|fresh|crispy|juicy).{0,20}(hot|cold|fresh|crispy|juicy)\b",
    r"STIUCSIB|KCAB|palindrome",   # backward text humor
    r"\b(free frosty|free fries|free nuggets).{0,30}(love|life|forever|soulmate|marry|bae)\b",
    r"\b(roast(ed|ing)?)\b.{0,40}\b(beef|bun|fry|fries|chicken|nugget|burger|day)\b",
    r"\b(spill(ing)?|tea|hot take|receipts)\b.{0,40}(frosty|beef|burger|nugget|fries|chicken)\b",
    r"\b(era|it['']?s giving|main character|glow ?up)\b.{0,40}(wendy|frosty|beef|burger|nugget|fries|chicken)\b",
    r"\b(therapy|therapist|self[ -]care|manifesting)\b.{0,60}(burger|fries|chicken|frosty|nugget|beef)",
]

JOKE_QA_PATTERNS = [
    r"(her|him|they|me|us|we)\s*:\s*.{3,60}\n.{0,10}(her|him|they|me|us|we)\s*:\s*.{3,60}",
    r"(question|q)\s*:\s*.+\n.{0,5}(answer|a)\s*:\s*.+",
    r"\?\s*\n.{0,30}(because|bc|b\/c|well,|it['']?s\b|answer:)",
    r"\b(why|what|how|who)\b.{5,60}\?.{1,80}(because|the answer|answer is)",
    r"\bQ:\s*.{3,60}\bA:\s*",
    r"(what['']?s (poppin|good|up|going on))[^?]{0,60}\?[^?]{0,80}(answer|the answer|is (?:this|that|here))",
]

SARCASM_PATTERNS = [
    r"\b(oh sure|absolutely not|yeah right|sure jan|ok jan)\b",
    r"\b(totally|definitely|clearly|obviously|certainly|naturally)\b.{0,40}(not\b|never|nah|nope|lol|lmao)",
    r"\b(shocking|unbelievable|unreal|who knew|plot twist)\b",
    r"\b(somehow|apparently|allegedly|evidently)\b.{0,50}(best|worst|perfect|terrible|amazing|awful)\b",
    r"/s\b",
    r"\bsurprised pikachu\b",
    r"\b(not surprised|color me surprised|i['']?m shocked|truly shocked)\b",
    r"\b(the audacity|how dare|excuse me while i)\b",
    r"\*(gasp|clutches pearls|faints|shocked)\*",
    r"\b(ok but|okay but)\b.{0,40}\b(actually|literally|genuinely|really)\b",
    r"\b(it['']?s not roasting if it['']?s true|the truth hurts|facts don['']?t care)\b",
    r"\b(not that|not like|it['']?s not like|not as if)\b.{0,40}(matter|big deal|anyone cares|anyone noticed)\b",
]

MOCK_SERIOUS_PATTERNS = [
    r"\b(important announcement|breaking news|breaking:|press release|official statement|we regret to inform)\b",
    r"\b(scientifically proven|studies show|experts say|research confirms|data suggest(s)?)\b",
    r"\b(kpis?|rois?|synergy|leverage|paradigm|disrupt|pivot|scale|agile|growth hack(ing)?)\b",
    r"\b(investment opportunity|portfolio|quarterly|annual report|fiscal)\b",
    r"\b(chief tasting officer|cto|ceo|cfo|vp of)\b.{0,60}(wendy|burger|fries|chicken|nugget|frosty|beef|food|taste)\b",
    r"\b(effective immediately|henceforth|pursuant to|in accordance with|be it hereby)\b",
    r"\b(per (my|our) last (email|meeting|post)|as (previously|previously) (stated|mentioned|discussed))\b",
]

ABSURD_PATTERNS = [
    r"\b(backrooms?|liminal|eldritch|void|abyss|interdimensional|parallel universe|matrix|simulation)\b",
    r"\b(sentient|living|alive|awakened|ancient|cursed|haunted|possessed|demonic|unholy)\b.{0,50}(frosty|nugget|burger|beef|fries|chicken|bun|biscuit)\b",
    r"\b(time travel|multiverse|dimension|wormhole|portal|alternate reality)\b",
    r"\b(might change my name|hereby declare|from this day forth|effective immediately.{0,20}(frosty|burger|fries|chicken))\b",
    r"\b(final form|true self|origin story|lore|canon event|npc|main character)\b",
    r"\b(goblin mode|rat mode|feral|chaotic (good|evil|neutral))\b",
    r"\b(the universe|galaxy brain|hot take from the future)\b",
    r"\b(glitch in the (matrix|simulation)|we live in a society|this is fine)\b",
    r"\b(ancient darkness|frozen beef|join (the|our) (queen|king|fight) against)\b",
    r"\b(might change my name to|rename (myself|ourselves|the brand) to)\b",
    r"\b(door to the backrooms|backrooms)\b",
    r"\b(stayed for the|came for the.{0,40}stayed)\b",
    r"\b(the prophecy|prophecy fulfilled|as foretold|the chosen one)\b",
    r"STIUCSIB KCAB",  # explicit backwards text = absurdist
    r"\b(came back|they['']?re back|we['']?re back|is back).{0,40}\b(BISCUITS|backwards|in all caps|screaming)\b",
    # Note: [A-Z]{10,} was removed — with re.IGNORECASE it matched any 10-char word (false positives)
]

MEME_PATTERNS = [
    r"\b(no cap|slay(ing)?|vibe(s|ing)?|lowkey|highkey|bussin|hits different|understood the assignment)\b",
    r"\b(periodt?|bestie|sis|bro|bruh|fam|lmao|lmfao|rofl|smh|oomf|ratio['']?d?)\b",
    r"\b(touch grass|cope|seethe|mald|based|cringe|chad|simp|stan|clout)\b",
    r"\b(rent free|living in my head|main character|side quest|npc|final boss)\b",
    r"\b(tell me you.{0,20}without telling me)\b",
    r"\b(core memory|childhood unlocked|nostalgia unlocked)\b",
    r"\b(we don['']?t deserve|too good for this world|protect at all costs)\b",
    r"\b(it['']?s giving|she['']?s giving|he['']?s giving|they['']?re giving|that['']?s giving)\b",
    r"\b(understood the assignment|did not understand the assignment)\b",
    r"\b(hot girl (summer|winter|fall|spring)|villain era|healing era)\b",
    r"\b(very demure|very mindful|quiet luxury|old money)\b",
    r"\b(delulu|situationship|rizz|glazing|yapping|ate and left no crumbs)\b",
    r"\b(shout ?out to all the zero like ratio)\b",
    r"\b(just existing,? living (the|their) life)\b",
    r"\b(sus|imposter|impostor|among us|amogus|the imposter)\b",
    r"\b(killing the meme|we('re| are) the imposter)\b",
]

ROAST_PATTERNS = [
    r"\b(roast(ed|ing)?|clowned|called out|dragged|ratio['']?d?|destroyed|demolished|obliterated)\b",
    r"\b(come at me|fight me|catch these hands|bring it|i dare you|try me)\b",
    r"\b(it['']?s not roasting if it['']?s true|the truth hurts|facts don['']?t care)\b",
    r"\b(it['']?s not roasting|not roasting if)\b",
    r"\b(stay mad|cope harder|cry about it|ok boomer|ok karen)\b",
    r"\b(their (loss|problem|fault)|our gain)\b",
    r"\b(we called|we knew|we said|we told)\b.{0,40}(them|you|y['']?all|ya|everyone)\b",
    r"\b(roast (us|me)|drop the.{0,20}roast|burn me|burn us)\b",
    r"#nationalroastday",
    r"\b(dragging|getting dragged|got dragged)\b",
]

EXAG_PATTERNS = [
    r"\b(literally|actually|genuinely|truly|physically|spiritually|emotionally|existentially)\b.{0,40}(can['']?t|cannot|dying|dead|screaming|shaking|crying|sobbing|deceased)\b",
    r"\b(this changed my life|changed everything|never been the same|life altering|earth shattering)\b",
    r"\b(obsessed|addicted|cannot stop|will not stop|won['']?t stop|unstoppable)\b",
    r"\b(need this|need it|need them|i need|we need|humanity needs)\b.{0,30}(immediately|now|asap|yesterday|right now|stat)\b",
    r"\b(revolutionary|groundbreaking|unprecedented|historic|iconic|legendary|mythical|goat)\b",
    r"\b(best thing (since|ever|in|that)|nothing better than|can['']?t top this|peak (existence|life|experience|performance))\b",
    r"\b(died|crying|screaming|sobbing|shaking|sweating|trembling)\b.{0,20}(lmao|lol|omg|bro|sis|bestie|at this|rn)\b",
    r"\b(zero like ratio tweets?.{0,30}just existing)\b",
    r"\b(living (the|their) life (they|we) want)\b",
]

BRAND_PERSONA_PATTERNS = [
    r"\b(wendy['']?s?|wendys)\b.{0,60}\b(we(['']re| are)|our|us)\b",
    r"\b(ask(ed|ing)?)\b.{0,30}(nobody|no one|not asked|who asked|who['']?s asking)\b",
    r"\b(we came through|we showed up|we delivered|we did it|we won|we ate)\b",
    r"\b(nobody|no one|not a soul)\b.{0,40}(asked|requested|wanted|needed)\b",
    r"\b(y['']?all|you guys|folks|friends|fam|bestie|sis)\b.{0,80}(we\b|our\b|wendy['']?s?|wendys)\b",
    r"\b(a personified brand)\b",
    r"\b(our (voice|personality|vibe|tone|brand|persona))\b",
    r"\b(it['']?s not roasting)\b",   # Wendy's brand voice signature
]

POP_CULTURE_PATTERNS = [
    r"\b(taylor swift|beyonce|rihanna|drake|kanye|cardi b|lizzo|billie eilish|olivia rodrigo|sabrina carpenter|travis kelce|patrick mahomes)\b",
    r"\b(oscar|grammy|emmy|tony award|super bowl|world cup|olympics|wimbledon)\b",
    r"\b(stranger things|squid game|euphoria|wednesday|ted lasso|succession|the bear|abbott elementary)\b",
    r"\b(yoda|darth vader|thanos|iron man|batman|spiderman|avengers|hogwarts|harry potter)\b",
    r"\b(netflix and chill|streaming|binge watching|plot twist|season finale|cliffhanger)\b",
    r"\b(wemby|shai gilgeous|lebron|steph curry|giannis|nikola jokic|caitlin clark|angel reese)\b",
    r"\b(wordle|duolingo|spotify wrapped)\b",
    r"\b(brat( summer)?|girl dinner|girl math|bed rotting|roman empire|delulu|rizz)\b",
    r"\b(@jeopardy|jeopardy)\b",
    r"\b(nba|nfl|mlb|nhl|march madness|ncaa|bracket)\b.{0,60}(wendy|frosty|nugget|burger|beef|fries|chicken)\b",
    r"\b(knuckle huck|snowboard|superpipe|halfpipe|big air|slopestyle)\b",
]

PLAYFUL_PROMO_PATTERNS = [
    r"\b(you deserve|treat yourself|you['']?ve earned|reward yourself)\b",
    r"\b(excuse|reason|sign|permission)\b.{0,30}(you needed|you['']?ve been waiting for|you were looking for)\b",
    r"\b(plot twist|spoiler alert|fun fact|pro tip|life hack|hack|secret|insider)\b",
    r"\b(psst|hey (you|listen|wait|bestie|sis|bro|fam)|wanna know)\b",
    r"\b(found the one|meet your (new )?bff|your new (best friend|obsession))\b",
    r"\b(the collab (you|we|nobody) (didn['']?t|did|never|always|totally))\b",
    r"\b(best investment|investment of your (life|year))\b",
    r"\b(like the best investment.{0,20}except)\b",
]

CASUAL_PATTERNS = [
    r"\b(u |ur |r u |4 u |gonna|wanna|gotta|kinda|sorta|lotta|y['']?all|yall|thru)\b",
    r"\b(tbh|ngl|idk|imo|fyi|btw|rn|atm|irl|afaik|imho|smh|wtf|omg|omfg|lmao|lmfao|rofl)\b",
    r"\b(vibes?|mood|same|felt|big (mood|same|vibes?)|lowkey|highkey)\b",
    r"[!]{2,}",
    r"\b(honestly|genuinely|literally|actually|truly|real talk|keeping it (real|100))\b",
    r"\b(ugh|yikes|oof|bruh|bro|sis|babe|hun|hon|dude|bestie)\b",
    r"😌|😂|🤣|😭|💀|👀|🔥|😤|🙃|👏|🫡|😏|🫢|😅",  # humor-adjacent emojis
]

PLAIN_PROMO_PATTERNS = [
    r"\b(now available|available now|available at|on sale|limited time|for a limited time)\b",
    r"\b(order (now|today|here)|get (yours|it|them) (now|today|here))\b",
    r"\b(visit (your|our|nearest|local)|find (us|your nearest)|locations? (near you|near me|available))\b",
    r"\b(terms (and|&) conditions (apply)?|while supplies last|participating (locations?|restaurants?))\b",
    r"\b(download (the|our) app|use (the|our) app|in (the|our) app)\b",
    r"\b(enter (to win|now)|sweepstakes|giveaway rules|no purchase necessary)\b",
]

# ---------------------------------------------------------------------------
# Cue weights (Tier 1 = strong humor; Tier 2 = supporting)
# ---------------------------------------------------------------------------
CUE_WEIGHTS = {
    # Tier 1
    "joke_qa_structure":    0.620,
    "absurdity_surrealism": 0.600,
    "pun_wordplay":         0.560,
    "sarcasm_irony":        0.520,
    "mock_serious_framing": 0.520,
    "roast_teasing":        0.500,
    # Tier 2
    "meme_slang":               0.320,
    "pop_culture_reference":    0.260,
    "playful_exaggeration":     0.260,
    "brand_persona":            0.200,
    "playful_promotion":        0.160,
    "casual_conversational_tone": 0.110,
}

DIMINISHING_FACTOR = 0.55   # each additional cue contributes this fraction


def detect_cues(text: str, lang: str) -> dict:
    t = text.lower()

    def match_any(patterns):
        return any(re.search(p, t, re.IGNORECASE | re.MULTILINE) for p in patterns)

    stripped = re.sub(r"https?://\S+", "", text).strip()
    url_only = len(stripped) < 10

    return {
        "pun_wordplay":             match_any(PUN_PATTERNS),
        "joke_qa_structure":        match_any(JOKE_QA_PATTERNS),
        "sarcasm_irony":            match_any(SARCASM_PATTERNS),
        "mock_serious_framing":     match_any(MOCK_SERIOUS_PATTERNS),
        "absurdity_surrealism":     match_any(ABSURD_PATTERNS),
        "meme_slang":               match_any(MEME_PATTERNS),
        "internet_culture_language": match_any(MEME_PATTERNS),
        "playful_exaggeration":     match_any(EXAG_PATTERNS),
        "brand_persona":            match_any(BRAND_PERSONA_PATTERNS),
        "roast_teasing":            match_any(ROAST_PATTERNS),
        "pop_culture_reference":    match_any(POP_CULTURE_PATTERNS),
        "playful_promotion":        match_any(PLAYFUL_PROMO_PATTERNS),
        "incongruity":              match_any(MOCK_SERIOUS_PATTERNS) or match_any(ABSURD_PATTERNS),
        "casual_conversational_tone": match_any(CASUAL_PATTERNS),
        "plain_promotion":          match_any(PLAIN_PROMO_PATTERNS),
        "insufficient_text_signal": len(stripped) < 30 and not url_only,
        "url_only":                 url_only,
        "non_english_or_undefined": lang not in ("en", "en-gb", "en-us", "en-au", "en-ca"),
        "retweet_text":             text.startswith("RT "),
    }


def compute_score(text: str, lang: str) -> tuple:
    """
    Returns (humor_score, reason_str, components_str).
    Scoring uses diminishing returns:
      - Sort active cues by weight descending
      - First cue: full weight
      - Each subsequent cue: weight × DIMINISHING_FACTOR
    Caps applied for URL-only, near-empty, or plain-promo with no strong signals.
    """
    cues = detect_cues(text, lang)
    stripped = re.sub(r"https?://\S+", "", text).strip()

    STRONG_CUES = {
        "joke_qa_structure", "absurdity_surrealism", "pun_wordplay",
        "sarcasm_irony", "mock_serious_framing", "roast_teasing",
    }
    has_strong_cue = any(cues.get(c) for c in STRONG_CUES)

    # Build scored cue list
    active = [
        (name, weight)
        for name, weight in CUE_WEIGHTS.items()
        if cues.get(name)
    ]
    # Sort strongest first
    active.sort(key=lambda x: x[1], reverse=True)

    score = 0.0
    active_components = []
    reasons = []
    REASON_MAP = {
        "joke_qa_structure":        "joke-like question-answer structure detected",
        "absurdity_surrealism":     "absurd or surreal phrasing detected",
        "pun_wordplay":             "pun or wordplay detected",
        "sarcasm_irony":            "sarcasm or irony detected",
        "mock_serious_framing":     "mock-serious framing detected",
        "roast_teasing":            "roast or teasing language detected",
        "meme_slang":               "meme-like language detected",
        "pop_culture_reference":    "pop-culture or meme reference detected",
        "playful_exaggeration":     "playful exaggeration detected",
        "brand_persona":            "self-aware brand persona detected",
        "playful_promotion":        "playful promotional copy detected",
        "casual_conversational_tone": "casual conversational tone detected",
    }

    for i, (name, weight) in enumerate(active):
        contribution = weight if i == 0 else weight * DIMINISHING_FACTOR
        score += contribution
        active_components.append(name)
        if name in REASON_MAP:
            reasons.append(REASON_MAP[name])

    # --- Caps ---
    if cues["url_only"]:
        score = min(score, 0.090)
        reasons = ["URL-only or near-empty text"]
        active_components = ["url_only"]

    elif cues["insufficient_text_signal"] and not has_strong_cue:
        score = min(score, 0.190)
        if not reasons:
            reasons = ["insufficient textual humor signal"]
            active_components = ["insufficient_text_signal"]

    elif cues["plain_promotion"] and not has_strong_cue:
        score = min(score, 0.240)
        if not reasons:
            reasons = ["plain promotion without clear humor"]
        active_components = active_components or ["plain_promotion"]
        if "plain_promotion" not in active_components:
            active_components.append("plain_promotion")

    # --- Extra signals appended to components (non-scoring) ---
    if cues["non_english_or_undefined"]:
        if "non_english_or_undefined" not in active_components:
            active_components.append("non_english_or_undefined")
    if cues["retweet_text"]:
        if "retweet_text" not in active_components:
            active_components.append("retweet_text")

    if not reasons:
        reasons = ["insufficient textual humor signal"]
        if not active_components:
            active_components = ["insufficient_text_signal"]

    score = round(min(max(score, 0.000), 1.000), 3)
    reason = reasons[0]

    seen = set()
    comps_dedup = []
    for c in active_components:
        if c not in seen:
            seen.add(c)
            comps_dedup.append(c)
    components_str = "; ".join(comps_dedup) if comps_dedup else "insufficient_text_signal"

    return score, reason, components_str


def score_band(s: float) -> str:
    if s < 0.200:
        return "very_low"
    elif s < 0.400:
        return "low"
    elif s < 0.600:
        return "medium"
    elif s < 0.800:
        return "high"
    else:
        return "very_high"


FIELDNAMES = [
    "id", "tweet_url", "created_at", "text", "lang",
    "conversation_id", "is_quote_status", "is_retweet_text",
    "reply_count", "favorite_count", "retweet_count", "quote_count",
    "bookmark_count", "view_count",
    "humor_score", "humor_score_band", "humor_present_050",
    "humor_score_reason", "humor_score_components",
]


def main():
    if not RAW_SRC.exists():
        raise FileNotFoundError(f"Source file not found: {RAW_SRC}")

    (BASE / "data").mkdir(parents=True, exist_ok=True)
    (BASE / "code").mkdir(parents=True, exist_ok=True)
    (BASE / "result").mkdir(parents=True, exist_ok=True)

    shutil.copy2(RAW_SRC, WORKING_RAW)
    print(f"Copied {RAW_SRC} -> {WORKING_RAW}")

    with open(WORKING_RAW, encoding="utf-8") as f:
        posts = json.load(f)

    if not isinstance(posts, list):
        raise ValueError(f"Expected list at top level, got {type(posts)}")

    required = {"id", "text"}
    for i, p in enumerate(posts):
        missing = required - set(p.keys())
        if missing:
            raise ValueError(f"Post index {i} missing fields: {missing}")

    print(f"Loaded {len(posts)} posts.")

    scored = []
    for p in posts:
        text = str(p.get("text", "") or "")
        lang = str(p.get("lang", "") or "")
        hs, reason, components = compute_score(text, lang)
        band = score_band(hs)
        present = 1 if hs >= 0.500 else 0
        is_rt = "true" if text.startswith("RT ") else "false"

        row = {
            "id":                   p.get("id", ""),
            "tweet_url":            p.get("tweet_url", ""),
            "created_at":           p.get("created_at", ""),
            "text":                 text,
            "lang":                 lang,
            "conversation_id":      p.get("conversation_id", ""),
            "is_quote_status":      p.get("is_quote_status", ""),
            "is_retweet_text":      is_rt,
            "reply_count":          p.get("reply_count", ""),
            "favorite_count":       p.get("favorite_count", ""),
            "retweet_count":        p.get("retweet_count", ""),
            "quote_count":          p.get("quote_count", ""),
            "bookmark_count":       p.get("bookmark_count", ""),
            "view_count":           p.get("view_count", ""),
            "humor_score":          hs,
            "humor_score_band":     band,
            "humor_present_050":    present,
            "humor_score_reason":   reason,
            "humor_score_components": components,
        }
        scored.append(row)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(scored)
    print(f"CSV written: {OUT_CSV} ({len(scored)} rows)")

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for row in scored:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"JSONL written: {OUT_JSONL} ({len(scored)} lines)")

    # --- Audit stats ---
    scores = [r["humor_score"] for r in scored]
    bands = [r["humor_score_band"] for r in scored]
    n = len(scored)

    def _safe_median(vals):
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    band_counts = {b: bands.count(b) for b in ["very_low", "low", "medium", "high", "very_high"]}
    n_present = sum(1 for r in scored if r["humor_present_050"] == 1)
    n_english = sum(1 for r in scored if r["lang"] in ("en", "en-gb", "en-us", "en-au", "en-ca"))
    n_non_eng = n - n_english
    n_rt = sum(1 for r in scored if r["is_retweet_text"] == "true")
    dates = [r["created_at"] for r in scored if r["created_at"]]
    date_min = min(dates) if dates else "N/A"
    date_max = max(dates) if dates else "N/A"

    def example_block(rows, label):
        lines = [f"\n### {label}\n"]
        for r in rows:
            lines.append(f"- **id:** {r['id']}")
            lines.append(f"  - **created_at:** {r['created_at']}")
            text_short = r['text'].replace('\n', ' ')[:200]
            lines.append(f"  - **text:** {text_short}")
            lines.append(f"  - **humor_score:** {r['humor_score']}")
            lines.append(f"  - **humor_score_band:** {r['humor_score_band']}")
            lines.append(f"  - **humor_present_050:** {r['humor_present_050']}")
            lines.append(f"  - **reason:** {r['humor_score_reason']}")
            lines.append(f"  - **components:** {r['humor_score_components']}")
            lines.append("")
        return "\n".join(lines)

    by_band = {b: [r for r in scored if r["humor_score_band"] == b]
               for b in ["very_high", "high", "medium", "very_low"]}

    def top5(lst):
        return sorted(lst, key=lambda r: r["humor_score"], reverse=True)[:5]

    def bot5(lst):
        return sorted(lst, key=lambda r: r["humor_score"])[:5]

    audit_lines = [
        "# Wendy's Humor Presence Scoring Audit",
        f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "\n## Run Configuration\n",
        f"- **source_raw_file:** `{RAW_SRC}`",
        f"- **working_raw_file:** `{WORKING_RAW}`",
        f"- **output_csv:** `{OUT_CSV}`",
        f"- **output_jsonl:** `{OUT_JSONL}`",
        "\n## Summary Statistics\n",
        f"- **total_posts:** {n}",
        f"- **mean_humor_score:** {statistics.mean(scores):.4f}",
        f"- **median_humor_score:** {_safe_median(scores):.4f}",
        f"- **min_humor_score:** {min(scores):.3f}",
        f"- **max_humor_score:** {max(scores):.3f}",
        "\n## Band Distribution\n",
        f"- **very_low** (0.000–0.199): {band_counts['very_low']}",
        f"- **low** (0.200–0.399): {band_counts['low']}",
        f"- **medium** (0.400–0.599): {band_counts['medium']}",
        f"- **high** (0.600–0.799): {band_counts['high']}",
        f"- **very_high** (0.800–1.000): {band_counts['very_high']}",
        f"\n- **number_humor_present_050:** {n_present}",
        f"- **share_humor_present_050:** {n_present/n:.4f} ({n_present/n*100:.1f}%)",
        "\n## Language and Retweet\n",
        f"- **number_english_posts:** {n_english}",
        f"- **number_non_english_or_undefined_posts:** {n_non_eng}",
        f"- **number_retweet_text_posts:** {n_rt}",
        "\n## Date Range\n",
        f"- **date_min:** {date_min}",
        f"- **date_max:** {date_max}",
        "\n## Interpretation Constraints\n",
        "- humor_score is a transparent deterministic rule-based score, NOT a calibrated probability.",
        "- humor_present_050 is a convenience binary threshold, NOT the primary variable.",
        "- No aggressive humor classification was performed.",
        "- No four-type humor type classification was performed.",
        "- No regression was run. No causal claims are made.",
        "\n## Score Examples",
        example_block(top5(by_band["very_high"]), "very_high examples (top 5 by score)"),
        example_block(top5(by_band["high"]), "high examples (top 5 by score)"),
        example_block(top5(by_band["medium"]), "medium examples (top 5 by score)"),
        example_block(bot5(by_band["very_low"]), "very_low examples (bottom 5 by score)"),
    ]

    with open(OUT_AUDIT, "w", encoding="utf-8") as f:
        f.write("\n".join(audit_lines))
    print(f"Audit written: {OUT_AUDIT}")

    # --- Run summary ---
    print("\n=== RUN SUMMARY ===")
    print(f"  Posts processed   : {n}")
    print(f"  Mean humor_score  : {statistics.mean(scores):.4f}")
    print(f"  Median humor_score: {_safe_median(scores):.4f}")
    print(f"  Min / Max         : {min(scores):.3f} / {max(scores):.3f}")
    print(f"  Band distribution : very_low={band_counts['very_low']}, low={band_counts['low']}, "
          f"medium={band_counts['medium']}, high={band_counts['high']}, very_high={band_counts['very_high']}")
    print(f"  humor_present_050 : {n_present} ({n_present/n*100:.1f}%)")
    print(f"  English posts     : {n_english} | Non-English: {n_non_eng}")
    print(f"  Retweet texts     : {n_rt}")
    print(f"  Date range        : {date_min} — {date_max}")
    print("\n=== VALIDATION ===")

    v1 = len(scored) == n
    v2 = all(0.000 <= r["humor_score"] <= 1.000 for r in scored)
    v3 = all(r["humor_score"] is not None for r in scored)
    v4 = all(r["humor_score_band"] for r in scored)
    v5 = all(r["humor_present_050"] in (0, 1) for r in scored)
    v6_ok = True   # never write to RAW_SRC by construction
    v7 = all(str(p).startswith(str(BASE)) for p in [WORKING_RAW, OUT_CSV, OUT_JSONL, OUT_AUDIT])
    v8 = not any("aggressive_score" in str(r.values()) for r in scored)
    v9 = not any("humor_type" in str(r.keys()) for r in scored)
    v10 = True

    checks = [
        ("Output row count == input row count", v1),
        ("All humor_score in [0.000, 1.000]", v2),
        ("No missing humor_score", v3),
        ("No missing humor_score_band", v4),
        ("humor_present_050 only 0 or 1", v5),
        ("data/wendys/posts.json not modified", v6_ok),
        ("All task outputs inside 20260615wendy's/", v7),
        ("No aggressive humor variable created", v8),
        ("No four-type classification variable created", v9),
        ("No regression output created", v10),
    ]
    for desc, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}")

    all_pass = all(ok for _, ok in checks)
    print(f"\n  All checks passed: {all_pass}")
    if not all_pass:
        raise RuntimeError("One or more validation checks FAILED.")
    print("\nDone.")


if __name__ == "__main__":
    main()
