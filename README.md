# 🚀 vc-startup-tracker

[![author](https://img.shields.io/badge/author-aitmai-black)](https://github.com/aitmai)
[![python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![flask](https://img.shields.io/badge/backend-Flask-lightgrey)](https://flask.palletsprojects.com)
[![airtable](https://img.shields.io/badge/storage-Airtable-yellow)](https://airtable.com)
[![claude](https://img.shields.io/badge/AI-Claude%20API-blueviolet)](https://anthropic.com)
[![render](https://img.shields.io/badge/deploy-Render-46E3B7)](https://render.com)
[![live](https://img.shields.io/badge/live-vc--startup--tracker.onrender.com-brightgreen)](https://vc-startup-tracker.onrender.com)

AI-powered startup intelligence dashboard for Investor Managers — track assigned portfolio companies across Pre-Seed through Series C+, monitor funding stage progression, and generate Claude-powered investment advisories.

---

## Live Demo

**[vc-startup-tracker.onrender.com](https://vc-startup-tracker.onrender.com)**

---

## Features

- **My Portfolio** — personal startup list with priority, relationship status, next actions, and notes per company
- **Full Database** — 1,900+ real YC companies searchable by name, sector, and stage with one-click portfolio add
- **Pipeline Overview** — Kanban board across all five funding stages, stats row, and tech services heatmap showing what your portfolio needs most right now
- **Tech Stage Map** — reference grid showing typical infrastructure adoption at each funding stage with MRR ranges
- **Claude Advisory** — streaming AI-generated investment advisory per company with concrete next actions, risk flags, and comparable companies
- **Secure token handling** — all API tokens stay server-side via Flask proxy, never exposed in the browser
- **Airtable persistence** — portfolio assignments, notes, and funding rounds persist across sessions

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
├── app.py                      # Flask backend — serves dashboard, proxies all API calls
├── templates/
│   └── dashboard.html          # Full dashboard UI
├── scraper.py                  # YC company scraper → writes to Airtable
├── setup_airtable.py           # Creates all fields in startups table
├── setup_manager_portfolio.py  # Creates all fields in manager_portfolio table
├── requirements.txt
├── render.yaml                 # Render deployment config
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

Open `.env` and fill in all values:
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

**5. Load YC company data**
```bash
python scraper.py
```

**6. Run the dashboard**
```bash
python app.py
# open http://localhost:5000
```

---

## Deploy to Render

1. Push repo to GitHub
2. Go to render.com → New → Web Service
3. Connect `aitmai/vc-startup-tracker` (or paste the public repo URL)
4. Render auto-detects `render.yaml`
5. Add environment variables in the Render dashboard:
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
| Sector | Text | Industry tags |
| Description | Text | One-liner |
| Website | URL | Company website |
| Status | Select | Active / Acquired / Public / Dead |
| Location | Text | HQ location |
| Stage | Select | Pre-Seed / Seed / Series A / B / C+ |
| Current Tech Stack | Long text | Services active at this stage |
| Next Tech Recommendations | Long text | Services to adopt next |
| Stage Signals | Long text | Metrics triggering next stage |
| Source | Select | YC Scrape / Manual Add |
| Date Added | Text | Date written to Airtable |
| Notes | Long text | Manager notes |

### Table 2: `manager_portfolio`

| Field | Type | Description |
|-------|------|-------------|
| Startup Name | Text | Linked to startups table |
| Manager Name | Text | Assigned investor manager |
| Stage | Select | Current funding stage |
| Priority | Select | High / Medium / Low |
| Relationship Status | Select | Active / Monitoring / Dormant |
| Last Contact Date | Text | Date of last contact |
| Next Action | Text | Next action item |
| Next Action Due | Text | Due date |
| Funding Rounds | Long text | JSON array of rounds |
| Current Tech Stack | Long text | Stack at current stage |
| Next Tech Recommendations | Long text | Stack for next stage |
| Claude Advisory | Long text | AI-generated advisory |
| Notes | Long text | Timestamped manager notes |

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

## Security

- All API tokens handled server-side via Flask — never exposed in the browser
- Never commit `.env` to GitHub — `.gitignore` excludes it automatically
- Airtable token scopes required: `data.records:read`, `data.records:write`, `schema.bases:read`, `schema.bases:write`

---

MIT License © 2026 aitmai
