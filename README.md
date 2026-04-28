# Job Search Automation Pipeline

Automated job discovery and CV tailoring pipeline running on n8n + Python + LaTeX.

The workflow ingests jobs from multiple sources, deduplicates and scores them, generates tailored resume PDFs, logs everything to Google Sheets, and sends a single daily digest email.

## What It Does

- Runs job ingestion every hour (with source-specific schedules where applicable).
- Processes all new jobs found on each run (no per-run cap).
- Scores opportunities using a role/location/contract weighted model.
- Generates tailored CV PDFs from the LaTeX template.
- Uploads generated PDFs to Google Drive.
- Logs all processed jobs to the tracker sheet every hour.
- Sends one digest email per day at 08:00.

## Current Schedule

- Main ingestion loop: every 1 hour.
- JSearch: every 3 hours with rotating regions.
- Adzuna: daily at 08:00 (France + rotating country).
- SerpAPI: daily at 20:00 (rotating location).
- Email notifications: daily digest at 08:00 only.

Notes:
- The old 6-hour cadence has been replaced by an hourly cadence.
- Jobs are still persisted to the sheet every hour; email is consolidated into one daily summary.

## Source Strategy (International Expansion)

| Source | Strategy | Countries |
|---|---|---|
| France Travail | Every hour, 8 queries (was 4). Added: vision par ordinateur, data scientist, IA, python | France |
| Remotive | Every hour | Worldwide remote |
| Arbeitnow | Every hour | EU-wide |
| JSearch | Every 3h, rotating regions | France, Switzerland, UK, Germany, Netherlands |
| Adzuna | Daily at 08:00, FR + rotating country | FR daily + GB/DE/NL/AT/US/CA/AU rotating |
| SerpAPI | Daily at 20:00, rotating location | France, Switzerland, UK, Germany rotating |

## API Calling Strategy

APIs are rate-limited by **number of HTTP calls**, not by volume of results returned. Each country + query combination is one call. The strategy below maximises geographic coverage while staying within each free tier.

### Free Tier Limits

| API | Free Limit | Resets |
|---|---|---|
| France Travail | Effectively unlimited | — |
| Remotive | Unlimited (public RSS) | — |
| Arbeitnow | Unlimited (public RSS) | — |
| JSearch (RapidAPI) | 500 calls/month | Monthly |
| Adzuna | 250 calls/month | Monthly |
| SerpAPI | 100 calls/month | Monthly |

### France Travail

- Runs every hour, 8 keyword queries (all targeting France).
- No call cap concerns — used freely.
- Queries: `computer vision`, `machine learning`, `deep learning`, `NLP`, `vision par ordinateur`, `data scientist`, `intelligence artificielle`, `python`.

### Remotive & Arbeitnow

- Runs every hour, single paginated request each.
- Public RSS/JSON feeds with no authentication or hard cap.

### JSearch (RapidAPI) — every 3 hours, rotating regions

Runs when `hour % 3 === 0` (00:00, 03:00, 06:00, …). Each run picks one region set from an 8-position rotation based on `day % 8`.

| Slot | Regions queried |
|---|---|
| 0 | France, Switzerland |
| 1 | United Kingdom, Germany |
| 2 | Netherlands, France |
| 3 | Switzerland, Belgium |
| 4 | France, United Kingdom |
| 5 | Germany, Netherlands |
| 6 | Switzerland, United Kingdom |
| 7 | France, Germany |

2 queries × 8 runs/day = **16 calls/day → ~480 calls/month** (within 500 limit).

### Adzuna — daily at 08:00, FR daily + rotating international country

Each query (keyword × country) is one API call.

**Daily France queries (every day):** `computer vision`, `machine learning`, `deep learning` → 3 calls/day

**Rotating international country (1 country per day of week):**

| Day | Country |
|---|---|
| Sunday | GB (United Kingdom) |
| Monday | DE (Germany) |
| Tuesday | NL (Netherlands) |
| Wednesday | AT (Austria) |
| Thursday | US (United States) |
| Friday | CA (Canada) |
| Saturday | AU (Australia) |

2 international queries on the rotating country (`computer vision`, `machine learning`) → 2 calls/day

Total: **5 calls/day → ~150 calls/month** (within 250 limit, ~40% buffer).

### SerpAPI — daily at 20:00, 3-day location cycle

Runs a clean 3-day cycle using `day % 3`:

| `day % 3` | Location searched |
|---|---|
| 0 | France |
| 1 | Switzerland |
| 2 | United Kingdom |

