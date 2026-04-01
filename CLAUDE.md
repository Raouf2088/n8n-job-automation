# Job Search Automation Pipeline — Full Deployment

## What This Project Is

An automated job search pipeline that runs 24/7 on Oracle Cloud Free Tier. Every 6 hours it scrapes job postings, scores them against my profile using a free LLM API, tailors my LaTeX resume for each match, compiles it to PDF, uploads to Google Drive, logs everything to a Google Sheet, and emails me for high-priority matches.

### LLM Choice (use the most generous free tier available)

Pick the best option based on current free tier limits. As of March 2026:

1. **Gemini 2.5 Flash (RECOMMENDED)** — 10 RPM, 250 requests/day, 250K tokens/minute. Best balance of quality and quota. No credit card needed. Get key at https://aistudio.google.com. Use model `gemini-2.5-flash`. n8n has a native Google Gemini node, or use HTTP Request to the REST API.

2. **Groq (strong alternative)** — Runs Llama 4 Scout/Maverick, 30 RPM, ~14,400 requests/day on smaller models. Blazing fast inference. No credit card. Get key at https://console.groq.com. Use model `meta-llama/llama-4-maverick-17b-128e-instruct` or similar.

3. **Mistral AI (fallback)** — Free "Experiment" tier with access to all models including Mistral Small 3.1. Rate limits are more restrictive than Gemini/Groq but still workable for this use case (~1 RPS, 500K TPM). Get key at https://console.mistral.ai.

The workflow needs 2 LLM calls per job (scoring + tailoring). At 4 runs/day with ~20 new jobs per run, that's ~160 calls/day. Gemini's 250 RPD handles this comfortably. Groq's 14,400 RPD is overkill but great insurance. Mistral works but is tighter.

Ideally, implement a fallback chain: try Gemini first, fall back to Groq if rate-limited, then Mistral as last resort. But starting with just Gemini is perfectly fine.

## My Profile

Riad Boussoura — AI & Visual Computing Engineer based in Paris, France.
- Master's in AI & Computer Vision (Sorbonne Paris Nord, Excellence Scholarship)
- Master's in Visual Computing & Bachelor's in Software Engineering (USTHB, Top of Class)
- Most recent role: Computer Vision R&D Engineer at GoPro Paris (Sim-to-Real deep learning pipeline for 360-degree stitching, procedural generation in Blender Python API, custom PyTorch model, >50% processing time reduction)
- Previous: Lead Founding Engineer & CTO at BargMe startup (vision-integrated product recognition, recommendation engine, full product lifecycle)
- Previous: Technical Educator at SkillDino/InspirationTuts (300K+ subscribers, 3D CV tutorials)
- Awards: Google DevFest AI Hackathon 1st Prize, National Innovation Competition 2nd Prize, Samsung "Judges' Favorite"
- Core skills: PyTorch, OpenCV, Blender (Python API), Unity, Unreal Engine, C++, Python, Ray Tracing, Deep Learning, Computer Vision
- Target roles: Computer Vision / AI R&D, Game Rendering / Graphics R&D, 3D / Real-time Engine Dev, General Software Engineering
- Target locations: Europe (especially France, open to remote)
- Seniority: Junior to mid-level (0-3 years)

## What Exists Already

- `resume.tex` — My LaTeX resume using Jake's Resume template. This is the base template for generating tailored PDFs.

## What Needs To Be Built & Deployed

### 1. The Pipeline Files (build these first)

- **n8n workflow JSON** — The complete automation workflow with these stages:
  - Job ingestion from Welcome to the Jungle, Adzuna (free API), and Google Jobs via SerpAPI (free tier)
  - Normalize and deduplicate across sources
  - Check against Google Sheet to skip already-processed jobs
  - Score relevance using Mistral AI (free tier, `mistral-small-latest`, JSON output)
  - Filter: pass ACCEPT and STRETCH, drop REJECT
  - Tailor resume content using Mistral AI (reorder experiences, adjust skills emphasis, add ATS keywords)
  - Generate tailored PDF by populating my LaTeX template and compiling with pdflatex
  - Upload PDF to Google Drive folder `Job_Application_Resumes`
  - Write row to Google Sheet with: date, company, role, location, source, apply URL, relevance score, verdict, rationale, key requirements, gaps, status, Google Drive PDF link, highlighted skills, ATS keywords, salary range, hiring manager, notes
  - Email alert via Gmail for matches scoring 7/10 or above

