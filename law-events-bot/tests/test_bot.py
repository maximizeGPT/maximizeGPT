import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot  # noqa: E402

TODAY = date(2026, 10, 5)


def ev(**kw):
    base = dict(title="Event", organizer="Org", date="2026-10-20", end_date=None, location="Online",
                format="virtual", url="https://example.com/e", registration_deadline=None,
                cost="Free", why_relevant="Relevant.")
    return {**base, **kw}


# ---------- JSON parsing ----------

def test_parse_object_and_normalizes_fields():
    text = json.dumps({"events": [ev(format="Virtual", end_date="", cost=None)]})
    [e] = bot.parse_events(text)
    assert e["format"] == "virtual" and e["end_date"] is None and e["cost"] is None


def test_parse_fenced_list_and_skips_bad_items():
    items = [ev(title="Good"), ev(title="No date", date="TBD"), {"title": "No url"}, "junk"]
    text = "Here you go:\n```json\n" + json.dumps(items) + "\n```"
    assert [e["title"] for e in bot.parse_events(text)] == ["Good"]


def test_parse_raises_without_json():
    try:
        bot.parse_events("no events found")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_upcoming_filters_past_but_keeps_ongoing():
    events = [ev(title="past", date="2026-10-01"), ev(title="ongoing", date="2026-10-01", end_date="2026-10-06"),
              ev(title="today", date="2026-10-05")]
    assert [e["title"] for e in bot.upcoming(events, TODAY)] == ["ongoing", "today"]


# ---------- Dedupe ----------

def test_event_key_normalizes_url():
    a = ev(url="http://www.Example.com/e/?utm_source=x&b=2&a=1#frag")
    b = ev(url="https://example.com/e?a=1&b=2")
    assert bot.event_key(a) == bot.event_key(b)
    assert bot.event_key(a) != bot.event_key(ev(date="2026-10-21"))


def test_select_new_and_state_roundtrip(tmp_path):
    path = tmp_path / "seen.json"
    state = bot.load_state(path)
    assert state == {}
    first = bot.select_new([ev(), ev(), ev(url="https://other.org")], state, TODAY)
    assert len(first) == 2
    bot.save_state(state, path)
    again = bot.select_new([ev(), ev(title="Brand new", url="https://new.org")], bot.load_state(path), TODAY)
    assert [e["title"] for e in again] == ["Brand new"]


def test_prune_state_drops_old_entries():
    state = {"old": {"date": "2026-01-01"}, "recent": {"date": "2026-09-01"}}
    bot.prune_state(state, TODAY)
    assert list(state) == ["recent"]


# ---------- Digest rendering ----------

EVENTS = [
    ev(title="NYC Forum", date="2026-11-01", location="New York, NY", format="in-person"),
    ev(title="Webinar <Deans>", date="2026-10-15"),
    ev(title="Berkeley Open House", date="2026-10-30", location="Berkeley, CA", format="hybrid"),
    ev(title="SF Fair", date="2026-10-10", location="San Francisco, CA", format="in-person", end_date="2026-10-11"),
]


def test_group_order_and_sorting():
    groups = bot.group_events(EVENTS)
    assert [g for g, _ in groups] == ["In-person: Bay Area (local)", "Virtual", "In-person: elsewhere"]
    assert [e["title"] for e in groups[0][1]] == ["SF Fair", "Berkeley Open House"]


def test_render_text_and_html():
    text = bot.render_text(EVENTS, TODAY)
    assert "4 new event(s)" in text and "2026-10-10 to 2026-10-11" in text
    assert text.index("SF Fair") < text.index("Webinar") < text.index("NYC Forum")
    page = bot.render_html(EVENTS, TODAY)
    assert "Webinar &lt;Deans&gt;" in page and "href='https://example.com/e'" in page


# ---------- End to end with a mocked API ----------

class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


class FakeClient:
    def __init__(self, events):
        text = lambda t: SimpleNamespace(type="text", text=t)  # noqa: E731
        self.stream_replies = [SimpleNamespace(stop_reason="pause_turn", content=[text("...")]),
                               SimpleNamespace(stop_reason="end_turn", content=[text("notes")])]
        self.create_reply = SimpleNamespace(stop_reason="end_turn", content=[text(json.dumps({"events": events}))])
        self.calls = []
        self.messages = self

    def stream(self, **kw):
        self.calls.append(("stream", kw))
        return FakeStream(self.stream_replies.pop(0))

    def create(self, **kw):
        self.calls.append(("create", kw))
        return self.create_reply


def test_run_dry_run_end_to_end(tmp_path, capsys):
    path = tmp_path / "seen.json"
    client = FakeClient(EVENTS + [ev(title="Old", date="2026-09-01")])
    new = bot.run(client, TODAY, dry_run=True, state_path=path)
    assert len(new) == 4 and not path.exists()
    assert "SF Fair" in capsys.readouterr().out
    kinds = [k for k, _ in client.calls]
    assert kinds == ["stream", "stream", "create"]
    tools = client.calls[0][1]["tools"]
    assert {t["type"] for t in tools} == {"web_search_20260209", "web_fetch_20260209"}
    assert client.calls[2][1]["output_config"]["format"]["type"] == "json_schema"


def test_run_sends_only_new_and_skips_when_none(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bot, "send_email", lambda *a: sent.append(a))
    path = tmp_path / "seen.json"
    bot.run(FakeClient(EVENTS), TODAY, state_path=path)
    assert len(sent) == 1 and len(json.loads(path.read_text())) == 4
    bot.run(FakeClient(EVENTS), TODAY, state_path=path)
    assert len(sent) == 1
    bot.run(FakeClient(EVENTS), TODAY, always_send=True, state_path=path)
    assert len(sent) == 2
