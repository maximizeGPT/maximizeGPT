# Law School Events Bot

Every Monday this bot asks Claude to search the web for upcoming events for prospective law school applicants (LSAC forums, law school fairs, admissions info sessions and webinars, pipeline programs, networking events). It then emails a digest that lists only events it has not sent before.

The digest has three sections, each sorted by date:

1. In-person: Bay Area (local). Hayward base; SF, Oakland, Berkeley, the Peninsula, San Jose and Davis all count.
2. Virtual (includes hybrid events outside the Bay Area)
3. In-person: elsewhere

## Files

- `bot.py`: research, dedupe, digest, and email
- `config.py`: edit your location, cycle year, target schools, local city list, and search limits here
- `seen_events.json`: events already emailed (the workflow commits this file after each run)
- `tests/`: pytest unit tests (no API calls)
- `../.github/workflows/law-events-bot.yml`: weekly schedule (Mondays 15:00 UTC) plus manual runs

## Setup

1. Get an Anthropic API key at https://console.anthropic.com.
2. Create a Gmail app password for the account that will send the email:
   1. Turn on 2-Step Verification at https://myaccount.google.com/security.
   2. Go to https://myaccount.google.com/apppasswords, create an app named "law-events-bot", and copy the 16-character password.
3. In the GitHub repo, open Settings > Secrets and variables > Actions and add these repository secrets:

   | Secret | Value |
   | --- | --- |
   | `ANTHROPIC_API_KEY` | your Anthropic API key |
   | `SMTP_USER` | the sending Gmail address, e.g. `you@gmail.com` |
   | `SMTP_PASSWORD` | the Gmail app password from step 2 |
   | `EMAIL_TO` | where the digest goes, e.g. `rameenjafri@hotmail.com` |

4. Open the Actions tab, pick "Law school events bot", and click "Run workflow" to test it. Tick "always_send" to get an email even when nothing is new.

`SMTP_HOST` (default `smtp.gmail.com`) and `SMTP_PORT` (default `587`) are optional overrides.

## Run locally

```bash
cd law-events-bot
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python bot.py --dry-run          # print the digest; no email, state not saved
export SMTP_USER=you@gmail.com SMTP_PASSWORD=app-password EMAIL_TO=rameenjafri@hotmail.com
python bot.py                    # email new events and update seen_events.json
python bot.py --always-send      # email even if there are no new events
```

Run tests with `pip install pytest && python -m pytest tests`.

## Notes

- Each run makes one long web research call to `claude-opus-5-5` (up to 25 searches and 15 page fetches, set in `config.py`) plus one short call that converts the findings to JSON. A run takes a few minutes; cost scales with the number of searches and fetches.
- Requests use the API's server-side refusal fallback, so a declined request is retried on another Claude model automatically.
- Events are deduped by normalized URL plus start date. Delete an entry from `seen_events.json` to get it emailed again.
- Always confirm details on the event page before registering; search results can be stale.
