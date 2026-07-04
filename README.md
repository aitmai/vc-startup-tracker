# 🚀 vc-startup-tracker

[![author](https://img.shields.io/badge/author-aitmai-black)](https://github.com/aitmai)
[![python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![airtable](https://img.shields.io/badge/storage-Airtable-yellow)](https://airtable.com)

AI-powered startup tracker for Investor Managers — monitor portfolio companies across funding stages with automated tech stack recommendations and Claude-generated investment advisories.

---

## Features

- Pulls 4,000+ real YC companies from the public YC directory
- Auto-assigns funding stage based on batch year
- Auto-maps current tech stack and next recommendations per stage
- Writes all records to Airtable with duplicate detection
- Skips existing records on re-run — safe to run multiple times

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Data source | YC Public Company Directory |
| Storage | Airtable |
| Language | Python 3.9+ |
| AI layer | Claude API (Sonnet) |
| Frontend | React (coming in Phase 2) |

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
AIRTABLE_BASE_ID=appWQNv1G6y9m8CM6
AIRTABLE_TABLE_NAME=startups
```

**4. Run the scraper**
```bash
python scraper.py
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AIRTABLE_TOKEN` | Airtable Personal Access Token | `patXXXXX...` |
| `AIRTABLE_BASE_ID` | Airtable Base ID | `appWQNv1G6y9m8CM6` |
| `AIRTABLE_TABLE_NAME` | Table name in Airtable | `startups` |

---

## Airtable Table Structure

| Field | Type | Description |
|-------|------|-------------|
| Name | Text | Company name |
| Batch | Text | YC batch (e.g. W21, S22) |
| Sector | Text | Industry tags |
| Description | Text | One-liner |
| Website | URL | Company website |
| Status | Text | Active / Acquired / Public |
| Location | Text | HQ location |
| Stage | Text | Pre-Seed / Seed / Series A / B / C+ |
| Current AWS Stack | Long text | Services active at this stage |
| Next AWS Recommendations | Long text | Services to adopt next |
| Stage Signals | Long text | Metrics triggering next stage |
| Source | Text | YC Scrape / Manual Add |
| Date Added | Text | Date written to Airtable |
| Notes | Long text | Manager notes |

---

## Stage Logic

| Stage | Batch Age | MRR Range |
|-------|-----------|-----------|
| Pre-Seed | 0–1 years | <$5K |
| Seed | 1–2 years | $5K–$50K |
| Series A | 2–4 years | $50K–$150K |
| Series B | 4–6 years | $150K–$1M |
| Series C+ | 6+ years | $1M+ |

---

## Security

- Never commit `.env` to GitHub
- Token scopes required: `data.records:read`, `data.records:write`, `schema.bases:read`
- `.gitignore` excludes `.env` automatically

---

MIT License © 2026 aitmai
