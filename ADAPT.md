# Adapting the Pipeline to Your Profile

This pipeline was originally tuned for an AI/Computer-Vision engineer in Paris. To make it useful for someone else, you'll mainly change three things:

1. **Search terms and locations** — what jobs come in.
2. **Role categories and scoring weights** — how they're ranked.
3. **The resume itself** — what gets attached to applications.

Every change below is in plain text files you can edit in any editor. None require touching n8n's UI except to re-import.

---

## 1. Search terms and locations

All source queries live in the n8n workflow (`workflow/n8n_job_automation_workflow.json`). Each source is a separate node. The fastest path is to edit through n8n's UI:

| Node name | What to edit |
|---|---|
| `France Travail Search` | Keyword list (currently: `computer vision`, `machine learning`, …). FR-only. |
| `JSearch (RapidAPI)` | Region rotation table inside the Code node. Keywords passed as query string. |
| `Adzuna Search` | Country rotation + keyword list inside the Code node. |
| `SerpAPI Search` | 3-day location cycle + keyword list inside the Code node. |
| `Remotive` / `Arbeitnow` | Filter logic in the *Code* node downstream — they return everything, so you filter by title regex. |

To change keywords, open each Code node and edit the array literals. The patterns are commented inline.

> If you change locations significantly, also update the **scoring** location bonuses in step 2.

---

## 2. Scoring model

The scoring lives entirely in the **`Categorize & Score`** Code node. It's pure regex — no LLM call — so it's cheap and deterministic. Three knobs:

### 2a. Role categories

```js
const categories = [
  { name: 'Computer Vision', keywords: [...], titleKeywords: [...] },
  { name: 'Machine Learning Engineer', keywords: [...], titleKeywords: [...] },
  { name: 'Data Scientist', ... },
  { name: 'Data Analyst', ... },
];
```

Replace these with categories that match your target roles. Categories not matched fall through to `Software Engineer`. Order matters — first match wins on `titleKeywords`.

### 2b. Base scores per category

```js
const roleScores = {
  'Computer Vision': 8,
  'Machine Learning Engineer': 6,
  'Data Scientist': 4,
  'Data Analyst': 3,
  'Software Engineer': 2
};
```

Higher = more relevant to *you*. Keep the values in 1–10 — the rest of the formula adds modifiers.

### 2c. Modifiers

| Factor | Adjustment |
|---|---|
| Contract: CDI / permanent | +2 |
| Contract: Stage / internship | -1 |
| Seniority: Junior signal | +1 |
| Seniority: Senior/Lead/Staff | -2 |
| Location: Paris / IDF | +3 |
| Location: rest of France | +2 |
| Location: Switzerland / UK / EU / remote | +1 |

Final score is clamped 1–15. The high-priority email fires for **score > 11**; the daily digest includes everything. To change those gates:

- High-priority threshold → `Build High Priority Alert` Code node, line `i.json.relevance_score > 11`.
- Digest contents → `Build Summary Email` Code node.

If your target geography isn't Europe, edit the location regex in the same node — the city lists are baked in.

---

## 3. Role-category → resume mapping

```js
const resumeLinks = {
  'Computer Vision': $env.CV_LINK_COMPUTER_VISION,
  'Machine Learning Engineer': $env.CV_LINK_ML_ENGINEER,
  ...
};
```

If you rename or replace categories in step 2a, update this map and the corresponding `CV_LINK_*` env vars in `.env.example` and `docker-compose.yml`. Keep the names byte-identical between the three files.

---

## 4. The resume itself

Two files:

