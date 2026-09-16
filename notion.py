"""The comms plan in Notion: one row per item per channel, with a Copy field.

The database's property names and types are read from Notion rather than assumed, because
the export this was designed against shows the campaign and channel as rollups of relations,
and those cannot be filtered by text. Where a property can be filtered, it is; where it
cannot, the pages are read and filtered here.

    NOTION_PROP_CAMPAIGN   default "Campaign text"
    NOTION_PROP_CHANNEL    default "Channel Name"
    NOTION_PROP_COPY       default "Copy"
"""
import datetime
import json
import os
import re
import threading
import time

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# the plan's several names for one phase, and the templates' own, all read as one key
CANON = {"announcement": "announce", "announcement post": "announce",
         "now live": "live", "launch": "live", "launch (collab)": "live",
         "halfway through": "still time", "halfway": "still time",
         "sustain post": "sustain", "sustain 1": "sustain", "sustain, the making": "sustain", "sustain, the artist's words": "sustain",
         "tease": "coming soon"}
ALIAS = {}
CHANNELS = {"ig": "IG Main · Post", "ig-insiders": "IG Ins · Post", "twitter": "Twitter", "email": "AA Email",
            "artist-ig": "Artist IG · Post", "artist-twitter": "Artist Twitter"}


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
    return [n]


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


_DB = {"at": 0.0, "db": None}


def database():
    """The plan's definition, cached for a minute: its properties, and where the campaign relation points."""
    if not _DB["db"] or time.time() - _DB["at"] > 60:
        _DB["db"] = _call("GET", f"/databases/{os.environ['NOTION_DATABASE_ID']}")
        _DB["at"] = time.time()
    return _DB["db"]


def schema():
    return {k: v["type"] for k, v in database()["properties"].items()}


def campaign_relation():
    """The relation property that names a row's campaign and the database it points to, as (name, id).
    The configured campaign property is usually a rollup of that relation; it may be the relation itself."""
    props = database()["properties"]
    p = props.get(_prop("NOTION_PROP_CAMPAIGN", "Campaign text")) or {}
    if p.get("type") == "rollup":
        p = props.get((p.get("rollup") or {}).get("relation_property_name") or "") or {}
    if p.get("type") != "relation":
        p = next((v for k, v in props.items() if v.get("type") == "relation" and "campaign" in k.lower()), {})
    if p.get("type") != "relation":
        return None, None
    return p.get("name"), (p.get("relation") or {}).get("database_id")


STATE_PROP = "NOTION_PROP_STATE"                      # the campaigns database's text property that holds a draft
CHUNK = 2000                                            # Notion's cap on one rich text item
_CDB = {"at": 0.0, "id": None, "db": None}


def campaigns_db():
    """The campaigns database the plan's rows point to, with its definition cached for a minute."""
    _, db_id = campaign_relation()
    if not db_id:
        raise NotionError("The plan's campaign column is not a relation, so there is no campaigns database to read.")
    if _CDB["id"] != db_id or not _CDB["db"] or time.time() - _CDB["at"] > 60:
        try:
            _CDB.update(id=db_id, db=_call("GET", f"/databases/{db_id}"), at=time.time())
        except NotionError as e:
            if "404" in str(e):
                raise NotionError("The integration cannot see the campaigns database. In Notion, connect it to that database as well as the plan.")
            raise
    return db_id, _CDB["db"]


def state_property():
    """The property a draft is kept in: (name, id). Missing, it says what to add in Notion."""
    _, db = campaigns_db()
    name = _prop(STATE_PROP, "Copy generator")
    prop = db["properties"].get(name)
    if not prop:
        raise NotionError(f"Drafts need a text property called “{name}” on the campaigns database. Add one in Notion (type Text), then try again; you can hide it from every view.")
    if prop.get("type") != "rich_text":
        raise NotionError(f"“{name}” on the campaigns database is a {prop.get('type')} property; a draft needs a Text property.")
    return name, prop["id"]


def _saved_at(prop):
    """The draft's own timestamp, kept at the front of its JSON so the first chunk carries it."""
    text = plain(prop or {}).strip()
    if not text:
        return None
    m = re.match(r'\{"savedAt":"([^"]+)"', text)
    return m.group(1) if m else ""


