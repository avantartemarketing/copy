"""Copy Generator, served.

One small server so the page can run outside claude.ai: it serves the page, renders a
release through the same templates and validator as the command line, calls Claude with a
key that stays here, and reads and writes the comms plan in Notion.

    ANTHROPIC_API_KEY   for the two AI buttons; without it they explain themselves
    NOTION_TOKEN        an internal integration with access to the comms database
    NOTION_DATABASE_ID  the comms plan database
    APP_PASSWORD        if set, the whole app is behind a password (user: any)
    GOOGLE_CLIENT_ID    with GOOGLE_CLIENT_SECRET: sign in with Google instead of the password
    ALLOWED_DOMAINS     the Google accounts allowed in, by domain; default avantarte.com
    ALLOWED_EMAILS      optional, single addresses allowed in from other domains
    SECRET_KEY          signs the sign-in cookie; Render generates one from the blueprint
    PUBLIC_URL          only with a custom domain: where the app is reached, for Google's redirect
    CLAUDE_MODEL        default claude-fable-5-1
"""
import datetime
import hashlib
import json
import os
import pathlib
import secrets
import time
from urllib.parse import urlencode

import requests
from flask import Flask, Response, jsonify, redirect, render_template_string, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix

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
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)      # Render ends TLS in front of gunicorn; the app still sees https

MODEL = os.environ.get("CLAUDE_MODEL", "claude-fable-5-1")
PASSWORD = os.environ.get("APP_PASSWORD", "")

# ---------------------------------------------------------------- who may come in
# With a Google client, everyone signs in with a Google account on an allowed domain and gets a
# signed cookie for thirty days. Without one, the password stands, and without that the app is open.
GOOGLE_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
ALLOWED_DOMAINS = [d.strip().lower() for d in os.environ.get("ALLOWED_DOMAINS", "avantarte.com").split(",") if d.strip()]
ALLOWED_EMAILS = [e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()]
app.secret_key = os.environ.get("SECRET_KEY") or hashlib.sha256(("copy-generator:" + GOOGLE_SECRET + PASSWORD).encode()).hexdigest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
                  PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=30))
OPEN_PATHS = {"/api/health", "/favicon.ico", "/favicon.svg", "/login", "/auth/google", "/auth/callback", "/logout"}


def signed_in():
    u = session.get("user")
    return u if isinstance(u, dict) and u.get("email") else None


def allowed(email):
    email = (email or "").lower()
    return email in ALLOWED_EMAILS or ("@" in email and email.rsplit("@", 1)[1] in ALLOWED_DOMAINS)


def safe_next(n):
    """Only an address on this site: a path, never another host."""
    return n if n and n.startswith("/") and not n.startswith("//") and "\\" not in n else "/"


def public_url():
    """Where this app is reached from outside: PUBLIC_URL if set (a custom domain), else the address
    Render gives the service, else what the request says."""
    return (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or request.url_root).rstrip("/")


def callback_url():
    return public_url() + "/auth/callback"


@app.before_request
def gate():
    if request.path in OPEN_PATHS:                                   # Render's health check carries no sign-in
        return None
    if GOOGLE_ID:
        if signed_in():
            return None
        if request.path.startswith("/api/"):
            return jsonify(error="Signed out. Sign in again."), 401
        return redirect("/login?" + urlencode({"next": request.full_path.rstrip("?")}))
    if not PASSWORD:
        return None
    auth = request.authorization
    if auth and auth.password == PASSWORD:
        return None
    return Response("Copy Generator", 401, {"WWW-Authenticate": 'Basic realm="Copy Generator"'})


LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · Copy Generator</title>
<link rel="icon" type="image/png" sizes="64x64" href="/favicon.ico">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
:root{--paper:#FBFAF7;--surface:#FFFFFF;--line:#E5E2DA;--ink:#1C1B16;--ink-soft:#6E6B60;--accent:#1F3A5F;--accent-soft:#E7ECF3;--accent-line:#C3D0E2;--warn:#8F4327;--warn-soft:#F8EDE8}
@media (prefers-color-scheme:dark){:root{--paper:#161512;--surface:#1D1C18;--line:#343229;--ink:#EDEAE1;--ink-soft:#A19D91;--accent:#9BB8DC;--accent-soft:#222B37;--accent-line:#3A4757;--warn:#D99878;--warn-soft:#2E241E}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--paper);color:var(--ink);font:14px/1.5 "Instrument Sans",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:30px 34px 32px;max-width:380px;width:calc(100% - 32px);box-sizing:border-box}
.mark{font-family:"Newsreader",Georgia,"Times New Roman",serif;font-size:19px;letter-spacing:-.01em}
p{color:var(--ink-soft);margin:10px 0 0}
a.btn{display:block;margin-top:22px;padding:10px 14px;border:1px solid var(--accent-line);background:var(--accent-soft);color:var(--accent);border-radius:7px;text-align:center;text-decoration:none;font-weight:500}
.err{margin-top:16px;padding:10px 12px;border-radius:7px;background:var(--warn-soft);color:var(--warn)}
</style></head>
<body><div class="card"><span class="mark">Copy Generator</span>
<p>Sign in with your {{ domains }} Google account.</p>
{% if error %}<div class="err">{{ error }}</div>{% endif %}
<a class="btn" href="/auth/google?{{ query }}">Sign in with Google</a>
</div></body></html>
"""
LOGIN_ERRORS = {"domain": "That Google account is not one of ours. Sign in with your work account.",
                "state": "The sign-in did not complete. Try again.",
                "google": "Google did not sign you in. Try again."}


@app.get("/login")
def login():
    if not GOOGLE_ID:
        return redirect("/")
    nxt = safe_next(request.args.get("next"))
    if signed_in():
        return redirect(nxt)
    return render_template_string(LOGIN_PAGE, error=LOGIN_ERRORS.get(request.args.get("error", ""), ""),
                                  query=urlencode({"next": nxt}), domains=" or ".join(ALLOWED_DOMAINS))


@app.get("/auth/google")
def auth_google():
    if not GOOGLE_ID:
        return redirect("/")
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    session["next"] = safe_next(request.args.get("next"))
    params = {"client_id": GOOGLE_ID, "redirect_uri": callback_url(), "response_type": "code", "scope": "openid email profile",
              "state": state, "access_type": "online", "prompt": "select_account"}
    if len(ALLOWED_DOMAINS) == 1:
        params["hd"] = ALLOWED_DOMAINS[0]                            # a hint for Google's account chooser; the check is ours
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@app.get("/auth/callback")
def auth_callback():
    if not GOOGLE_ID:
        return redirect("/")
    if request.args.get("error") or not request.args.get("code"):
        return redirect("/login?error=google")
    if not request.args.get("state") or request.args.get("state") != session.pop("oauth_state", None):
        return redirect("/login?error=state")
    nxt = safe_next(session.pop("next", "/"))
    try:
        tok = requests.post("https://oauth2.googleapis.com/token", timeout=15,
                            data={"code": request.args["code"], "client_id": GOOGLE_ID, "client_secret": GOOGLE_SECRET,
                                  "redirect_uri": callback_url(), "grant_type": "authorization_code"}).json()
        if not tok.get("access_token"):
            raise ValueError(tok.get("error_description") or tok.get("error") or "no token")
        me = requests.get("https://openidconnect.googleapis.com/v1/userinfo", timeout=15,
                          headers={"Authorization": "Bearer " + tok["access_token"]}).json()
    except Exception as e:                                           # noqa: BLE001 - whatever Google said, the answer is the same
        app.logger.warning("Google sign-in failed: %s", e)
        return redirect("/login?error=google")
    email = (me.get("email") or "").lower()
    if not email or me.get("email_verified") is False or not allowed(email):
        return redirect("/login?error=domain")
    session.clear()
    session.permanent = True
    session["user"] = {"email": email, "name": me.get("name") or email.split("@")[0]}
    return redirect(nxt)


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login" if GOOGLE_ID else "/")


@app.get("/")
@app.get("/c/<cid>")
@app.get("/c/<cid>/<slug>")
def page(cid="", slug=""):
    """The one page; a campaign's address (/c/<id>/<name>) serves it too, and the page opens that campaign."""
    return send_from_directory(ROOT / "tool", "copy-generator.html")


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(ROOT / "tool", "favicon.png", mimetype="image/png")   # the pen nib; the page carries its own copy


@app.get("/favicon.svg")
def favicon_svg():
    return send_from_directory(ROOT / "tool", "favicon.svg", mimetype="image/svg+xml")


@app.get("/api/health")
def health():
    return jsonify(ok=True, claude=bool(os.environ.get("ANTHROPIC_API_KEY")), notion=notion.configured(), model=MODEL,
                   commit=os.environ.get("RENDER_GIT_COMMIT", "")[:7],      # which push is live; Render sets it
                   login="google" if GOOGLE_ID else "password" if PASSWORD else "open", user=signed_in())


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


def parse_json(text):
    """The JSON in a reply: as it is, or inside a code fence, or between the first brace and the last."""
    for candidate in (text, text.strip().strip("`").removeprefix("json").strip()):
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


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
    kwargs = dict(model=MODEL, max_tokens=8000, messages=[{"role": "user", "content": prompt}])
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
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        if response.stop_reason == "max_tokens":
            return jsonify(error="Claude's reply was cut off before the end. Try again."), 502
        data = parse_json(text) if schema else text
        if schema and data is None:
            app.logger.warning("Claude's reply was not JSON (%s): %r", response.stop_reason, text[:400])
            return jsonify(error="Claude's reply was not the JSON asked for. It began: " + (text.strip()[:160] or "(nothing)")), 502
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
    """The cached list, or with ?q= a search of every campaign, or with ?force=1 a fresh read."""
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    t0 = time.time()
    try:
        q = (request.args.get("q") or "").strip()
        lst = notion.search_campaigns(q) if q else notion.campaigns(force=request.args.get("force") == "1")
        app.logger.info("campaigns %s in %.2fs", "search" if q else "list", time.time() - t0)
        return jsonify(campaigns=lst, took=round(time.time() - t0, 2))
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
    t0 = time.time()
    try:
        rows = notion.rows_for_campaign(body.get("campaign", ""), body.get("campaign_id", ""))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 502
    app.logger.info("rows for %s in %.2fs", body.get("campaign_id") or body.get("campaign"), time.time() - t0)
    return jsonify(rows=rows, took=round(time.time() - t0, 2))


@app.post("/api/notion/write")
def api_notion_write():
    """rows: [{id, text}], written by row id: the page decided which row gets what."""
    if not notion.configured():
        return jsonify(error="Notion is not configured on this server: set NOTION_TOKEN and NOTION_DATABASE_ID."), 503
    body = request.get_json(force=True) or {}
    try:
        return jsonify(notion.write_rows(body.get("rows") or []))
    except notion.NotionError as e:
        return jsonify(error=str(e)), 502


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
