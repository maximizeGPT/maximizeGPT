"""Weekly digest of upcoming events for prospective law school applicants.

Researches events with Claude (web search + web fetch), dedupes against
seen_events.json, and emails only new events.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import smtplib
import sys
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import config

STATE_FILE = Path(__file__).with_name("seen_events.json")
FIELDS = ["title", "organizer", "date", "end_date", "location", "format", "url",
          "registration_deadline", "cost", "why_relevant"]
NULLABLE = {"end_date", "registration_deadline"}

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    **{f: {"type": "string"} for f in FIELDS if f not in NULLABLE},
                    **{f: {"anyOf": [{"type": "string"}, {"type": "null"}]} for f in NULLABLE},
                    "format": {"type": "string", "enum": ["in-person", "virtual", "hybrid"]},
                },
                "required": FIELDS,
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}


# ---------- Research ----------

def research_prompt(today: date) -> str:
    until = today + timedelta(days=config.LOOKAHEAD_DAYS)
    lines = "\n".join(f"- {t}" for t in config.EVENT_TYPES)
    virtual = "Also include virtual events open to applicants anywhere." if config.INCLUDE_VIRTUAL else ""
    return f"""Today is {today.isoformat()}. I am a prospective law school applicant in the {config.APPLICATION_CYCLE} admissions cycle, based in {config.HOME_REGION}; the whole Bay Area (SF, Oakland, Berkeley, the Peninsula, San Jose) and Davis are within reach. {virtual}

Use web search and web fetch to find specific upcoming events dated between {today.isoformat()} and {until.isoformat()} of these types:
{lines}

Prioritize these schools: {", ".join(config.TARGET_SCHOOLS)}. Also check LSAC (lsac.org forums and events), AccessLex, CLEO, PLUS programs, and Bay Area university pre-law advising pages (Stanford, UC Berkeley, Cal State East Bay, SF State, San Jose State, Santa Clara, USF, UC Davis).

For each event, verify the date and get the official event or registration URL. Skip events that are past, undated, or for admitted students only. For each event report: title, organizer, start date (YYYY-MM-DD), end date if multi-day, location (city or "Online"), format (in-person, virtual, or hybrid), URL, registration deadline if any, cost, and one sentence on why it is relevant to me. Aim for breadth: list every qualifying event you find."""


def extraction_prompt(notes: str) -> str:
    return ("Convert these research notes into the JSON schema. Include only concrete events with a "
            "known start date and URL. Use YYYY-MM-DD dates, null for unknown end_date or "
            "registration_deadline, and \"Unknown\" for other unknown text fields.\n\n" + notes)


def _fallback_kwargs() -> dict:
    # Server-side refusal fallback: reroutes a declined request to another model automatically.
    return {"extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
            "extra_body": {"fallbacks": "default"}}


def research_events(client, today: date) -> str:
    """Run the web research turn and return Claude's final text notes."""
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": config.MAX_SEARCHES},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": config.MAX_FETCHES},
    ]
    messages = [{"role": "user", "content": research_prompt(today)}]
    for _ in range(6):
        with client.messages.stream(model=config.MODEL, max_tokens=64000, tools=tools,
                                    messages=messages, thinking={"type": "adaptive"},
                                    output_config={"effort": "high"}, **_fallback_kwargs()) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "refusal":
            raise RuntimeError("Research request was declined (refusal)")
        if resp.stop_reason != "pause_turn":
            return "\n".join(b.text for b in resp.content if b.type == "text")
        messages = messages[:1] + [{"role": "assistant", "content": resp.content}]
    raise RuntimeError("Research turn kept pausing; giving up")


def extract_events(client, notes: str) -> list[dict]:
    """Turn free-form notes into validated event dicts using structured output."""
    resp = client.messages.create(
        model=config.MODEL, max_tokens=16000,
        messages=[{"role": "user", "content": extraction_prompt(notes)}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EVENT_SCHEMA}},
        **_fallback_kwargs(),
    )
    if resp.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"Extraction stopped early: {resp.stop_reason}")
    return parse_events(next(b.text for b in resp.content if b.type == "text"))


