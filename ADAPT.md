# Adapting the Pipeline to Your Profile

This pipeline was originally tuned for an AI/Computer-Vision engineer in Paris. It has been
reconfigured below for **Abderraouf Semid** — Systems & Network Engineer / DevOps, based in
Paris, targeting junior-to-intermediate roles in France.

1. **Search terms and locations** — what jobs come in.
2. **Role categories and scoring weights** — how they're ranked.
3. **The resume itself** — what gets attached to applications.

Every change below is in plain text files you can edit in any editor. None require touching n8n's UI except to re-import.

---

## 1. Search terms and locations

All source queries live in the n8n workflow (`workflow/n8n_job_automation_workflow.json`). Each source is a separate node. The fastest path is to edit through n8n's UI:

| Node name | What to edit |
|---|---|
| `France Travail Search` | Replace keywords with: `administrateur systèmes réseaux`, `ingénieur DevOps`, `ingénieur DevSecOps`, `cloud engineer`, `ingénieur infrastructure`. FR-only. |
| `JSearch (RapidAPI)` | Region rotation table inside the Code node. Use: `Paris`, `Île-de-France`, `Lyon`, `remote France`. Keywords: `DevOps engineer`, `sysadmin Linux`, `cloud infrastructure`, `DevSecOps`. |
| `Adzuna Search` | Country: `fr`. Keywords: `DevOps`, `administrateur Linux`, `Terraform`, `Keycloak`, `infrastructure cloud`. |
| `SerpAPI Search` | 3-day location cycle: `Paris`, `Île-de-France`, `remote`. Keywords: `ingénieur DevOps junior`, `administrateur systèmes junior`, `DevSecOps junior`. |
| `Remotive` / `Arbeitnow` | Filter by title regex — suggested pattern: `/devops|sysadmin|infrastructure|cloud.engineer|devsecops|network.engineer/i` |

To change keywords, open each Code node and edit the array literals. The patterns are commented inline.

**Recommended keyword list (copy-paste ready):**
```js
// French keywords (France Travail, SerpAPI FR)
const keywordsFR = [
  'administrateur systèmes réseaux',
  'ingénieur DevOps junior',
  'ingénieur DevSecOps',
  'administrateur Linux',
  'ingénieur cloud',
  'ingénieur infrastructure',
  'administrateur réseau sécurité',
  'automatisation infrastructure',
];

// English keywords (JSearch, Adzuna, Remotive, Arbeitnow)
const keywordsEN = [
  'DevOps engineer junior',
  'DevSecOps engineer',
  'Linux sysadmin',
  'cloud infrastructure engineer',
  'site reliability engineer junior',
  'infrastructure automation',
  'Terraform Ansible',
  'Keycloak HashiCorp Vault',
];
```

> If you change locations significantly, also update the **scoring** location bonuses in step 2.

---

## 2. Scoring model

The scoring lives entirely in the **`Categorize & Score`** Code node. It's pure regex — no LLM call — so it's cheap and deterministic. Three knobs:

### 2a. Role categories

Replace the original Computer Vision categories with the following, ordered by priority for your profile:

```js
const categories = [
  {
    name: 'DevSecOps Engineer',
    // Highest priority: matches your WiKeys internship exactly
    keywords: ['keycloak', 'vault', 'hashicorp', 'devsecops', 'sso', 'oidc', 'saml', 'ldap', 'pki', 'ssl', 'secret management', 'openldap'],
    titleKeywords: ['devsecops', 'devops security', 'sécurité devops'],
  },
  {
    name: 'DevOps Engineer',
    // Strong match: Terraform, CI/CD, n8n project
    keywords: ['terraform', 'ansible', 'gitlab ci', 'ci/cd', 'pipeline', 'docker', 'kubernetes', 'infrastructure as code', 'iac', 'n8n', 'automation'],
    titleKeywords: ['devops', 'devsecops', 'sre', 'site reliability', 'platform engineer'],
  },
  {
    name: 'Cloud Engineer',
    // Good match: Azure (WiKeys), AWS/GCP knowledge
    keywords: ['azure', 'aws', 'gcp', 'cloud', 'openstack', 'vmware', 'virtualisation', 'kubernetes', 'helm'],
    titleKeywords: ['cloud engineer', 'cloud infrastructure', 'ingénieur cloud'],
  },
  {
    name: 'Sysadmin Linux',
    // Core match: Linux administration across all projects
    keywords: ['linux', 'bash', 'ubuntu', 'debian', 'rhel', 'centos', 'administration système', 'système linux', 'scripting'],
    titleKeywords: ['administrateur système', 'administrateur linux', 'system administrator', 'sysadmin'],
  },
  {
    name: 'Network Engineer',
    // Telecom background from IGEE + university projects
    keywords: ['réseau', 'network', 'cisco', 'ospf', 'tcp/ip', 'dns', 'dhcp', 'vlan', 'firewall', 'routage', '4g', '5g', 'voip', 'téléphonie ip'],
    titleKeywords: ['réseau', 'network engineer', 'administrateur réseau', 'ingénieur réseau'],
  },
  {
    name: 'AI/Automation Engineer',
    // Differentiating niche: n8n + LLM project
    keywords: ['n8n', 'llm', 'openai', 'gemini', 'workflow automation', 'ai devops', 'mlops', 'prompt engineering', 'agentic'],
    titleKeywords: ['automation engineer', 'ai engineer', 'mlops', 'workflow'],
  },
];
// Fallback for unmatched titles
// 'Systems Engineer' (generic)
```

