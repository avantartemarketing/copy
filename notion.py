"""The comms plan in Notion: one row per item per channel, with a Copy field.

The database's property names and types are read from Notion rather than assumed, because
the export this was designed against shows the campaign and channel as rollups of relations,
and those cannot be filtered by text. Where a property can be filtered, it is; where it
cannot, the pages are read and filtered here.

    NOTION_PROP_CAMPAIGN   default "Campaign text"
    NOTION_PROP_CHANNEL    default "Channel Name"
    NOTION_PROP_COPY       default "Copy"

NOTION_DATABASE_ID is the plan database's id, or its address. When Notion finds no database by
it, the id is looked at before giving up: the page it names, if the plan is the one database
laid out on that page, stands in for it; anything else is an error that says what the id names,
which databases the integration can see, and so what to set or what to connect.
"""
import os
import re
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


_DB = {"at": 0.0, "db": None, "id": None}
_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}", re.I)


def _id(s):
    """The id in a setting, which may be the whole address of the plan: the last id before its ?v= view,
    in the dashed form Notion writes ids in."""
    found = _ID.findall((s or "").split("?")[0].split("#")[0])
    if not found:
        return (s or "").strip()
    i = found[-1].lower()
    return i if "-" in i else f"{i[:8]}-{i[8:12]}-{i[12:16]}-{i[16:20]}-{i[20:]}"


def database():
    """The plan's definition, cached for a minute: its properties, and where the campaign relation points."""
    if not _DB["db"] or time.time() - _DB["at"] > 60:
        db_id = _DB["id"] or _id(os.environ["NOTION_DATABASE_ID"])
        try:
            db = _call("GET", f"/databases/{db_id}")
        except NotionError as e:
            if "404" not in str(e):
                raise
            db = _locate(db_id, e)
        _DB.update(db=db, id=db["id"], at=time.time())
    return _DB["db"]


def _try(method, path, **kw):
    """A call whose refusal is itself an answer: None where Notion will not serve it."""
    try:
        return _call(method, path, **kw)
    except NotionError:
        return None


def _blocks(block_id, depth=0):
    """The blocks on a page, into its columns and toggles but no further: enough to find a database laid out on it."""
    cursor = None
    while True:
        res = _try("GET", f"/blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else ""))
        if not res:
            return
        for b in res.get("results", []):
            yield b
            if depth < 2 and b.get("has_children") and b.get("type") in ("column_list", "column", "toggle", "callout", "synced_block"):
                yield from _blocks(b["id"], depth + 1)
        if not res.get("has_more"):
            return
        cursor = res.get("next_cursor")


def _visible():
    """The databases the integration has been connected to, as (title, id)."""
    res = _try("POST", "/search", json={"filter": {"property": "object", "value": "database"}, "page_size": 100}) or {}
    return [("".join(t.get("plain_text", "") for t in d.get("title") or []).strip() or "untitled", d["id"])
            for d in res.get("results", []) if d.get("object") == "database"]


def _title(page):
    return next((plain(v) for v in (page.get("properties") or {}).values() if v.get("type") == "title"), "").strip() or "untitled"


def _locate(given, err):
    """Notion found no database by the configured id. The plan on the page the id names is used in its
    place; anything else is an error that says what the id names and what the integration can see."""
    page = _try("GET", f"/pages/{given}")
    seen = _visible()
    sees = (f" It can see {len(seen)} database{'s' if len(seen) != 1 else ''}: " + "; ".join(f"“{t}” {i}" for t, i in seen) + ".") if seen else ""
    if page:
        parent = page.get("parent") or {}
        if parent.get("type") == "database_id":
            raise NotionError(f"{err} That id is the row “{_title(page)}” of the database {parent['database_id']}; set NOTION_DATABASE_ID to that.")
        dbs = [b for b in _blocks(given) if b.get("type") == "child_database"]
        if len(dbs) == 1:
            return _call("GET", f"/databases/{dbs[0]['id']}")
        if dbs:
            raise NotionError(f"{err} That id is the page “{_title(page)}”, which holds {len(dbs)} databases; set NOTION_DATABASE_ID to the plan's: "
                              + "; ".join(f"“{(b.get('child_database') or {}).get('title') or 'untitled'}” {b['id']}" for b in dbs) + ".")
        raise NotionError(f"{err} That id is the page “{_title(page)}”, not a database, and none is laid out on it. If the plan there is a linked "
                          f"view of a database, open the plan as its own page and set NOTION_DATABASE_ID to the 32 characters before ?v= in its address.{sees}")
    if seen:
        raise NotionError(f"{err} Nothing the integration can see has that id.{sees} Either connect the plan to the integration in Notion "
                          "(··· at the top right of the plan, then Connections) or set NOTION_DATABASE_ID to the plan's id from that list.")
    raise NotionError(f"{err} The integration has not been connected to any database. In Notion, open the plan, choose ··· at the top right, "
                      "then Connections, and add the integration; then do the same for the campaigns database its Campaign column points to.")


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


def campaigns(limit=300):
    """The campaigns a row can belong to, most recently edited first, from the campaigns database."""
    _, db_id = campaign_relation()
    if not db_id:
        raise NotionError("The plan's campaign column is not a relation, so there is no list to choose from.")
    body = {"page_size": 100, "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
    out, cursor = [], None
    while len(out) < limit:
        if cursor:
            body["start_cursor"] = cursor
        try:
            res = _call("POST", f"/databases/{db_id}/query", json=body)
        except NotionError as e:
            if "404" in str(e):
                raise NotionError("The integration cannot see the campaigns database. In Notion, connect it to that database as well as the plan.")
            raise
        for pg in res.get("results", []):
            title = next((plain(v) for v in pg["properties"].values() if v.get("type") == "title"), "").strip()
            if title:
                out.append({"id": pg["id"], "name": title, "edited": (pg.get("last_edited_time") or "")[:10]})
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return out[:limit]


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


def rows_for_campaign(campaign="", campaign_id=""):
    """The plan's rows for one campaign: by the campaign page's id when chosen from the list, which is
    exact, or by text in the campaign column when typed, which matches by containment."""
    campaign, campaign_id = (campaign or "").strip(), (campaign_id or "").strip()
    if not campaign and not campaign_id:
        raise NotionError("No campaign chosen.")
    types = schema()
    p_camp, p_chan, p_copy = _prop("NOTION_PROP_CAMPAIGN", "Campaign text"), _prop("NOTION_PROP_CHANNEL", "Channel Name"), _prop("NOTION_PROP_COPY", "Copy")
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
            res = _call("POST", f"/databases/{database()['id']}/query", json=body)
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
        rows.append({
            "id": pg["id"], "name": plain(pr.get(title, {})), "channel": plain(pr.get(p_chan, {})),
            "campaign": camp, "status": plain(pr.get("Status", {})) if "Status" in pr else "",
            "has_copy": bool(plain(pr.get(p_copy, {})).strip()), "url": pg.get("url", ""),
        })
    return rows


def _key(channel, name):
    n = (name or "").strip().lower()
    return (channel or "").strip().lower(), CANON.get(n, n)


def push(campaign, items, campaign_id=""):
    """items: [{channel: ig|ig-insiders|twitter|email, name, text}]. Writes Copy on the matching row."""
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
