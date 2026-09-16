"""Copy Generator, served.

One small server so the page can run outside claude.ai: it serves the page, renders a
release through the same templates and validator as the command line, calls Claude with a
key that stays here, and reads and writes the comms plan in Notion.

    ANTHROPIC_API_KEY   for the two AI buttons; without it they explain themselves
    NOTION_TOKEN        an internal integration with access to the comms database
    NOTION_DATABASE_ID  the comms plan database
    APP_PASSWORD        if set, the whole app is behind a password (user: any)
    CLAUDE_MODEL        default claude-opus-5
"""
import json
import os
import pathlib

from flask import Flask, Response, jsonify, request, send_from_directory

from bridge import brief_from_state, split_set
from render import render
from validate import validate
import notion

ROOT = pathlib.Path(__file__).resolve().parent


def _dotenv(path=ROOT / ".env"):
    """A local .env, for running on a laptop; Render sets the variables itself. Never committed."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_dotenv()
app = Flask(__name__, static_folder=None)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")
PASSWORD = os.environ.get("APP_PASSWORD", "")


@app.before_request
def gate():
    if not PASSWORD or request.path in ("/api/health", "/favicon.ico"):   # Render's health check has no password
        return None
    auth = request.authorization
    if auth and auth.password == PASSWORD:
        return None
    return Response("Copy Generator", 401, {"WWW-Authenticate": 'Basic realm="Copy Generator"'})


@app.get("/")
def page():
    return send_from_directory(ROOT / "tool", "copy-generator.html")


@app.get("/favicon.ico")
def favicon():
    return Response(status=204)


@app.get("/api/health")
def health():
    return jsonify(ok=True, claude=bool(os.environ.get("ANTHROPIC_API_KEY")), notion=notion.configured(), model=MODEL,
                   commit=os.environ.get("RENDER_GIT_COMMIT", "")[:7])      # which push is live; Render sets it


# ------------------------------------------------------------------ the templates, as the page sees them
@app.post("/api/render")
def api_render():
    state = request.get_json(force=True) or {}
    brief = brief_from_state(state)
    out, errors, warnings = {}, [], []
    for name in brief["outputs"]:
        try:
            text = render(brief, name)
        except Exception as e:                       # a missing fact reads as a template error, say which
            return jsonify(error=f"{name}: {e}", brief=brief), 400
        e, w = validate(text, brief)
        errors += e
        warnings += w
        if name == "artist-set":                     # one template, two channels
            items = split_set(name, text)
            out["artist-posts"] = [i for i in items if i["kind"] == "post"]
            out["artist-tweets"] = [i for i in items if i["kind"] == "tweet"]
        else:
            out[name] = split_set(name, text)
    return jsonify(outputs=out, errors=errors, warnings=warnings, brief=brief)


# ------------------------------------------------------------------ Claude, with the key kept here
def _client():
    import anthropic
    return anthropic.Anthropic()


@app.post("/api/claude")
def api_claude():
    """The page sends the prompt it built and the JSON shape it wants back."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify(error="Claude is not configured on this server: set ANTHROPIC_API_KEY."), 503
    body = request.get_json(force=True) or {}
    prompt, schema = body.get("prompt", ""), body.get("schema")
    if not prompt.strip():
        return jsonify(error="Nothing to send."), 400
    import anthropic
    kwargs = dict(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    if schema:
        kwargs["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
    try:
        client = _client()
        try:
            # a refusal, unlikely for copy about artworks, is re-run on a fallback model by the server
            response = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except (anthropic.BadRequestError, TypeError):
            response = client.messages.create(**kwargs)
        if response.stop_reason == "refusal":
            return jsonify(error="Claude declined this request."), 502
        text = next((b.text for b in response.content if b.type == "text"), "")
        data = json.loads(text) if schema else text
        return jsonify(result=data, usage={"in": response.usage.input_tokens, "out": response.usage.output_tokens})
    except anthropic.AuthenticationError:
        return jsonify(error="The server's Anthropic key was rejected."), 503
    except anthropic.RateLimitError:
        return jsonify(error="Rate limited. Try again in a moment."), 429
    except anthropic.APIStatusError as e:
        return jsonify(error=f"Claude returned {e.status_code}: {e.message}"), 502
    except anthropic.APIConnectionError:
        return jsonify(error="Could not reach Claude."), 502
    except (json.JSONDecodeError, StopIteration):
        return jsonify(error="Claude's reply was not the JSON asked for."), 502


# ------------------------------------------------------------------ Notion: the comms plan's rows
@app.get("/api/notion/campaigns")
def api_notion_campaigns():
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    try:
        return jsonify(campaigns=notion.campaigns())
    except notion.NotionError as e:
        return jsonify(error=str(e)), 502


@app.get("/api/notion/draft/<campaign_id>")
def api_notion_draft(campaign_id):
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    try:
        return jsonify(state=notion.draft(campaign_id))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 409 if "property" in str(e) else 502


@app.put("/api/notion/draft/<campaign_id>")
def api_notion_save(campaign_id):
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    body = request.get_json(force=True) or {}
    try:
        return jsonify(saved_at=notion.save_draft(campaign_id, body.get("state") or {}, (request.authorization.username if request.authorization else "") or ""))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 409 if "property" in str(e) else 502


@app.post("/api/notion/rows")
def api_notion_rows():
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    body = request.get_json(force=True) or {}
    try:
        rows = notion.rows_for_campaign(body.get("campaign", ""), body.get("campaign_id", ""))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 502
    return jsonify(rows=rows)


@app.post("/api/notion/push")
def api_notion_push():
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    body = request.get_json(force=True) or {}
    try:
        result = notion.push(body.get("campaign", ""), body.get("items") or [], body.get("campaign_id", ""))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 502
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), debug=False)