- **`resume.tex`** — the static base CV (Jake's Resume template). Open it and replace name, header (email, LinkedIn, GitHub), Education, Experience, Projects, Skills. Ships with placeholder content (`Your Name`, `Your University`, etc.) — search for `Your ` and `20XX` to find every spot to edit.
- **`pipeline/cv_template.tex`** — same template with `{{EXPERIENCES}}`, `{{PROJECTS}}`, `{{SKILLS}}` placeholders. Replace the static **header** and **Education** sections with yours; leave the three `{{...}}` markers alone.

> Both files have a comment block at the top listing what's safe to edit. The repo's `.gitignore` excludes `*.local.tex`, so you can keep an unsanitized personal copy as e.g. `resume.local.tex` without it leaking into commits.

Both compile with plain `pdflatex`. Test locally:

```bash
docker compose exec n8n pdflatex -output-directory /tmp /home/node/pipeline/cv_template.tex
```

### The Python tailor (`pipeline/generate_tailored_cv.py`)

This script takes JSON on stdin → fills the template → compiles a tailored PDF. It's wired but not invoked by the default workflow (which logs Drive links to pre-made PDFs instead). To enable on-demand tailoring:

1. Add a Code node after `Categorize & Score` that calls an LLM (Groq / Gemini) to produce JSON matching the schema in the docstring of `generate_tailored_cv.py`.
2. Add an **Execute Command** node:
   ```bash
   echo '{{ $json.tailored_cv }}' | python3 /home/node/pipeline/generate_tailored_cv.py
   ```
3. Pipe the resulting PDF path to a **Google Drive Upload** node, and write the share URL back to the sheet's *Resume PDF* column.

The hardcoded filename prefix `Riad_Boussoura_CV_` lives in two places — search and replace:
- `pipeline/generate_tailored_cv.py:326`
- `pipeline/pdf_service.py:74`

---

## 5. Email digest content

`Build Summary Email` (daily, Paris midnight) and `Build High Priority Alert` (immediate, score > 11) are HTML strings inside Code nodes. Edit the template literals directly — they're CSS-inlined `<table>` markup. The variable `items` is the row set; columns map 1:1 to the sheet headers.

---

## 6. Schedule

Each source has its own Cron trigger node. Defaults:

- Main hourly loop: `Schedule Trigger`
- JSearch: every 3 hours, region-rotated
- Adzuna: daily 08:00 (FR daily + rotating country)
- SerpAPI: daily 20:00 (3-day location cycle)
- Daily digest: hourly check, fires only at Paris 00:00

Change the cron expressions in the trigger nodes if you want different cadence. The free-tier budget tables in `README.md` assume the defaults — if you make sources fire more often, recheck monthly call counts.

---

## 7. Optional: bring back LLM scoring/tailoring

The original design used Groq/Gemini for both relevance scoring and resume tailoring. The current workflow ships with regex-only scoring (faster, free, deterministic) but the env vars `GROQ_API_KEY` and `GEMINI_API_KEY` are still wired. If you want LLM scoring back:

1. Add an **HTTP Request** node after `Filter Already Processed`:
   - URL: `https://api.groq.com/openai/v1/chat/completions`
   - Auth: Bearer `={{ $env.GROQ_API_KEY }}`
   - Body: OpenAI-compatible chat payload with a system prompt asking for `{score, verdict, rationale}` JSON.
2. Replace the regex scorer's output mapping with the LLM's JSON.
3. Keep the regex scorer as a fallback for rate-limit cases (n8n's `onError: continueRegularOutput`).

CLAUDE.md in the repo has the original prompt scaffolding under "Scoring Guidelines" and "Resume Tailoring Rules".

---

## Quick checklist before you push your fork

- [ ] `.env` is **not** committed (it's in `.gitignore` — confirm with `git status`).
- [ ] `client_secret*.json` and `*.key` files removed or gitignored.
- [ ] Personal info in `resume.tex` and `pipeline/cv_template.tex` replaced.
- [ ] Hardcoded filename prefix `Riad_Boussoura_CV_` replaced in both Python files.
- [ ] Role categories, scoring weights, and locations updated to match your target.
- [ ] `NOTIFICATION_EMAIL` set to your address.
- [ ] At least one job source has a working API key.