- **generate_tailored_cv.py** — Python script that:
  - Reads Mistral's tailored JSON from stdin
  - Populates the LaTeX template placeholders (experiences, projects, skills)
  - Escapes LaTeX special characters properly
  - Auto-bolds ATS keywords from the job description in bullet points and skills
  - Compiles to PDF via pdflatex
  - Cleans up auxiliary files (.aux, .log, .out)
  - Prints the PDF path to stdout
  - Paths should be configurable via CV_TEMPLATE_PATH and CV_OUTPUT_DIR env vars

- **cv_template.tex** — A version of my resume.tex with `{{EXPERIENCES}}`, `{{PROJECTS}}`, and `{{SKILLS}}` placeholders that the Python script fills in. Education section stays static.

- **job_tracker_template.xlsx** — Google Sheets template with:
  - Main "Job Tracker" sheet with all columns, conditional formatting (green/yellow/red for verdicts), dropdown validations for Status and Verdict, auto-filter, frozen panes
  - "Dashboard" sheet with summary formulas (total jobs, ACCEPT count, STRETCH count, applied count, avg score)
  - "Setup Guide" sheet

- **Prompt templates** — The system prompts for both Mistral API calls (relevance scoring and resume tailoring), embedded in the workflow JSON

### 2. Infrastructure

**Current strategy (as of 2026-03-30):**
- **Phase A (now):** Run locally on Windows 11 via Docker Desktop to get the pipeline running immediately
- **Phase B (background):** Keep retrying Oracle Cloud Free Tier ARM instance (VM.Standard.A1.Flex, 1 OCPU, 6 GB RAM) — capacity is scarce, account is set up in France Central (Paris) region with VCN `n8n-vcn` and public subnet ready
- **Phase C (fallback):** If Oracle never frees up, consider Hetzner CX22 (~€3.79/month, German DC) for 24/7 uptime

For local deployment:
- Docker Desktop on Windows 11
- No Caddy needed locally (access n8n directly at http://localhost:5678)
- Google OAuth redirect URI already configured: `http://localhost:5678/rest/oauth2-credential/callback`

For cloud deployment (when available):
- Dockerfile extends n8nio/n8n with texlive (pdflatex) and Python
- docker-compose.yml with Caddy as HTTPS reverse proxy
- DuckDNS subdomain for free SSL
- Open firewall ports: 22, 80, 443, 5678
- Google Cloud OAuth2 credentials for Sheets, Drive, and Gmail

### 3. Free API Keys Needed

- Groq (https://console.groq.com) — primary LLM, ~14,400 requests/day free, no credit card, OpenAI-compatible API
- Gemini (https://ai.google.dev) — fallback LLM, 250 requests/day free, no credit card
- Adzuna (https://developer.adzuna.com) — 250 requests/month free
- SerpAPI (https://serpapi.com) — 100 searches/month free

### 4. Scoring Guidelines for the Relevance Prompt

Be TOLERANT — the goal is to widen possibilities, not filter aggressively:
- ACCEPT (score >= 6): Candidate meets most requirements or can grow into them
- STRETCH (score 4-5): Significant gaps but domain is aligned
- REJECT (score < 4): Fundamentally misaligned
- Be generous on seniority — many "3-5 years" roles will consider strong juniors with relevant projects

### 5. Resume Tailoring Rules

- Reorder and reweight bullet points to match job priorities
- Adjust which experiences and projects appear based on relevance
- Promote relevant skills to the top
- NEVER fabricate experience — only reframe existing achievements
- Add ATS keywords from the job description naturally
- For game/rendering roles: emphasize Blender, Unity, Unreal, ray tracing, procedural generation
- For CV/AI roles: emphasize GoPro pipeline, PyTorch, OpenCV, deep learning
- For general SWE roles: emphasize full-stack experience, system design, Python expertise

## Technical Preferences

- All free-tier services
- Docker-based deployment
- Caddy for SSL (not nginx)
- Google Sheets for tracking (not Airtable/Notion)
- **Groq** as primary LLM (free tier: 1,000 RPD, 30 RPM, 100K TPD, model `llama-3.3-70b-versatile`, OpenAI-compatible API, key from https://console.groq.com). Best writing quality among free options (70B params). Gemini 2.5 Flash free tier is too restrictive (5 RPM, 20 RPD). NOT Mistral either.
- LaTeX (pdflatex) for resume PDF generation
- n8n self-hosted (not n8n Cloud)

## Project Structure

```
n8n-job-automation/
├── CLAUDE.md                   (this file)
├── resume.tex                  (my existing LaTeX resume)
├── Dockerfile
├── docker-compose.yml
├── .env
├── pipeline/
│   ├── cv_template.tex         (template with placeholders)
│   └── generate_tailored_cv.py
├── workflow/
│   └── n8n_job_automation_workflow.json
└── sheets/
    └── job_tracker_template.xlsx
```