def _campaign_rows(res):
    state = _prop(STATE_PROP, "Copy generator")
    out = []
    for pg in res.get("results", []):
        title = next((plain(v) for v in pg["properties"].values() if v.get("type") == "title"), "").strip()
        if title:
            saved = _saved_at(pg["properties"].get(state)) if state in pg["properties"] else None
            props = pg["properties"]
            find = lambda rx: next((plain(v) for k, v in props.items() if re.search(rx, k, re.I) and plain(v)), "")
            out.append({"id": pg["id"], "name": title, "edited": (pg.get("last_edited_time") or "")[:10],
                        "has_draft": saved is not None, "saved_at": saved or None,
                        "dates": {"tease": find(r"^tease date"), "announce": find(r"^announce date"), "launch": find(r"^launch date"), "live": find(r"^live date")}})
    return out


_CAMPS = {"at": 0.0, "list": None, "lock": threading.Lock(), "refreshing": False}
CAMPS_FRESH, CAMPS_STALE = 120, 3600                    # served as is for two minutes; refreshed behind the answer for an hour


def _fetch_campaigns(limit=100):
    """One request: the hundred most recently edited campaigns, which covers months of releases."""
    db_id, _ = campaigns_db()
    res = _call("POST", f"/databases/{db_id}/query", json={"page_size": min(100, limit), "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]})
    return _campaign_rows(res)


def campaigns(force=False):
    """The campaigns, most recently edited first, from a cache that Notion's latency never shows through:
    a fresh list is answered at once; a stale one is answered at once and refreshed behind it."""
    age = time.time() - _CAMPS["at"]
    if _CAMPS["list"] is not None and not force and age < CAMPS_STALE:
        if age > CAMPS_FRESH and not _CAMPS["refreshing"]:
            _CAMPS["refreshing"] = True
            threading.Thread(target=_refresh_campaigns, daemon=True).start()
        return _CAMPS["list"]
    lst = _fetch_campaigns()
    _CAMPS.update(list=lst, at=time.time())
    return lst


def _refresh_campaigns():
    try:
        _CAMPS.update(list=_fetch_campaigns(), at=time.time())
    except Exception:
        pass
    finally:
        _CAMPS["refreshing"] = False


def search_campaigns(q):
    """Every campaign whose name contains q, for the ones older than the cached hundred."""
    db_id, db = campaigns_db()
    title = next(k for k, v in db["properties"].items() if v.get("type") == "title")
    res = _call("POST", f"/databases/{db_id}/query", json={"page_size": 50, "filter": {"property": title, "title": {"contains": q}},
                                                            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]})
    return _campaign_rows(res)


def note_draft(campaign_id, saved_at):
    """A draft was just saved: the cached list says so without a round trip."""
    for c in _CAMPS["list"] or []:
        if c["id"] == campaign_id:
            c["has_draft"], c["saved_at"] = True, saved_at


def draft(campaign_id):
    """The draft saved on a campaign's page, or None."""
    _, prop_id = state_property()
    parts, cursor = [], None
    item = lambda x: (x.get("rich_text") or {}).get("plain_text", "") if isinstance(x.get("rich_text"), dict) else plain(x)   # a property item holds one rich text object
    while True:
        res = _call("GET", f"/pages/{campaign_id}/properties/{prop_id}" + (f"?start_cursor={cursor}" if cursor else ""))
        if res.get("object") == "property_item":                  # a short value comes back whole
            parts.append(item(res))
            break
        parts += [item(x) for x in res.get("results", [])]
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    text = "".join(parts).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        raise NotionError("The draft saved on this campaign could not be read; it may have been edited by hand in Notion.")


def save_draft(campaign_id, state, who=""):
    """Writes the draft onto the campaign's page, in chunks of 2000 characters, its timestamp first."""
    name, _ = state_property()
    body = {"savedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "savedBy": who}
    body.update({k: v for k, v in (state or {}).items() if k not in ("savedAt", "savedBy")})
    text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    chunks = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]
    if len(chunks) > 100:
        raise NotionError("The draft is too large to save on the campaign page.")
    _call("PATCH", f"/pages/{campaign_id}", json={"properties": {name: {"rich_text": [{"type": "text", "text": {"content": c}} for c in chunks]}}})
    note_draft(campaign_id, body["savedAt"])
    return body["savedAt"]


def plain(prop):
    """The text of a property, whatever its type; a property_item envelope reads the same."""
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
    if t == "checkbox":
        return "Yes" if prop.get("checkbox") else "No"
    if t == "date":
        return ((prop.get("date") or {}).get("start") or "")[:16]
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


def rows_for_campaign(campaign="", campaign_id=""):
    """The plan's rows for one campaign: by the campaign page's id when chosen from the list, which is
    exact, or by text in the campaign column when typed, which matches by containment."""
    campaign, campaign_id = (campaign or "").strip(), (campaign_id or "").strip()
    if not campaign and not campaign_id:
        raise NotionError("No campaign chosen.")
    types = schema()
    p_camp, p_chan, p_copy = _prop("NOTION_PROP_CAMPAIGN", "Campaign text"), _prop("NOTION_PROP_CHANNEL", "Channel Name"), _prop("NOTION_PROP_COPY", "Copy")
    p_needs, p_date, p_phase = _prop("NOTION_PROP_NEEDS", "Needs copy"), _prop("NOTION_PROP_DATE", "Live Date"), _prop("NOTION_PROP_PHASE", "Campaign Phase")
    for p in (p_camp, p_chan, p_copy):
        if p not in types:
            raise NotionError(f"The database has no property called “{p}”. It has: {', '.join(sorted(types))}.")
    title = next(k for k, t in types.items() if t == "title")
    if campaign_id:
        rel, _ = campaign_relation()
        if not rel:
            raise NotionError("The plan has no campaign relation to look rows up by.")
        flt = {"property": rel, "relation": {"contains": campaign_id}}
    else:
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
            if flt and not campaign_id and "400" in str(e) and not cursor:
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
        if not flt and not campaign_id and campaign.lower() not in camp.lower():
            continue
        copy = plain(pr.get(p_copy, {})).strip()
        needs = plain(pr[p_needs]).strip().lower() if p_needs in pr else ""
        rows.append({
            "id": pg["id"], "name": plain(pr.get(title, {})), "channel": plain(pr.get(p_chan, {})),
            "campaign": camp, "status": plain(pr.get("Status", {})) if "Status" in pr else "",
            "has_copy": bool(copy), "copy": copy, "url": pg.get("url", ""),
            "needs_copy": None if p_needs not in pr else needs in ("yes", "true", "✓", "checked", "1"),   # None: the plan has no such column
            "live_date": plain(pr[p_date]) if p_date in pr else "",
            "phase": plain(pr[p_phase]) if p_phase in pr else "",
        })
    rows.sort(key=lambda r: (r["phase"], r["live_date"], r["channel"], r["name"]))
    return rows


def _key(channel, name):
    n = (name or "").strip().lower()
    return (channel or "").strip().lower(), CANON.get(n, n)


def write_rows(rows):
    """rows: [{id, text}]. Writes each text into that row's Copy, in chunks of 2000 characters."""
    p_copy = _prop("NOTION_PROP_COPY", "Copy")
    types = schema()
    if types.get(p_copy) != "rich_text":
        raise NotionError(f"“{p_copy}” is a {types.get(p_copy)} property; Copy must be rich text to be written.")
    written, failed = [], []
    for r in rows:
        text = (r.get("text") or "").strip()
        chunks = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)] or [""]
        try:
            _call("PATCH", f"/pages/{r['id']}", json={"properties": {p_copy: {"rich_text": [{"type": "text", "text": {"content": c}} for c in chunks]}}})
            written.append(r["id"])
        except NotionError as e:
            failed.append({"id": r["id"], "error": str(e)})
    return {"written": written, "failed": failed}


def push(campaign, items, campaign_id=""):
    """items: [{channel: ig|ig-insiders|twitter|email, name, text}]. Writes Copy on the matching row, by name."""
    p_copy = _prop("NOTION_PROP_COPY", "Copy")
    types = schema()
    if types.get(p_copy) != "rich_text":
        raise NotionError(f"“{p_copy}” is a {types.get(p_copy)} property; Copy must be rich text to be written.")
    rows = rows_for_campaign(campaign, campaign_id)
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
