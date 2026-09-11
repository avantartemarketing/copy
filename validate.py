"""
Mechanical checks, derived from docs/02-voice-and-negatives.md. No AI involved.

Two layers:
  check_bounded()  runs on every BOUNDED field in the brief (the only free text). Strict:
                   banned words, length, punctuation, and every number or name must be
                   backed by the facts elsewhere in the brief.
  check_email()    runs on the assembled email. Global hygiene only: dashes, spelling,
                   time and date formats, split words, and a cap on overused words.

In the real tool check_bounded() also runs on every AI candidate before a human sees it.
Errors block; warnings go to the reviewer.
"""
import re

import yaml

# The free-text fields. Everything else in the brief is a fact or a menu choice.
BOUNDED_KEYS = {"hook", "card_line", "subject_hook", "early_access_note", "technique_sentence",
                "recap", "quote_sentence", "footer", "delay_phrase", "artist_line", "artist_thanks", "artist_bio", "hook_short", "detail", "technique_clause", "making"}

BANNED = [
    # sales-page urgency the brand has never used
    "don't miss out", "don’t miss out", "miss out", "hurry", "act now", "act fast", "grab", "snag",
    "shop now", "get yours", "secure yours", "treat yourself", "last call", "final hours", "ends soon",
    "selling fast", "going fast", "almost gone", "while stocks last", "limited time offer",
    "exclusive offer", "own a piece of", "bring home", "make a statement", "conversation starter",
    "investment", "appreciate in value",
    # ai-flavoured filler
    "elevate", "delve", "dive into", "tapestry of", "testament to", "journey through", "realm",
    "unleash", "embark", "captivating", "mesmerising", "mesmerizing", "breathtaking", "stunning",
    "amazing", "must-have", "unmissable", "prestigious", "world-class", "seamless", "seamlessly",
    "effortless", "effortlessly", "game-changing", "cutting-edge", "nestled", "boasts", "showcases",
    "whether you're", "whether you’re", "look no further", "it's not just", "it’s not just",
    "not only", "in a world where", "in today's", "in today’s", "at its core", "at the heart of",
    "imagine", "picture this", "perfect for", "the perfect gift", "what are you waiting",
    "we're thrilled", "we’re thrilled", "thrilled to", "excited to announce", "excitingly",
    "we hope you'll agree", "as you know", "truly special", "one-of-a-kind",
    # wrong nouns for what we sell and who we sell to
    "product", "item", "merch", "drop", "raffle", "lottery", "giveaway", "customer", "shopper",
]
CAPPED = {"iconic": 1, "truly": 1, "unique": 1, "meticulous": 1, "meticulously": 1, "very": 1,
          "celebrated": 1, "renowned": 1, "landmark": 1, "seminal": 1, "striking": 1}
US_SPELLING = {"color": "colour", "colors": "colours", "colorway": "colourway", "realize": "realise",
               "center": "centre", "gray": "grey", "jewelry": "jewellery", "favorite": "favourite",
               "honor": "honour", "catalog": "catalogue", "program": "programme"}
LOCKED_OK = ["Great choice!", "and we will!"]      # locked house lines that legitimately break a rule
HOUSE_PROPER = set("""UK Make-Ready North London Amsterdam Avant Arte Estate Foundation Trust Insiders
  January February March April May June July August September October November December
  Monday Tuesday Wednesday Thursday Friday Saturday Sunday I I'm I'd I've It's""".split())


def bounded_fields(brief):
    """Yield (path, text) for every BOUNDED field in the brief."""
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in BOUNDED_KEYS:
                    if isinstance(v, str) and v.strip():
                        yield path + k, v
                else:
                    yield from walk(v, path + k + ".")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from walk(v, f"{path}{i}.")
    yield from walk(brief, "")