3 keyword queries per run → **3 calls/day → ~90 calls/month** (within 100 limit, ~10% buffer).

> **Note:** SerpAPI has the tightest budget. The 10% buffer means roughly 3 spare calls per month. Avoid adding more queries here without reducing elsewhere or upgrading the plan.

### Monthly Budget Summary

| API | Budget | Projected Usage | Headroom |
|---|---|---|---|
| JSearch | 500 | ~480 | ~4% |
| Adzuna | 250 | ~150 | ~40% |
| SerpAPI | 100 | ~90 | ~10% |

---

## Scoring Model

### Score Factors

| Factor | Score |
|---|---|
| Role base | CV: 8, ML: 6, DS: 4, DA: 3, SWE: 2 |
| Contract | CDI: +2, CDD/Freelance: +0, Stage: -1 |
| Seniority | Junior: +1, Unspecified: +0, Senior: -2 |
| Paris / IDF | +3 |
| Other France | +2 |
| Switzerland / UK / Europe | +1 |
| Rest of world | +0 |

Paris / IDF tier includes suburbs such as La Defense, Nanterre, Boulogne, Levallois, Puteaux, and Issy.

**Seniority detection:**
- Junior signals (title + description): `junior`, `jr.`, `débutant`, `entry-level`, `fresh graduate`, `jeune diplômé`, `recent graduate`, `berufseinsteiger`
- Senior signals (title): `senior`, `sr.`, `principal`, `staff`, `lead`, `expert`, `director`, `head of`, `architect`
- Senior signals (description): `profil confirmé`, `confirmé(e) en/dans`, `expérimenté(e)`
- No seniority keyword found → Unspecified (+0)

### Worked Examples

- Computer Vision + CDI + Junior + Paris = 8 + 2 + 1 + 3 = **14**
- Computer Vision + CDI + Unspecified + Paris = 8 + 2 + 0 + 3 = **13**
- Computer Vision + CDI + Senior + Paris = 8 + 2 - 2 + 3 = **11**
- ML Engineer + CDI + Junior + Lyon = 6 + 2 + 1 + 2 = **11**
- ML Engineer + CDI + Unspecified + Zurich = 6 + 2 + 0 + 1 = **9**
- Data Scientist + CDI + Senior + US = 4 + 2 - 2 + 0 = **4**
- Software Engineer + Stage + Paris = 2 - 1 + 0 + 3 = **4**

## Project Structure

```text
n8n-job-automation/
├── CLAUDE.md
├── README.md
├── Dockerfile
├── docker-compose.yml
├── .env
├── resume.tex
├── pipeline/
│   ├── cv_template.tex
│   ├── generate_tailored_cv.py
│   └── pdf_service.py
├── workflow/
│   └── n8n_job_automation_workflow.json
└── sheets/
    └── create_tracker.py
```

## Core Components

- n8n workflow:
  - ingestion, normalization, deduplication, scheduling, integrations
- CV generator script:
  - fills LaTeX placeholders, highlights keywords, compiles PDF
- Tracking sheet:
  - centralized job history and status workflow

## Quickstart

```bash
git clone <your-fork-url> n8n-job-automation
cd n8n-job-automation
cp .env.example .env   # then fill in keys
docker compose up -d
open http://localhost:5678
```

For the full step-by-step walkthrough (Google OAuth, API keys, importing the workflow):
**[INSTALL.md](INSTALL.md)**

To customize search terms, scoring, role categories, and the resume for your own profile:
**[ADAPT.md](ADAPT.md)**

## Data Flow

1. Sources fetch jobs by schedule.
2. Jobs are normalized and deduplicated.
3. Previously processed jobs are filtered out via the tracker.
4. New jobs are scored.
5. Eligible jobs trigger CV tailoring and PDF generation.
6. PDFs are uploaded to Google Drive.
7. Jobs are logged to Google Sheets.
8. Daily digest email is sent at 08:00.

## Deployment Notes

- Current operating mode: local Docker on Windows.
- Cloud target: Oracle Cloud Free Tier ARM instance when capacity is available.
- Reverse proxy/SSL for cloud: Caddy + DuckDNS.

## Important Behavior Changes

- Ingestion frequency changed from 6h to 1h.
- Per-run cap removed: all new jobs are processed.
- Email alerts changed from immediate/high-priority to one daily digest at 08:00.
- Sourcing expanded from France-centric to broader EU/global coverage with rotating-country strategies.