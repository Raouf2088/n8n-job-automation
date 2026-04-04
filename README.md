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

## Scoring Model

### Score Factors

| Factor | Score |
|---|---|
| Role base | CV: 8, ML: 6, DS: 4, DA: 3, SWE: 2 |
| Contract | CDI: +2, CDD/Freelance: +0, Stage: -1 |
| Paris / IDF | +3 |
| Other France | +2 |
| Switzerland / UK / Europe | +1 |
| Rest of world | +0 |

Paris / IDF tier includes suburbs such as La Defense, Nanterre, Boulogne, Levallois, Puteaux, and Issy.

### Worked Examples

- Computer Vision + CDI + Paris = 8 + 2 + 3 = 13
- ML Engineer + CDI + Lyon = 6 + 2 + 2 = 10
- ML Engineer + CDI + Zurich = 6 + 2 + 1 = 9
- Data Scientist + CDI + US = 4 + 2 + 0 = 6
- Software Engineer + Stage + Paris = 2 - 1 + 3 = 4

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

## Local Run (Windows + Docker Desktop)

1. Ensure Docker Desktop is installed and running.
2. Configure required environment variables in `.env`.
3. Start services:

```bash
docker compose up -d
```

4. Open n8n at `http://localhost:5678`.

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