def facts(brief):
    """The brief with its free-text fields removed: the only things a bounded field may assert."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in BOUNDED_KEYS}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    blob = yaml.safe_dump(strip(brief), allow_unicode=True)
    nums = {int(x) for x in re.findall(r"\d+", blob)}
    words = set(re.findall(r"[\w'’.-]+", blob))
    return nums, words


def sentences(text):
    for para in text.split("\n"):
        for s in re.split(r"(?<=[.!?])\s+", para.strip()):
            if s:
                yield s


def dash_and_spelling(text, low, errors):
    if "—" in text:
        errors.append("em dash (—): the house dash is a spaced en dash ( – )")
    if re.search(r"\w[–—]\w", text):
        errors.append("unspaced dash: use a spaced en dash ( – )")
    for us, uk in US_SPELLING.items():
        if re.search(rf"\b{us}\b", low):
            errors.append(f"US spelling “{us}”: use “{uk}”")
    if re.search(r"limited-edition", low):
        errors.append("“limited-edition”: the house form is “limited edition”, no hyphen")


def check_bounded(name, text, fact_nums, fact_words):
    errors, warnings = [], []
    low = text.lower()
    for p in BANNED:
        if re.search(r"(?<![\w-])" + re.escape(p) + r"(?![\w-])", low):
            errors.append(f"banned: “{p}”")
    dash_and_spelling(text, low, errors)
    if "!" in text:
        errors.append("exclamation mark")
    if "?" in text:
        errors.append("question mark: no rhetorical questions")
    for s in sentences(text):
        n = len(s.split())
        if n > 35:
            errors.append(f"sentence of {n} words (max 35): “{s[:48]}…”")
    if len(text.split()) > 70:
        warnings.append(f"{len(text.split())} words (house paragraphs: median 24, p90 50)")
    for w, cap in CAPPED.items():
        n = len(re.findall(rf"\b{w}\b", low))
        if n > cap:
            warnings.append(f"“{w}” used {n}× in one slot")
    for num in sorted({int(x) for x in re.findall(r"\d+", text)}):
        if num not in fact_nums:
            errors.append(f"number {num} is not in the brief's facts")
    for s in sentences(text):
        for tok in s.split()[1:]:
            t = tok.strip("“”\"'(),.;:").removesuffix("'s").removesuffix("’s")
            if len(t) > 1 and re.match(r"^[A-Z][\w'’.-]*$", t) and t not in HOUSE_PROPER and t not in fact_words:
                warnings.append(f"“{t}” is not in the brief's facts (invented name or place?)")
    return [f"{name}: {e}" for e in errors], [f"{name}: {w}" for w in warnings]


def check_email(text):
    errors, warnings = [], []
    body = "\n".join(l for l in text.splitlines() if not l.startswith("[INTERNAL NAME]"))
    body = re.sub(r"^\[[^\]]+\]\s*", "", body, flags=re.M)         # module markers
    body = re.sub(r"\{\{.*?\}\}", "", body)                          # personalisation tokens
    body = body.replace("═", "")
    low = body.lower()
    dash_and_spelling(body, low, errors)
    for line in body.splitlines():
        if "!" in line and not any(ok in line for ok in LOCKED_OK):
            errors.append("exclamation mark")
            break
    if "?" in body:
        errors.append("question mark: no rhetorical questions")
    if re.search(r"\b\d{1,2}\s?(am|pm)\b", low):
        errors.append("12-hour time: write 17:00 UK time")
    if re.search(r"\b\d{1,2}(st|nd|rd|th)\b", low):
        errors.append("ordinal date (29th): write 29 September")
    if re.search(r"\b(gmt|bst)\b", low):
        errors.append("GMT/BST: write “UK time”")
    for w, cap in CAPPED.items():
        n = len(re.findall(rf"\b{w}\b", low))
        if n > cap:
            warnings.append(f"“{w}” used {n}× across the email (cap {cap})")
    if re.search(r"(?<![\w'’])(?!a\b)[a-z] [a-z]{1,2}\b|\b[a-z]{1,2} (?!a\b)[a-z](?![\w'’])", body):
        warnings.append("possible split word (“o f”, “an d”): a known HubSpot editor artefact")
    if "[CAPTION]" in text:                                          # Instagram caption rules
        cap = text.split("[CAPTION]", 1)[1].strip()
        if len(cap) > 650:
            warnings.append(f"caption of {len(cap)} characters (house median 413, p90 693)")
        if not re.search(r"link in (our |my |the )?bio", cap, re.I):
            errors.append("Instagram caption has no “link in bio” line")
        if re.search(r"https?://", cap):
            errors.append("Instagram caption contains a URL; links go in the bio")
    return errors, warnings


def validate(text, brief):
    fact_nums, fact_words = facts(brief)
    errors, warnings = check_email(text)
    for name, value in bounded_fields(brief):
        if value.strip() not in text:          # only the slots this email actually uses
            continue
        e, w = check_bounded(name, value, fact_nums, fact_words)
        errors += e
        warnings += w
    return sorted(set(errors)), sorted(set(warnings))
