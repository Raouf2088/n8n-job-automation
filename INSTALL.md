# Local Installation Guide

End-to-end setup for running this pipeline on your own machine with Docker. Tested on Windows 11 + Docker Desktop, but works on macOS and Linux with the same commands.

> **Time to first run:** ~30 minutes. Most of it is waiting on Google OAuth consent screens and copying API keys.

---

## 1. Prerequisites

- **Docker Desktop** (Windows/macOS) or **Docker Engine + Compose plugin** (Linux). Verify with `docker compose version`.
- **Git** to clone the repo.
- A **Google account** (for Sheets, Drive, Gmail).
- ~5 minutes per third-party API to register and grab a key.

No LaTeX install needed locally — `pdflatex` runs inside the n8n container.

---

## 2. Clone and bootstrap

```bash
git clone <your-fork-url> n8n-job-automation
cd n8n-job-automation
cp .env.example .env
```

Open `.env` in your editor. You'll fill it in over the next steps.

Generate an encryption key and paste it as `N8N_ENCRYPTION_KEY`:

```bash
# any of these works
openssl rand -hex 32
# or in PowerShell:
# [Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Lose this key and you lose every saved credential inside n8n — back it up.

---

## 3. Job-source API keys

You don't need every key. The workflow degrades gracefully — disconnected sources are skipped. Pick the ones you want:

| Source | Cost | Where | Env vars |
|---|---|---|---|
| France Travail | Free, unlimited | https://francetravail.io (FR jobs only) | `FRANCE_TRAVAIL_CLIENT_ID`, `FRANCE_TRAVAIL_CLIENT_SECRET` |
| Remotive | None — public RSS | (no key) | — |
| Arbeitnow | None — public RSS | (no key) | — |
| JSearch | 500/month free | https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch | `RAPIDAPI_KEY` |
| Adzuna | 250/month free | https://developer.adzuna.com | `ADZUNA_APP_ID`, `ADZUNA_KEY` |
| SerpAPI | 100/month free | https://serpapi.com | `SERPAPI_KEY` |

Paste the values into `.env`.

---

## 4. Google setup (Sheets + Drive + Gmail)

### 4a. Create a Google Cloud project + OAuth client

1. Go to https://console.cloud.google.com and create a new project.
2. **APIs & Services → Library** — enable: **Google Sheets API**, **Google Drive API**, **Gmail API**.
3. **APIs & Services → OAuth consent screen** — pick **External**, give the app a name, add your email as a test user. You don't need to publish the app.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**. Application type **Web application**. Add this authorized redirect URI:
   ```
   http://localhost:5678/rest/oauth2-credential/callback
   ```
5. Download the client JSON or copy the **Client ID** and **Client Secret** — you'll paste them into n8n in step 7.

### 4b. Create the tracker spreadsheet

1. New Google Sheet. Rename the first tab to **`Job Tracker`**.
2. Paste this header row in row 1:
   ```
   Date | Company | Role | Location | Source | Date Posted | Apply URL | Role Category | Contract Type | Score | Resume PDF | Status | Notes
   ```
3. Copy the spreadsheet ID from the URL: `docs.google.com/spreadsheets/d/`**`<this part>`**`/edit` → paste into `GOOGLE_SHEET_ID`.

### 4c. Create the Drive folder for tailored PDFs

1. New folder in Drive, e.g. `Job_Application_Resumes`.
2. Copy the folder ID from the URL: `drive.google.com/drive/folders/`**`<this part>`** → paste into `GDRIVE_FOLDER_ID`.

### 4d. Set the notification email

`NOTIFICATION_EMAIL=you@example.com` in `.env`. This is where the daily digest and high-priority alerts go.

---

## 5. (Optional) Pre-made resume Drive links

Each scored job is tagged with a role category (Computer Vision, ML Engineer, Data Scientist, Data Analyst, Software Engineer). The sheet logs a Drive link to a CV tailored for that category.

Either:
- **Skip for now** — leave the `CV_LINK_*` vars empty. The sheet's *Resume PDF* column will be blank, everything else still works.
- Or upload one PDF per category to the Drive folder, copy each share URL, and paste into the matching `CV_LINK_*` var in `.env`.

The on-demand LaTeX tailoring path (`pipeline/generate_tailored_cv.py`) is wired but not currently invoked by the default workflow. See **ADAPT.md** to enable it.

---

## 6. Start the stack

```bash
docker compose up -d
```

First run pulls `n8nio/n8n` and builds a layer with `texlive` + Python — takes a few minutes. After that, opens at:

```
http://localhost:5678
```

Create the n8n owner account (this is local-only, but n8n requires one).

Logs:
```bash
docker compose logs -f n8n
```

> **Caddy**: `docker-compose.yml` also defines a Caddy service for HTTPS. For local-only use, you can ignore it (it'll fail to get a cert without a real domain). To skip it, run `docker compose up -d n8n` instead.

---

## 7. Wire up Google credentials inside n8n

You need three credential entries: **Google Sheets OAuth2**, **Google Drive OAuth2**, **Gmail OAuth2**. They can all reuse the same Client ID/Secret from step 4a.

For each:

1. n8n → **Credentials → New** → pick the type.
2. Paste **Client ID** and **Client Secret** from step 4a.
3. Click **Sign in with Google**, complete consent, return to n8n.
4. **Save**.

---

## 8. Import the workflow

1. n8n → **Workflows → Import from File** → pick `workflow/n8n_job_automation_workflow.json`.
2. Open the imported workflow. Each node referencing Google (Sheets, Drive, Gmail) shows a red badge — click it and select the credential you created in step 7. Do this once per node.
3. **Save**, then toggle **Active** in the top-right.

The workflow exposes its IDs and folder targets via `$env.GOOGLE_SHEET_ID`, `$env.GDRIVE_FOLDER_ID`, etc., so you don't edit any node values — only the credential bindings.

---

## 9. Smoke test

Open the workflow → **Execute Workflow** (top-right). Watch the execution view:

- Sources fetch jobs.
- The **Filter Already Processed** node trims duplicates.
- **Categorize & Score** assigns a role category and 1–15 score.
- **Log to Google Sheet** appends rows.

Open your Google Sheet — new rows should appear. If the **Send Summary Email** node didn't fire, that's expected: it gates on Paris midnight.

If a node errors:
- **403 / scope** → re-run the OAuth consent flow with all three scopes.
- **rate-limit** → check the source's free-tier dashboard.
- **`pdflatex: not found`** → rebuild the image with `docker compose build --no-cache n8n`.

---

## 10. Letting it run

The workflow has its own internal Cron triggers (hourly main loop, plus per-source schedules). Once **Active** in n8n and the container is up, it runs unattended.

To stop:
```bash
docker compose down
```

State (saved credentials, workflow runs) lives in the `n8n_data` Docker volume and survives `down`/`up`.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Empty sheet after a run | All sources rate-limited or returned 0 results — check the source nodes' *output*. |
| Email never arrives | Gmail credential missing or `NOTIFICATION_EMAIL` typo. The digest only fires at Paris midnight; high-priority alerts fire when score > 11. |
| Drive PDF column always empty | `CV_LINK_*` env vars are blank. See step 5. |
| OAuth redirect mismatch | Step 4a redirect URI must be exactly `http://localhost:5678/rest/oauth2-credential/callback`. |
| Can't reach `localhost:5678` | `docker compose ps` — n8n container should be `Up`. Logs: `docker compose logs n8n`. |

For adapting the pipeline to your own profile and target roles, see **[ADAPT.md](ADAPT.md)**.