Order matters — first match wins on `titleKeywords`.

### 2b. Base scores per category

```js
const roleScores = {
  'DevSecOps Engineer':    9,  // Best match — WiKeys internship is direct experience
  'DevOps Engineer':       8,  // Strong match — Terraform + CI/CD + n8n project
  'Cloud Engineer':        7,  // Good match — Azure + multi-cloud knowledge
  'Sysadmin Linux':        6,  // Core match — all projects touch this
  'Network Engineer':      5,  // Background match — IGEE telecom + university projects
  'AI/Automation Engineer':7,  // Niche differentiator — rare junior combo
  'Systems Engineer':      3,  // Generic fallback
};
```

Higher = more relevant to *you*. Keep the values in 1–10 — the rest of the formula adds modifiers.

### 2c. Modifiers

| Factor | Adjustment |
|---|---|
| Contract: CDI / permanent | +2 |
| Contract: Stage / internship | -1 |
| Seniority: Junior / débutant signal | +1 |
| Seniority: Senior / Lead / Staff | -2 |
| Location: Paris / IDF | +3 |
| Location: rest of France | +2 |
| Location: Switzerland / UK / EU / remote | +1 |

Final score is clamped 1–15. The high-priority email fires for **score > 11**; the daily digest includes everything. To change those gates:

- High-priority threshold → `Build High Priority Alert` Code node, line `i.json.relevance_score > 11`.
- Digest contents → `Build Summary Email` Code node.

If your target geography isn't Europe, edit the location regex in the same node — the city lists are baked in.

---

## 3. Role-category → resume mapping

You have a single CV but may want to prepare two or three variants emphasizing different angles. Suggested mapping:

```js
const resumeLinks = {
  'DevSecOps Engineer':    $env.CV_LINK_DEVSECOPS,      // Lead with Keycloak/Vault/WiKeys
  'DevOps Engineer':       $env.CV_LINK_DEVOPS,          // Lead with Terraform/CI-CD/n8n
  'Cloud Engineer':        $env.CV_LINK_DEVOPS,          // Same as DevOps variant
  'Sysadmin Linux':        $env.CV_LINK_SYSADMIN,        // Lead with Linux admin projects
  'Network Engineer':      $env.CV_LINK_SYSADMIN,        // Same as sysadmin variant
  'AI/Automation Engineer':$env.CV_LINK_DEVOPS,          // Lead with n8n + LLM project
  'Systems Engineer':      $env.CV_LINK_SYSADMIN,        // Fallback
};
```

Add these to `.env.example` and `docker-compose.yml`:
```
CV_LINK_DEVSECOPS=<your Google Drive share link>
CV_LINK_DEVOPS=<your Google Drive share link>
CV_LINK_SYSADMIN=<your Google Drive share link>
```

Keep the names byte-identical between the three files.

---

## 4. The resume itself

Two files to update:

- **`resume.tex`** — the static base CV. Replace all placeholder content with yours:

```
Name:       Abderraouf Semid
Email:      raoufsemid7@gmail.com
LinkedIn:   https://www.linkedin.com/in/semid-r/
Location:   Paris, France
Phone:      07 51 59 36 35
```

