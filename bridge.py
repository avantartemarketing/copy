"""The tool's state, as a brief.

The page keeps one flat record of facts and the written fragments. The templates, the
validator and the workbook all read a brief (see briefs/). This is the one place the two
shapes meet, so the page can be rendered by the same templates as everything else.
"""
import datetime
import re


def _dt(v):
    """The page stores '2026-04-30T14:00'; the briefs write '2026-04-30 14:00'. Either, or blank."""
    v = (v or "").strip().replace("T", " ")
    return v[:16] if v else ""


def page_text(page):
    """The product pages' text, the first artwork's and its siblings', as the facts a fragment may
    assert: a number or a name on the page is sourced, so the validator lets it through."""
    out = []
    for pg in [page] + list(page.get("more") or []):
        for k in ("description", "medium"):
            v = (pg or {}).get(k)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
    return out


def brief_from_state(state):
    f = state.get("facts") or {}
    blocks = state.get("blocks") or {}
    g = lambda k, default="": (f.get(k) if f.get(k) not in (None, "") else default)
    n = max(1, min(200, int(g("artworks", 1) or 1)))     # the writer's number; 200 only guards the loop
    series = g("series_name") if g("is_series") == "yes" else ""
    artworks = []
    for i in range(1, n + 1):
        title = (f.get(f"title_{i}") or "").strip() or ("Untitled" if series else f"Artwork {i}")
        artworks.append({"title": title, "card_line": (blocks.get(f"card_{i}") or "").strip()})
    surname = (g("artist").split() or ["Release"])[-1]
    surname = re.sub(r"[^A-Za-z0-9]", "", surname)
    launch = _dt(g("launch_at"))
    year = launch[2:4] if launch else datetime.date.today().strftime("%y")
    draw = g("mechanic") == "draw"
    features = [g(k) for k in ("f1", "f2", "f3", "f4", "f5") if g(k)]
    page_facts = page_text(state.get("page") or {})
    return {
        "outputs": ["ig-set", "twitter-set", "email-set", "artist-set"],
        "release": {
            "campaign_code": f"{surname}_{'LE' if draw else 'TL'}_{year}",
            "link": g("link"),
            "mechanic": "draw" if draw else "timed",
            "window": g("window", "one week"),
            "coming_soon_at": "", "announce_at": "", "sustain_at": "", "sustain2_at": "",
            "launch_at": launch,
            "halfway_at": "",
            "closes_at": _dt(g("closes_at")),
            "last_chance_at": "",
            "early_access_at": "",
            "early_access_code": g("early_access_code", "000-000"),
            "framing_code": g("framing_code"),
            "framing_percent": int(g("framing_percent", 10) or 10),
            "fundraiser": g("beneficiary"),
            "beneficiary_handle": g("beneficiary_handle"),
            "advisor": g("advisor", "Sam"),
            "social_dates": {k: _dt(v) for k, v in ((state.get("dates") or {}).get("social") or {}).items() if v},
            "email_dates": {k: _dt(v) for k, v in ((state.get("dates") or {}).get("email") or {}).items() if v},
        },
        "artist": {
            "name": g("artist"),
            "collab_with": g("collab_with") or g("artist"),
            "handle": g("handle"),
            "x_handle": g("x_handle"),
            "hashtag": g("hashtag"),
            "collaboration_ordinal": g("ordinal", "latest"),
            "quote": g("quote"),
            "voice": "third" if str(g("artist_voice")).startswith("third") else "first",
            "facts": [],
        },
        "edition": {
            "unit": g("unit", "print"),
            "count": n,
            "phrase": g("edition_phrase"),
            "series": series,
            "features": features or ["Signed by the artist", "Individually numbered"],
            "facts": [],
        },
        "artworks": artworks,
        "context": {
            "artist_bio": g("bio"),
            "hook": (blocks.get("hook") or "").strip(),
            "qualifier": (blocks.get("qualifier") or "").strip(),
            "opener": (state.get("opener") or "").strip(),
            "making": (blocks.get("making") or "").strip(),
            "facts": page_facts,
        },
    }


# The rendered sets, split into the items the comms plan names, so the page and Notion
# can address one item at a time.
_HEAD = {
    "ig-set": re.compile(r"^\[POST \d+ · (?P<name>[^·\]]+?) · (?P<send>\d{6})(?: · [^\]]*)?\]\s*$", re.M),
    "twitter-set": re.compile(r"^\[TWEET \d+ · (?P<name>[^·\]]+?) · (?P<send>\d{6})(?: · [^\]]*)?\]\s*$", re.M),
    "email-set": re.compile(r"^\[EMAIL \d+ · (?P<name>[^\]]+?) · (?P<send>\d{6})\]\s*$", re.M),
    "artist-set": re.compile(r"^\[ARTIST (?P<kind>POST|TWEET) \d+ · (?P<name>[^·\]]+?) · (?P<send>\d{6})(?: · [^\]]*)?\]\s*$", re.M),
}


def split_set(name, text):
    rx = _HEAD[name]
    heads = list(rx.finditer(text))
    items = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end].strip()
        body = re.sub(r"\n═+\s*$", "", body).strip()          # the rule between emails
        item = {"name": m.group("name").strip(), "send": m.group("send"), "text": body}
        if "kind" in m.groupdict():
            item["kind"] = m.group("kind").lower()
        items.append(item)
    return items
