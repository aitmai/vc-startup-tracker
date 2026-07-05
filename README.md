# 🚀 vc-startup-tracker

[![author](https://img.shields.io/badge/author-aitmai-black)](https://github.com/aitmai)
[![python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![flask](https://img.shields.io/badge/backend-Flask-lightgrey)](https://flask.palletsprojects.com)
[![airtable](https://img.shields.io/badge/storage-Airtable-yellow)](https://airtable.com)
[![claude](https://img.shields.io/badge/AI-Claude%20API-blueviolet)](https://anthropic.com)
[![render](https://img.shields.io/badge/deploy-Render-46E3B7)](https://render.com)
[![live](https://img.shields.io/badge/live-vc--startup--tracker.onrender.com-brightgreen)](https://vc-startup-tracker.onrender.com)

AI-powered startup intelligence dashboard for Investor Managers — track assigned portfolio companies across Seed through Series C+, monitor funding stage progression, and generate Claude-powered investment advisories.

---

## Live Demo

**[vc-startup-tracker.onrender.com](https://vc-startup-tracker.onrender.com)**

---

## Features

- **Login persistence** — name saved to localStorage, auto-login on return visits with logout button
- **My Portfolio** — personal startup list per manager with priority, relationship status, next actions, notes, stage stepper, and Claude advisory per company
- **Full Database** — ~900 real YC companies (Seed+, active only, W20–present) searchable by name, sector, and stage with one-click portfolio add
- **Pipeline Overview** — Kanban board across all five funding stages, stats row (total, high priority, active, overdue), and tech services heatmap
- **Tech Stage Map** — reference grid showing typical infrastructure adoption at each funding stage with MRR ranges
- **Claude Advisory** — streaming AI-generated investment advisory per company with concrete next actions, risk flags, and comparable companies
- **Secure token handling** — all API tokens stay server-side via Flask proxy, never exposed in the browser
- **Airtable persistence** — portfolio assignments, notes, and funding rounds persist across sessions per manager
- **Save error handling** — explicit error alerts if Airtable write fails, no silent local-only adds

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Backend | Flask (Python) |
| Frontend | Vanilla JS + HTML |
| Data source | YC Public Company Directory |
| Storage | Airtable (two tables: startups, manager_portfolio) |
| AI layer | Claude Sonnet via Anthropic API |
| Deployment | Render |

---

## Project Structure

```
vc-startup-tracker/
├── app.py                          # Flask backend — serves dashboard, proxies all API calls
├── templates/
│   └── dashboard.html              # Full dashboard UI — all four tabs
├── scraper.py                      # Original YC scraper (all companies)
├── load_fresh.py                   # Fresh load — Seed+ only, real sectors only
├── load_fresh2.py                  # Fresh load v2 — two-pass, fills to 900
├── load_balanced.py                # Balanced load — quota per stage, no public
├── topup_startups.py               # Top-up — adds N new companies without duplicates
├── trim_startups.py                # Trim — removes dead/inactive and old batches
├── trim_startups2.py               # Trim pass 2 — aggressive cut to target count
├── reload_startups.py              # Reload — deletes Pre-Seed/Unknown, refetches
├── setup_airtable.py               # Creates all fields in startups table
├── setup_manager_portfolio.py      # Creates all fields in manager_portfolio table
├── requirements.txt
├── render.yaml                     # Render deployment config
├── .env.example
└── .gitignore
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/aitmai/vc-startup-tracker
cd vc-startup-tracker
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure environment**
```bash
cp .env.example .env
```

Open `.env` and fill in:
```
AIRTABLE_TOKEN=your_personal_access_token
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_NAME=startups
ANTHROPIC_API_KEY=your_anthropic_key
FLASK_ENV=development
PORT=5000
```

**4. Set up Airtable tables**
```bash
python setup_airtable.py
python setup_manager_portfolio.py
```

**5. Load startup data**
```bash
python load_balanced.py
```

**6. Run the dashboard**
```bash
python app.py
# open http://localhost:5000
```

---

## Data Scripts

All scripts accept `y` or `yes` / `n` or `no` at confirmation prompts.

| Script | Purpose |
|--------|---------|
| `load_balanced.py` | **Recommended first load** — 900 companies, balanced by stage (Seed=350, A=300, B=150, C+=100), no Pre-Seed, no public, no inactive |
| `topup_startups.py` | Add more companies without duplicates — checks existing names before writing |
| `trim_startups.py` | Remove dead/inactive companies and old batches |
| `trim_startups2.py` | Aggressive trim — delete oldest records until under target count |
| `load_fresh.py` | Fresh load — Seed+ only, skips companies with no sector tags |
| `load_fresh2.py` | Fresh load v2 — fills remaining slots with "Technology" label for untagged |
| `scraper.py` | Original scraper — all companies, all stages |

**Recommended data workflow:**
```bash
# Initial setup (empty table)
python load_balanced.py

# Add more companies later without duplicates
python topup_startups.py

# Clean up bad data
python trim_startups.py
```

---

## Deploy to Render

1. Push repo to GitHub
2. Go to render.com → New → Web Service
3. Connect `aitmai/vc-startup-tracker` or paste the public repo URL under Public Git Repository tab
4. Render auto-detects `render.yaml`
5. Add environment variables:
   - `AIRTABLE_TOKEN`
   - `ANTHROPIC_API_KEY`
6. Click Deploy — live in ~2 minutes

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AIRTABLE_TOKEN` | Airtable Personal Access Token | `patXXXXX...` |
| `AIRTABLE_BASE_ID` | Airtable Base ID | `appXXXXXXXXXXXXXX` |
| `AIRTABLE_TABLE_NAME` | Startups table name | `startups` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | `sk-ant-XXXX...` |
| `FLASK_ENV` | Flask environment | `development` or `production` |
| `PORT` | Port for local dev | `5000` |

---

## Airtable Schema

### Table 1: `startups`

| Field | Type | Description |
|-------|------|-------------|
| Name | Text | Company name |
| Batch | Text | YC batch (e.g. W21, S22) |
| Sector | Text | Industry tags — "Technology" if untagged |
| Description | Text | One-liner |
| Website | URL | Company website |
| Status | Select | Active / Acquired |
| Location | Text | HQ location |
| Stage | Select | Seed / Series A / Series B / Series C+ |
| Current AWS Stack | Long text | Infrastructure active at this stage |
| Next AWS Recommendations | Long text | Infrastructure to adopt next |
| Stage Signals | Long text | Metrics triggering next stage |
| Source | Select | YC Scrape / Manual Add |
| Date Added | Text | Date written to Airtable |
| Notes | Long text | Manager notes |

### Table 2: `manager_portfolio`

| Field | Type | Description |
|-------|------|-------------|
| Manager Name | Text | Login name — used to filter portfolio per manager |
| Manager Email | Text | Manager email |
| Startup Name | Text | Company name |
| Startup Website | URL | Company website |
| Sector | Text | Industry sector |
| Stage | Select | Current funding stage |
| Priority | Select | High / Medium / Low |
| Relationship Status | Select | Active / Monitoring / Dormant |
| Last Contact Date | Text | Date of last contact |
| Next Action | Text | Next action item |
| Next Action Due | Text | Due date |
| Funding Rounds | Long text | JSON array of rounds |
| Current Tech Stack | Long text | Stack at current stage |
| Next Tech Recommendations | Long text | Stack for next stage |
| Stage Signals | Long text | Metrics triggering next stage |
| Claude Advisory | Long text | AI-generated advisory |
| Notes | Long text | Timestamped manager notes |
| Date Added | Text | Date record was created |
| Added By | Text | Manager who created this record |
| Source | Select | YC Database / Manual Add / Referral / Event / Inbound |

---

## Stage Logic

| Stage | Batch Age | MRR Range |
|-------|-----------|-----------|
| Pre-Seed | 0–1 years | < $5K |
| Seed | 1–2 years | $5K – $50K |
| Series A | 2–4 years | $50K – $150K |
| Series B | 4–6 years | $150K – $1M |
| Series C+ | 6+ years | $1M+ |

---

## Data Rules

- No Pre-Seed companies in the database
- No public companies (IPO'd)
- No inactive / dead / closed companies
- Companies without YC sector tags are labeled "Technology"
- All scripts check for duplicates before writing
- All confirmation prompts accept `y`, `yes`, `n`, or `no`

---

## Security

- All API tokens handled server-side via Flask — never exposed in the browser
- Never commit `.env` to GitHub — `.gitignore` excludes it automatically
- Airtable token scopes required: `data.records:read`, `data.records:write`, `schema.bases:read`, `schema.bases:write`
- Save operations show explicit error messages if Airtable write fails — no silent failures

---

MIT License © 2026 aitmai