Education section (chronological, newest first):
```
Master in Engineering and Network Innovation — Sorbonne Paris Nord, 2023–2025
Master in Telecommunications — IGEE, Algiers, 2018–2023
Bachelor's in Electrical & Electronic Engineering — IGEE, Algiers, 2018–2021
```

- **`pipeline/cv_template.tex`** — same template with `{{EXPERIENCES}}`, `{{PROJECTS}}`, `{{SKILLS}}` placeholders. Replace the static **header** and **Education** sections with the content above; leave the three `{{...}}` markers alone.

> Both files have a comment block at the top listing what's safe to edit. The repo's `.gitignore` excludes `*.local.tex`, so you can keep an unsanitized personal copy as e.g. `resume.local.tex` without it leaking into commits.

Both compile with plain `pdflatex`. Test locally:

```bash
docker compose exec n8n pdflatex -output-directory /tmp /home/node/pipeline/cv_template.tex
```

### The Python tailor (`pipeline/generate_tailored_cv.py`)

This script takes JSON on stdin → fills the template → compiles a tailored PDF. To enable on-demand tailoring:

1. Add a Code node after `Categorize & Score` that calls an LLM (Groq / Gemini) to produce JSON matching the schema in the docstring of `generate_tailored_cv.py`. Suggested system prompt emphasis: *highlight Keycloak/Vault for security roles, highlight Terraform/n8n for DevOps roles, highlight Linux + DNS/DHCP/LDAP for sysadmin roles.*
2. Add an **Execute Command** node:
   ```bash
   echo '{{ $json.tailored_cv }}' | python3 /home/node/pipeline/generate_tailored_cv.py
   ```
3. Pipe the resulting PDF path to a **Google Drive Upload** node, and write the share URL back to the sheet's *Resume PDF* column.

The hardcoded filename prefix `Riad_Boussoura_CV_` must be replaced in two places:
- `pipeline/generate_tailored_cv.py:326` → change to `Abderraouf_Semid_CV_`
- `pipeline/pdf_service.py:74` → change to `Abderraouf_Semid_CV_`

---

## 5. Email digest content

`Build Summary Email` (daily, Paris midnight) and `Build High Priority Alert` (immediate, score > 11) are HTML strings inside Code nodes. Edit the template literals directly — they're CSS-inlined `<table>` markup. The variable `items` is the row set; columns map 1:1 to the sheet headers.

---

## 6. Schedule

Each source has its own Cron trigger node. Defaults work well — no changes needed:

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
   - Body: OpenAI-compatible chat payload. Suggested system prompt:
     ```
     You are a job relevance scorer for a junior Systems/DevOps engineer in Paris.
     Key skills to reward: Linux, Terraform, Ansible, Keycloak, HashiCorp Vault,
     Docker, Kubernetes, CI/CD (GitLab), Azure/AWS/GCP, n8n, SSO/OIDC/SAML,
     network administration (DNS, DHCP, OSPF), bash scripting.
     Penalize: senior-only roles, non-technical management, roles requiring 5+ years.
     Return JSON: { score: 1-10, verdict: string, rationale: string }
     ```
2. Replace the regex scorer's output mapping with the LLM's JSON.
3. Keep the regex scorer as a fallback for rate-limit cases (n8n's `onError: continueRegularOutput`).

CLAUDE.md in the repo has the original prompt scaffolding under "Scoring Guidelines" and "Resume Tailoring Rules".

---

## Quick checklist before you push your fork

- [ ] `.env` is **not** committed (it's in `.gitignore` — confirm with `git status`).
- [ ] `client_secret*.json` and `*.key` files removed or gitignored.
- [ ] Personal info in `resume.tex` and `pipeline/cv_template.tex` replaced with Abderraouf Semid's details.
- [ ] Hardcoded filename prefix `Riad_Boussoura_CV_` replaced with `Abderraouf_Semid_CV_` in both Python files.
- [ ] Role categories updated to: `DevSecOps Engineer`, `DevOps Engineer`, `Cloud Engineer`, `Sysadmin Linux`, `Network Engineer`, `AI/Automation Engineer`.
- [ ] Keywords updated from AI/CV terms to sysadmin/DevOps terms (see section 1).
- [ ] `CV_LINK_DEVSECOPS`, `CV_LINK_DEVOPS`, `CV_LINK_SYSADMIN` env vars set.
- [ ] `NOTIFICATION_EMAIL` set to `raoufsemid7@gmail.com`.
- [ ] At least one job source has a working API key.
