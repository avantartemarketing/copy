#!/usr/bin/env python3
"""
Proof of concept: release brief (YAML) + template (Jinja2) -> email copy, then validate.

Deterministic. Nothing in this file calls an AI. The only free text is what the
brief carries in its BOUNDED fields, which a human writes or an AI produces under
prompts/slot-contract.md. Either way validate.py checks it before anyone sees it.

Usage:
  python3 render.py briefs/robert-longo-le-26.yaml all
  python3 render.py briefs/robert-longo-le-26.yaml announcement-le
"""
import datetime
import pathlib
import re
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from validate import validate

ROOT = pathlib.Path(__file__).resolve().parent

# --- MENUS: the only "variation" the tool has. Extend the lists; never let an AI invent an opener.
OPENERS = {
    "delighted": "We're delighted to announce",
    "proud": "We're proud to present",
    "moon": "We are over the moon to announce",
}
EA_OPENERS = {
    "preparing": "We're currently preparing the launch of",
    "share": "I'm delighted to share",
    "unveil": "We will soon be unveiling",
}
GROUP = {2: "pair", 3: "trio", 4: "quartet", 6: "sextet", 7: "septet"}      # "A trio of prints by …"
NEW = {1: "a new", 2: "a pair of new", 3: "a trio of new", 4: "a quartet of new",
       5: "five new", 6: "six new", 7: "a septet of new"}
COLLECT = {1: "a", 2: "a pair of", 3: "a trio of", 4: "a quartet of", 5: "five", 6: "six", 7: "a septet of"}
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}


def dt(v):
    return v if isinstance(v, datetime.datetime) else datetime.datetime.fromisoformat(str(v))


# --- FILTERS: every date and time in every email goes through one of these, so formats cannot drift.
def uktime(v):
    return dt(v).strftime("%H:%M UK time")


def ukdate(v):
    return dt(v).strftime("%-d %B")                 # 29 September   (marketing emails)


def ukdate_dd(v):
    return dt(v).strftime("%d %B")                  # 02 July        (Now Live, post-purchase)


def weekday(v):
    return dt(v).strftime("%A")


def ddmmyy(v):
    return dt(v).strftime("%d%m%y")                 # HubSpot internal-name prefix


def day_before(v):
    return dt(v) - datetime.timedelta(days=1)


def ship_window(w):
    a, b = dt(w["from"]), dt(w["to"])               # "23 - 30 October" / "26 October - 03 November"
    return f"{a:%d} - {b:%d %B}" if a.month == b.month else f"{a:%d %B} - {b:%d %B}"


def _noun(ed, plural):
    medium = (ed.get("medium_prefix") or "").strip()
    return (f"{medium} {ed['unit']}".strip()) + ("s" if plural else "")


def edition_phrase(ed):
    """'a new limited edition silkscreen print' / 'a trio of new limited edition prints'"""
    n = ed["count"]
    return f"{NEW[n]} limited edition {_noun(ed, n > 1)}"


def collect_phrase(ed):
    """'a limited edition silkscreen print' / 'a trio of limited edition prints'"""
    n = ed["count"]
    return f"{COLLECT[n]} limited edition {_noun(ed, n > 1)}"


def recap_phrase(ed):
    """'a new limited edition silkscreen print' / 'three limited edition prints'  (Last Chance opener)"""
    n = ed["count"]
    return edition_phrase(ed) if n == 1 else f"{WORDS[n]} limited edition {_noun(ed, True)}"


def titles(artworks):
    t = [a["title"] for a in artworks]
    return t[0] if len(t) == 1 else ", ".join(t[:-1]) + " and " + t[-1]


def auth_phrase(ed, artist):
    kind = ed.get("signed_by", "artist")
    if kind == "artist":
        return "signed by the artist"
    if kind == "estate_stamp":
        return f"authenticated with a bespoke debossed {artist['partner']} stamp"
    if kind == "engraved":
        return "authenticated with the artist's engraved signature"
    return ""


def production_paragraph(ed, artist):
    """Assembled from typed fields. The optional technique sentence is a BOUNDED slot in the brief."""
    parts = []
    if ed.get("technique_sentence"):
        parts.append(ed["technique_sentence"].strip())
    if ed.get("size"):
        bits = [f"Each {ed['unit']} is released in a limited edition of {ed['size']}"]
        if ed.get("numbered", True):
            bits.append("individually numbered")
        if auth_phrase(ed, artist):
            bits.append(auth_phrase(ed, artist))
        parts.append(", ".join(bits[:-1]) + (" and " + bits[-1] if len(bits) > 1 else bits[0]) + ".")
    return " ".join(parts)


def build_env():
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(uktime=uktime, ukdate=ukdate, ukdate_dd=ukdate_dd, weekday=weekday, ddmmyy=ddmmyy,
                       day_before=day_before, ship_window=ship_window, edition_phrase=edition_phrase,
                       collect_phrase=collect_phrase, recap_phrase=recap_phrase, titles=titles)
    env.globals.update(OPENERS=OPENERS, EA_OPENERS=EA_OPENERS, GROUP=GROUP, WORDS=WORDS,
                       production_paragraph=production_paragraph)
    return env


def render(brief, name):
    text = build_env().get_template(name + ".txt").render(**brief)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    brief_path, which = sys.argv[1], sys.argv[2]
    brief = yaml.safe_load(open(brief_path, encoding="utf-8"))
    names = brief["emails"] if which == "all" else [which]
    out_dir = ROOT / "out" / pathlib.Path(brief_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for name in names:
        text = render(brief, name)
        (out_dir / f"{name}.txt").write_text(text, encoding="utf-8")
        errors, warnings = validate(text, brief)
        failed = failed or bool(errors)
        print(f"[{'BLOCKED' if errors else 'ok'}] {out_dir.relative_to(ROOT)}/{name}.txt")
        for e in errors:
            print("    error:  ", e)
        for w in warnings:
            print("    warning:", w)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
