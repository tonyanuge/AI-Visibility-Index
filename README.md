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

## API protection (rate limits + admin export auth)
The public API routes are rate-limited **per client IP**, config-driven via
`config/ratelimit.yaml` (`checker` 30/min, `leads` 10/min, `export` 5/min — tightest, as
it's the brute-force target). Over-limit requests get **429** with a `Retry-After` header.
The limiter is in-process (stdlib only) — **single-instance and resets on restart**; a
shared store for multi-instance is a future gate. `X-Forwarded-For` is **not** trusted by
default (set `trust_forwarded_for: true` only behind a trusted proxy).

`/api/leads/export` auth status codes: **503** when `AVIX_ADMIN_EXPORT_TOKEN` is unset
(fail-closed), **401** + `WWW-Authenticate: Token realm="lead-export"` for missing/blank/
wrong token, **200 + CSV** with the correct token. A successful export records a
content-free `export.accessed` audit event (event + non-PII reference only — never the
token, email, or client IP).

## Branded client report (.docx)
Render a consistent, branded **AI Visibility Check** report from a structured JSON input.
The generator is a *renderer*: the analyst supplies the narrative + evidence; the
generator owns branding, colour, tables, the dated-snapshot disclaimer, and pagination.
```bash
PYTHONPATH=src python scripts/generate_report.py tests/fixtures/sample_report.json
# -> writes data/exports/<client>_AI_Visibility_Check.docx   (data/ is gitignored)
```
Branding lives in `config/report.yaml`; drop an optional `config/assets/logo.png` to brand
the cover (runs fine without it). Rendered `.docx` files go to `data/exports/` and are
**never committed**. The report makes no guaranteed-ranking claim and renders the
dated-snapshot disclaimer verbatim. PDF export, email delivery, and in-app generation are
intentionally out of scope (future work).

## Demo journey (search → on-screen + downloadable report)
Seed a synthetic **Accountants — Dublin** market so a search returns a real verdict:
```bash
PYTHONPATH=src python scripts/seed_accountants.py   # synthetic "(DEMO)" firms only
```
On `/checker`, searching a business now shows an **on-screen report** — verdict, competitors
recommended ahead, a mention-rate stat (share of recommendations / count + % invisible), and
data-derived key findings (read from the scoring output) — plus a **"Download report"** button
that streams the branded `.docx` from `GET /api/report?business=&category=&area=` (generated
in-memory, never written to a repo path; rate-limited per IP). The auto-report states only what
the captured data shows — no tailored advice or predictions — and carries the same dated-snapshot
disclaimer. Demo data is synthetic and **not** a publishable Index.

### Sample-data guardrail (defamation safety)
Because the demo holds synthetic data, the checker must never make a claim about a **real**
business. A cell is treated as **SAMPLE** unless it is provably all-real (every mention has a
known non-demo source; configured in `config/demo.yaml`) — uncertainty **fails toward guarded**.
In a guarded cell, only the seeded **roster** (example `(DEMO)`) names get a verdict; any other
name returns a neutral *"Not in this sample"* note — **never** a fabricated Invisible/Beaten/Strong
verdict, and it names no competitors. This is enforced **server-side** in the checker/report
services (a direct `/api/checker` or `/api/report` call with a real name is refused too — the
report 404s, never a `.docx`). The business field is a **typeahead combobox** — free text is
always allowed, with the sample (DEMO) firms surfaced as live suggestions from
`GET /api/sample/roster` (a retrieval aid, not the gate — the server guard is). A typed
off-roster name returns the neutral note **and** offers a real check (reuses `/api/leads`).
Every seeded result + the downloaded `.docx` carry an unmissable
**"SAMPLE DATA — illustrative only, not a real measurement"** strip.

### Real captured markets (roster-restriction vs sample-banner are separate)
The two guardrail behaviours are split so a **real** captured market works honestly:
- **Roster restriction** applies to **all** mapped markets (real + demo): only firms in the
  cell roster get a verdict; an off-roster name returns an honest *"We haven't captured … in
  this dataset yet"* note (no verdict, no competitors) and the report 404s.
- The **SAMPLE banner** is **demo-only**. A real market (every mention has a non-demo `source`)
  instead shows a **dated-snapshot provenance note** (engines / date / run-count derived from the
  data, via `config/demo.yaml`), keeping the "no ranking is guaranteed" boundary.

Load a real market from gitignored CSVs (never committed):
```bash
# data/imports/{captures.csv, roster.csv, aliases.csv}  — all gitignored
PYTHONPATH=src python scripts/seed_dublin6.py
```
`captures.csv` rows are normalised to canonical roster names via `aliases.csv` (variant →
canonical) **before** scoring — fail-safe: uncertain variants are left separate, never merged on a
guess; an `__EXCLUDE__` canonical drops non-agencies (e.g. directories). The script prints a
verification summary (rows, distinct firms/prompts/engines, top firm, zero-mention roster count) to
eyeball before trusting the market. No real firm names or verdicts are committed to the repo.

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
| 3a | **Set `AVIX_ADMIN_EXPORT_TOKEN`** (a long random secret) to enable lead export. | `/api/leads/export` returns lead emails (PII). It **fails closed** until this env var is set; callers must pass it in the `X-Admin-Export-Token` header. Never put the token in frontend code. Example: `curl -H "X-Admin-Export-Token: $AVIX_ADMIN_EXPORT_TOKEN" localhost:8000/api/leads/export`. |
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
