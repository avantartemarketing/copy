"""The comms plan in Notion: one row per item per channel, with a Copy field.

The database's property names and types are read from Notion rather than assumed, because
the export this was designed against shows the campaign and channel as rollups of relations,
and those cannot be filtered by text. Where a property can be filtered, it is; where it
cannot, the pages are read and filtered here.

    NOTION_PROP_CAMPAIGN   default "Campaign text"
    NOTION_PROP_CHANNEL    default "Channel Name"
    NOTION_PROP_COPY       default "Copy"
"""
import os

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# the templates' names for items, against the plan's own
ALIAS = {"announce": "announcement", "live": "now live", "still time": "halfway through",
         "sustain, the artist's words": "sustain", "sustain, the making": "sustain"}
CHANNELS = {"ig": "IG Main · Post", "ig-insiders": "IG Ins · Post", "twitter": "Twitter", "email": "AA Email"}


def plan_names(name):
    """The plan's row names an item may be filed under. An email name from the templates can
    carry a suffix the plan does not, or stand for two rows at once."""
    n = (name or "").strip()
    for suffix in (", signed by the advisor", ", this release's paragraph"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    if "(TL Flow and Non-flow)" in n:
        return [n.replace("(TL Flow and Non-flow)", "(TL Flow)"), n.replace("(TL Flow and Non-flow)", "(TL Non-flow)")]
    if " · " in n:
        return [x.strip() for x in n.split(" · ")]
    low = n.lower()
    return [ALIAS.get(low, n)]


class NotionError(Exception):
    pass


def configured():
    return bool(os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_DATABASE_ID"))


def _h():
    return {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}", "Notion-Version": VERSION, "Content-Type": "application/json"}


def _call(method, path, **kw):
    r = requests.request(method, API + path, headers=_h(), timeout=30, **kw)
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        raise NotionError(f"Notion {r.status_code}: {msg}")
    return r.json()


def _prop(name, default):
    return os.environ.get(name, default)


def schema():
    db = _call("GET", f"/databases/{os.environ['NOTION_DATABASE_ID']}")
    return {k: v["type"] for k, v in db["properties"].items()}


def plain(prop):
    """The text of a property, whatever its type."""
    t = prop.get("type")
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in prop.get(t) or [])
    if t == "formula":
        f = prop.get("formula") or {}
        return str(f.get(f.get("type"), "") or "")
    if t == "rollup":
        r = prop.get("rollup") or {}
        if r.get("type") == "array":
            return " ".join(plain(x) for x in r.get("array") or [])
        return str(r.get(r.get("type"), "") or "")
    if t == "select":
        return (prop.get("select") or {}).get("name", "") or ""
    if t == "status":
        return (prop.get("status") or {}).get("name", "") or ""
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in prop.get("multi_select") or [])
    return ""


def _filter(name, ptype, text):
    """A Notion filter for 'this property contains text', or None where the type cannot be filtered so."""
    if ptype in ("title", "rich_text"):
        return {"property": name, ptype: {"contains": text}}
    if ptype == "formula":
        return {"property": name, "formula": {"string": {"contains": text}}}
    if ptype == "rollup":
        return {"property": name, "rollup": {"any": {"rich_text": {"contains": text}}}}
    return None


def rows_for_campaign(campaign):
    campaign = (campaign or "").strip()
    if not campaign:
        raise NotionError("No campaign name given.")
    types = schema()
    p_camp, p_chan, p_copy = _prop("NOTION_PROP_CAMPAIGN", "Campaign text"), _prop("NOTION_PROP_CHANNEL", "Channel Name"), _prop("NOTION_PROP_COPY", "Copy")
    for p in (p_camp, p_chan, p_copy):
        if p not in types:
            raise NotionError(f"The database has no property called “{p}”. It has: {', '.join(sorted(types))}.")
    title = next(k for k, t in types.items() if t == "title")
    flt = _filter(p_camp, types[p_camp], campaign)
    body = {"page_size": 100}
    if flt:
        body["filter"] = flt
    pages, cursor, fetched = [], None, 0
    while True:
        if cursor:
            body["start_cursor"] = cursor
        try:
            res = _call("POST", f"/databases/{os.environ['NOTION_DATABASE_ID']}/query", json=body)
        except NotionError as e:
            # a rollup of a title, say, refuses the text filter: read the rows and filter here instead
            if flt and "400" in str(e) and not cursor:
                flt = None
                body.pop("filter", None)
                continue
            raise
        pages += res.get("results", [])
        fetched += len(res.get("results", []))
        if not res.get("has_more") or fetched >= 2000:
            break
        cursor = res.get("next_cursor")
    rows = []
    for pg in pages:
        pr = pg["properties"]
        camp = plain(pr.get(p_camp, {}))
        if not flt and campaign.lower() not in camp.lower():
            continue
        rows.append({
            "id": pg["id"], "name": plain(pr.get(title, {})), "channel": plain(pr.get(p_chan, {})),
            "campaign": camp, "status": plain(pr.get("Status", {})) if "Status" in pr else "",
            "has_copy": bool(plain(pr.get(p_copy, {})).strip()), "url": pg.get("url", ""),
        })
    return rows


def _key(channel, name):
    n = (name or "").strip().lower()
    return (channel or "").strip().lower(), ALIAS.get(n, n)


def push(campaign, items):
    """items: [{channel: ig|ig-insiders|twitter|email, name, text}]. Writes Copy on the matching row."""
    p_copy = _prop("NOTION_PROP_COPY", "Copy")
    types = schema()
    if types.get(p_copy) != "rich_text":
        raise NotionError(f"“{p_copy}” is a {types.get(p_copy)} property; Copy must be rich text to be written.")
    rows = rows_for_campaign(campaign)
    names = sorted({r["campaign"] for r in rows})
    if len(names) > 1:                               # "Grayson Perry" would match two campaigns; never write into both
        raise NotionError(f"“{campaign}” matches {len(names)} campaigns: {' / '.join(names)}. Use a name that matches one.")
    by = {}
    for r in rows:
        by.setdefault(_key(r["channel"], r["name"]), []).append(r)
    written, unmatched = [], []
    for it in items:
        # an Instagram caption goes to the main feed and, where the plan has a row for it, to Insiders
        channels = ["IG Main · Post", "IG Ins · Post"] if it.get("channel") == "ig" else [CHANNELS.get(it.get("channel", ""), it.get("channel", ""))]
        text = (it.get("text") or "").strip()
        chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)] or [""]   # Notion's per-block cap
        hits = []
        for channel in channels:
            for c in plan_names(it.get("name", "")):
                hits += by.get(_key(channel, c)) or []
        if not hits:
            unmatched.append({"channel": channels[0], "name": it.get("name", "")})
            continue
        for hit in hits:
            _call("PATCH", f"/pages/{hit['id']}", json={"properties": {p_copy: {"rich_text": [{"type": "text", "text": {"content": c}} for c in chunks]}}})
            written.append({"channel": hit["channel"], "name": hit["name"], "url": hit["url"]})
    return {"written": written, "unmatched": unmatched, "rows": len(rows)}