def parse_events(text: str) -> list[dict]:
    """Parse model output (object with "events", or a bare list, optionally fenced) into events."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if not m:
            raise ValueError("No JSON found in model output")
        data = json.loads(m.group(1))
    items = data.get("events", []) if isinstance(data, dict) else data
    events = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not item.get("title") or not item.get("url"):
            continue
        ev = {f: (str(item[f]).strip() if item.get(f) not in (None, "") else None) for f in FIELDS}
        ev["format"] = (ev["format"] or "unknown").lower()
        if _parse_date(ev["date"]):
            events.append(ev)
    return events


# ---------- Filtering and dedupe ----------

def _parse_date(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s[:10]) if s else None
    except ValueError:
        return None


def upcoming(events: list[dict], today: date) -> list[dict]:
    """Keep events whose start (or end, for multi-day) is today or later."""
    return [e for e in events if (_parse_date(e["end_date"]) or _parse_date(e["date"])) >= today]


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query)
                             if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_"))))
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit(("https", host, parts.path.rstrip("/"), query, ""))


def event_key(ev: dict) -> str:
    raw = f"{normalize_url(ev['url'])}|{ev['date'][:10]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_state(path: Path = STATE_FILE) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def select_new(events: list[dict], state: dict, today: date) -> list[dict]:
    """Return unseen events (deduped within the batch too) and record them in state."""
    new = []
    for ev in events:
        k = event_key(ev)
        if k not in state:
            state[k] = {"title": ev["title"], "date": ev["date"][:10], "first_seen": today.isoformat()}
            new.append(ev)
    return new


def prune_state(state: dict, today: date, keep_days: int = 60) -> None:
    cutoff = today - timedelta(days=keep_days)
    for k in [k for k, v in state.items() if (_parse_date(v.get("date")) or today) < cutoff]:
        del state[k]


# ---------- Digest ----------

def is_local(ev: dict) -> bool:
    loc = (ev.get("location") or "").lower()
    return any(k in loc for k in config.LOCAL_KEYWORDS)


def group_events(events: list[dict]) -> list[tuple[str, list[dict]]]:
    groups = {"In-person: Bay Area (local)": [], "Virtual": [], "In-person: elsewhere": []}
    for ev in sorted(events, key=lambda e: (e["date"], e["title"])):
        if ev["format"] != "virtual" and is_local(ev):
            groups["In-person: Bay Area (local)"].append(ev)
        elif ev["format"] in ("virtual", "hybrid"):
            groups["Virtual"].append(ev)
        else:
            groups["In-person: elsewhere"].append(ev)
    return [(name, evs) for name, evs in groups.items() if evs]


def _when(ev: dict) -> str:
    return ev["date"] + (f" to {ev['end_date']}" if ev["end_date"] and ev["end_date"] != ev["date"] else "")


def _details(ev: dict) -> list[tuple[str, str]]:
    rows = [("When", _when(ev)), ("Where", f"{ev['location'] or 'Unknown'} ({ev['format']})"),
            ("Organizer", ev["organizer"]), ("Cost", ev["cost"]),
            ("Register by", ev["registration_deadline"]), ("Why", ev["why_relevant"])]
    return [(k, v) for k, v in rows if v]


def render_text(events: list[dict], today: date) -> str:
    out = [f"Law school events digest ({today.isoformat()}): {len(events)} new event(s)", ""]
    for name, evs in group_events(events):
        out += [f"== {name} ==", ""]
        for ev in evs:
            out.append(f"* {ev['title']}")
            out += [f"    {k}: {v}" for k, v in _details(ev)]
            out += [f"    Link: {ev['url']}", ""]
    return "\n".join(out)


def render_html(events: list[dict], today: date) -> str:
    e = html.escape
    parts = [f"<h2>Law school events digest ({today.isoformat()})</h2>",
             f"<p>{len(events)} new event(s) since the last digest.</p>"]
    for name, evs in group_events(events):
        parts.append(f"<h3>{e(name)}</h3>")
        for ev in evs:
            rows = "".join(f"<tr><td style='color:#666;padding-right:8px'>{e(k)}</td><td>{e(v)}</td></tr>"
                           for k, v in _details(ev))
            parts.append(f"<div style='margin-bottom:16px'><a href='{e(ev['url'], quote=True)}'>"
                         f"<b>{e(ev['title'])}</b></a><table style='font-size:14px'>{rows}</table></div>")
    return f"<html><body style='font-family:sans-serif'>{''.join(parts)}</body></html>"


# ---------- Email ----------

def send_email(subject: str, text: str, html_body: str) -> None:
    user, password, to = (os.environ.get(k) for k in ("SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO"))
    if not (user and password and to):
        raise RuntimeError("SMTP_USER, SMTP_PASSWORD and EMAIL_TO must be set")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    host, port = os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=60) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)


# ---------- Main ----------

def run(client, today: date, dry_run: bool = False, always_send: bool = False,
        state_path: Path = STATE_FILE) -> list[dict]:
    notes = research_events(client, today)
    events = upcoming(extract_events(client, notes), today)
    state = load_state(state_path)
    new = select_new(events, state, today)
    print(f"Found {len(events)} upcoming event(s), {len(new)} new.", file=sys.stderr)
    if new or always_send:
        subject = f"Law school events: {len(new)} new ({today.isoformat()})"
        text, html_body = render_text(new, today), render_html(new, today)
        if dry_run:
            print(f"Subject: {subject}\n\n{text}")
        else:
            send_email(subject, text, html_body)
    if not dry_run:
        prune_state(state, today)
        save_state(state, state_path)
    return new


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="print the digest; do not email or save state")
    p.add_argument("--always-send", action="store_true", help="send a digest even with no new events")
    args = p.parse_args(argv)
    import anthropic
    run(anthropic.Anthropic(), date.today(), dry_run=args.dry_run, always_send=args.always_send)


if __name__ == "__main__":
    main()
