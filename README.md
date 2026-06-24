# AI Visibility Index ("AI Mystery Shopping")

> **AI Visibility Index is a product of TraceLogic Limited.** It is a distinct
> application operated by TraceLogic Limited — not merged into any other TraceLogic
> system. © 2026 TraceLogic Limited. All rights reserved. See [LICENSE](LICENSE).

A working productised-service backend + public **checker** for measuring what AI
assistants (ChatGPT, Gemini, Perplexity) recommend for local buying-intent queries,
scoring every business on visibility / rank / accuracy / share-of-voice, and turning
**invisible** businesses into captured leads.

Two surfaces on one shared engine:
- **The Index** — scored per-category league tables (`/api/index/{category}/{area}`).
- **The Checker** — public page returning an instant verdict (Invisible / Beaten /
  Strong / Not-covered) and capturing the lead (`/checker` + `/api/checker` + `/api/leads`).

Page routes: `/` serves the marketing **landing page**; `/checker` serves the
functional **checker page** (backed by the live API). The API endpoints are unchanged.

## Run it locally (≈2 minutes)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/seed.py                                # loads synthetic demo data (2 verticals)
PYTHONPATH=src python -m uvicorn avix.api.main:app --reload --port 8000
# open http://localhost:8000          -> the landing page
# open http://localhost:8000/checker  -> the functional checker
```

> ⚠️ **Data status — SYNTHETIC DEMO ONLY.** Everything shipped in this repo is
> seeded synthetic data (every business is suffixed `(DEMO)`). It exists only so the
> app runs and the tests go green. **It is not evidence and must not be treated as a
> publishable Index.** Real market publication requires live captures / imported
> tracker data first (see *Load your real data* below). Until you import real
> captures, no league table here reflects what any AI assistant actually returned.

## Verify it works
```bash
PYTHONPATH=src python -m pytest tests/ -q        # unit tests (scoring engine)
PYTHONPATH=.   python scripts/smoke_test.py      # end-to-end smoke (all layers + API)
```

## Deployment status
**Not configured yet.** The app runs locally as shipped (`uvicorn`/`gunicorn`); no
hosting, domain, CI, or runtime environment is provisioned in this repo. The
**intended deployment target is [Lovable](https://lovable.dev)** — not yet set up.
Do not treat anything here as deployed or production-ready.

## Load your real data (replaces the demo)
The capture grain matches the tracker spreadsheet's **Run Log** exactly.
```bash
python scripts/import_tracker.py /path/to/ai_mystery_shopping_tracker.xlsx
# or a CSV with the Run Log columns
```

## Architecture (UI never bypasses the backend)
```
web/ (checker page)  ->  api/ (FastAPI)  ->  service/  ->  core/ (scoring) + store/ (sqlite)
config/  = taxonomy, archetypes, scoring thresholds, prompt packs  (data, not code)
audit/   = content-free event log (never stores emails / raw LLM text / secrets)
ingest/  = manual CSV/xlsx import (works now) + env-gated live LLM runners (optional)
```

## >>> THINGS THAT NEED YOUR ACTION <<<
| # | Action | Why / where |
|---|--------|-------------|
| 1 | **Create Stripe Payment Links** (audit + monthly monitoring) and paste the URLs into `config/settings.yaml` (copy from `settings.example.yaml`). | Surfaced on the checker CTA. Until set, buttons point at placeholders. |
| 2 | **(Optional) Add LLM API keys** to `.env` (`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`) to enable automated answer-fetching. | Without keys the app runs **manual-only** (you capture via the tracker and import). Live keys + outbound network are required to fetch answers; **mention extraction from raw answers is still a human/assisted review step.** |
| 3 | **(Optional) Email connector** — add `SENDGRID_API_KEY` to send report emails. | Not wired to a provider yet; leads are captured and exportable via `/api/leads/export` so you can send manually on day one. |
| 4 | **Run the live invisibility probe** and import real captures before publishing any Index. | The scores are only as good as your data; demo rows are synthetic. |
| 5 | **Legal:** do **not** publish aesthetics or solicitor rankings (POM advertising / LSRA rules, live 2026 enforcement). Estate agents, physio, dentists, opticians, vets, driving instructors are clean to publish. | Product/legal boundary. |
| 6 | **Deploy** when ready (any container/VM host: `uvicorn`/`gunicorn`). | Not deployed; runs locally as shipped. |

## Honest capability boundaries (claims match build)
- The scoring engine, persistence, import, Index, checker, lead capture, content-free
  audit, API and web page **work now**.
- Live LLM runners are **real code but inert without keys + network**; automated
  *extraction* of business names/ranks/accuracy from raw answers is **not** automated —
  it's an assisted/manual step by design.
- No "guaranteed ranking" or "AI-powered" claims are made anywhere. All Index output is
  a dated snapshot of what the AIs returned under stated conditions.
