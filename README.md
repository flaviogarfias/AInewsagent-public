# AI Daily Briefing Agent

[Español](README.es.md) · [English setup guide](docs/SETUP.en.md)

An example agent that selects up to **one AI paper and one AI news item** per report, generates HTML and PDF, and sends an email plus a Slack status **only after delivery is explicitly enabled**. A local model evaluates candidates; deduplication, dispatch timing, and delivery controls are deterministic. A red rating does **not** exclude a new eligible item. Source failures block report email delivery; an authorized outbound run may still post a failure status to Slack.

**Repository status:** this standalone example is separate from the live deployment. This repository excludes accounts, credentials, delivery history, generated reports, and operational configuration. The exported code passed 173 tests on Ubuntu 24.04 ARM64 and macOS. An earlier no-send Linux run with all seven public feeds and preloaded local Ollama (`qwen3:4b`) generated HTML/PDF, selected one news item and no eligible paper, recorded zero source errors, and left zero pending/sent deliveries. A fresh isolated run of this revision selected one paper and one news item and generated HTML/PDF, but its audit status was **failed** with one source error and zero pending/sent deliveries; a separate diagnostic found an OpenAI article returning HTTP 403, but the first run's audit did not record the failing URL. A still earlier run recorded 40 arXiv date-lookup errors; later public-source probes and full-feed runs could not reproduce them, so their precise cause is unknown. This small CPU-hosted model also produced a timeout and an overlong summary in separate trials; neither successful artifacts nor passing unit tests establish reliable model performance or validate Composio, Gmail, or Slack from the clean copy. The outbound path was tested in the separate private deployment.

## Safe start

1. Install Python 3.10+, `uv` or `pip`, and [Ollama](https://ollama.com/) with a locally installed model capable of following the JSON schema. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) is needed only for scheduling.
2. Install and test from the repository directory:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -e '.[test]'
   PYTHONPATH=src .venv/bin/python -m pytest -q tests
   ```

3. Copy `config/briefing.example.json` to the Git-ignored `config/briefing.json`. Choose a model tag actually shown by `ollama list`.
4. Validate without delivery: `PYTHONPATH=src .venv/bin/python -m ai_daily_briefing.cli config/briefing.json`.
5. With Ollama running and public feeds reachable, generate a report **without delivery**: `PYTHONPATH=src .venv/bin/python scripts/run_once.py config/briefing.json --workdir var`. Inspect `var/artifacts/<run-id>/` and `var/audit.sqlite3`; `var/` is ignored by Git.

The example configuration deliberately contains invalid outbound destinations and `delivery.send_enabled=false`. None of the commands above send email, post to Slack, or create a scheduled job. Generated reports are in Spanish. Follow the [setup and safety guide](docs/SETUP.en.md) before authorizing any delivery; [Spanish installation and operation guide](docs/INSTALACION.es.md) is also available.

## Limits and release gate

Public-source links are checked for reachability, not for the truth of every claim. For shortlisted arXiv papers, the Atom API's original `published` date—not the RSS entry date—determines the 48-hour eligibility window; the report labels both dates when a paper qualifies. If no paper qualifies, that category is empty even when a feed entry looks recent. Unavailable or invalid arXiv metadata counts as a source failure and blocks report email delivery; an authorized outbound run may still post a failure status to Slack. The model classifies from metadata and summaries and can be wrong; punctuation and length checks do not replace editorial review. Tavily is optional and disabled; Exa and Brave have no active adapters. No paid search is assumed. A sleeping or offline machine can miss the scheduled 15-minute dispatch window. Before enabling a schedule, compare the scheduler's actual next run with the application's IANA-timezone next run; a timezone mismatch can silently prevent a report. Measure real run duration on the destination machine because Hermes may interrupt long jobs.

Local `.env`, `config/briefing.json`, `var/`, generated artifacts, and logs must stay out of Git. **Do not copy private data from the live deployment into this repository.** The release files were reviewed for credential and personal-data patterns; this is not a guarantee against every undiscovered issue. Review generated summaries against primary sources before enabling delivery.

## License

[MIT](LICENSE). The example schedule is illustrative; configure your own time and timezone before creating a job.
