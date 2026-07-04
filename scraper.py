"""
vc-startup-tracker — YC Company Scraper
========================================
Pulls all YC companies from the public YC directory
and writes them to Airtable with auto-assigned stage,
AWS stack, and next recommendations.

Run: python scraper.py
"""

import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────
AIRTABLE_TOKEN     = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID   = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE     = os.getenv("AIRTABLE_TABLE_NAME", "startups")
AIRTABLE_URL       = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
HEADERS_AIRTABLE   = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

YC_API_URL         = "https://api.ycombinator.com/v0.1/companies"
BATCH_SIZE         = 10   # Airtable max per request
RATE_LIMIT_SLEEP   = 0.25 # seconds between Airtable writes
YC_PAGE_SIZE       = 100  # companies per YC API page

# ── Stage mapping by batch year ──────────────────────────
def assign_stage(batch: str, status: str) -> str:
    if status and status.lower() in ["acquired", "public"]:
        return "Series C+"
    if not batch:
        return "Seed"
    year_str = batch[-2:]
    try:
        year = int(year_str)
        year = year + 2000 if year < 100 else year
    except:
        return "Seed"
    current_year = datetime.now().year % 100
    age = current_year - year
    if age <= 1:
        return "Pre-Seed"
    elif age <= 2:
        return "Seed"
    elif age <= 4:
        return "Series A"
    elif age <= 6:
        return "Series B"
    else:
        return "Series C+"

# ── AWS stack by stage ───────────────────────────────────
AWS_STACK = {
    "Pre-Seed": {
        "current": [
            "S3 (file storage)",
            "Lambda (serverless functions)",
            "API Gateway",
            "Vercel / Render (hosting)"
        ],
        "next": [
            "EC2 (dedicated compute)",
            "RDS PostgreSQL (real database)",
            "CloudWatch (monitoring)",
            "IAM (access control)"
        ],
        "signals": [
            "First 10 paying customers",
            "MRR crosses $5K",
            "Team grows to 3+",
            "Data storage exceeds SQLite limits"
        ]
    },
    "Seed": {
        "current": [
            "EC2 (compute)",
            "RDS PostgreSQL (database)",
            "S3 (storage)",
            "Lambda (async jobs)",
            "IAM (access control)",
            "CloudWatch (monitoring)"
        ],
        "next": [
            "ECS (container orchestration)",
            "ElastiCache Redis (caching)",
            "ALB (load balancer)",
            "Amazon Bedrock (generative AI)",
            "CloudFormation (infrastructure as code)"
        ],
        "signals": [
            "MRR crosses $50K",
            "Team grows to 10+",
            "Traffic spikes break single EC2",
            "Enterprise customers requesting SLAs",
            "First hired DevOps engineer"
        ]
    },
    "Series A": {
        "current": [
            "ECS / EKS (container orchestration)",
            "RDS with read replicas",
            "ElastiCache Redis (caching)",
            "ALB (load balancer)",
            "Amazon Bedrock (AI layer)",
            "CloudFormation (IaC)",
            "WAF (security)",
            "Cognito (auth)"
        ],
        "next": [
            "EKS (Kubernetes at scale)",
            "Aurora Serverless (auto-scaling DB)",
            "AWS Organizations (multi-account)",
            "SageMaker (custom ML models)",
            "Amazon QuickSight (analytics)",
            "AWS PrivateLink (enterprise isolation)"
        ],
        "signals": [
            "MRR crosses $150K",
            "Team grows to 25+",
            "Enterprise SSO requests incoming",
            "Multi-region requirements",
            "Compliance certifications needed (SOC2)"
        ]
    },
    "Series B": {
        "current": [
            "EKS multi-region",
            "Aurora Serverless",
            "AWS Organizations",
            "SageMaker (custom models)",
            "QuickSight (analytics)",
            "AWS PrivateLink",
            "Macie (data privacy)",
            "AWS Shield (DDoS protection)"
        ],
        "next": [
            "AWS Outposts (on-premise hybrid)",
            "Amazon Trainium (custom AI chips)",
            "AWS Control Tower (governance)",
            "Amazon Connect (enterprise support)",
            "Reserved Instances (cost optimization)",
            "AWS Marketplace listing"
        ],
        "signals": [
            "MRR crosses $1M",
            "Team grows to 100+",
            "International expansion",
            "Cloud spend exceeds $50K/month",
            "Board requires cost optimization"
        ]
    },
    "Series C+": {
        "current": [
            "Full AWS enterprise stack",
            "Multi-region active-active",
            "Custom silicon (Trainium/Inferentia)",
            "AWS Control Tower",
            "Reserved + Savings Plans",
            "AWS Marketplace listed",
            "Dedicated AWS account team"
        ],
        "next": [
            "AWS Partner Network (APN) status",
            "Co-sell agreements with AWS",
            "Custom enterprise support contracts",
            "Graviton processors (ARM cost savings)",
            "AWS for Industries solutions"
        ],
        "signals": [
            "ARR crosses $10M",
            "IPO preparation begins",
            "Cloud spend exceeds $200K/month",
            "AWS strategic partnership discussions"
        ]
    }
}

def get_stack(stage: str) -> dict:
    return AWS_STACK.get(stage, AWS_STACK["Seed"])

# ── Fetch all YC companies ───────────────────────────────
def fetch_yc_companies() -> list:
    companies = []
    page = 1
    print("Fetching YC companies...")

    while True:
        try:
            resp = requests.get(
                YC_API_URL,
                params={"page": page, "count": YC_PAGE_SIZE},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            if resp.status_code != 200:
                print(f"  YC API returned {resp.status_code} on page {page}. Stopping.")
                break

            data = resp.json()
            batch = data.get("companies", [])
            if not batch:
                print(f"  No more companies at page {page}. Done.")
                break

            companies.extend(batch)
            total = data.get("totalCount", "?")
            print(f"  Page {page}: fetched {len(batch)} companies (total so far: {len(companies)} / {total})")
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    print(f"\nTotal YC companies fetched: {len(companies)}")
    return companies

# ── Transform YC record → Airtable fields ───────────────
def transform(company: dict) -> dict:
    batch   = company.get("batch", "") or ""
    status  = company.get("status", "Active") or "Active"
    stage   = assign_stage(batch, status)
    stack   = get_stack(stage)

    return {
        "Name":                  company.get("name", "Unknown"),
        "Batch":                 batch,
        "Sector":                ", ".join(company.get("tags", [])) if company.get("tags") else "Unknown",
        "Description":           company.get("oneLiner", "") or "",
        "Website":               company.get("website", "") or "",
        "Status":                status,
        "Location":              company.get("location", "") or "",
        "Stage":                 stage,
        "Current AWS Stack":     "\n".join(f"• {s}" for s in stack["current"]),
        "Next AWS Recommendations": "\n".join(f"• {s}" for s in stack["next"]),
        "Stage Signals":         "\n".join(f"• {s}" for s in stack["signals"]),
        "Source":                "YC Scrape",
        "Date Added":            datetime.now().strftime("%Y-%m-%d"),
        "Notes":                 ""
    }

# ── Fetch existing company names from Airtable ───────────
def fetch_existing_names() -> set:
    existing = set()
    offset = None
    print("Checking existing Airtable records...")

    while True:
        params = {"fields[]": "Name", "pageSize": 100}
        if offset:
            params["offset"] = offset

        resp = requests.get(AIRTABLE_URL, headers=HEADERS_AIRTABLE, params=params)
        if resp.status_code != 200:
            print(f"  Could not fetch existing records: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        for rec in data.get("records", []):
            name = rec.get("fields", {}).get("Name", "")
            if name:
                existing.add(name.lower().strip())

        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.2)

    print(f"  Found {len(existing)} existing records.")
    return existing

# ── Write batch to Airtable ──────────────────────────────
def write_batch(records: list, batch_num: int) -> int:
    payload = {"records": [{"fields": r} for r in records]}
    resp = requests.post(AIRTABLE_URL, headers=HEADERS_AIRTABLE, json=payload)

    if resp.status_code == 200:
        created = len(resp.json().get("records", []))
        print(f"  Batch {batch_num}: wrote {created} records ✓")
        return created
    else:
        print(f"  Batch {batch_num}: ERROR {resp.status_code} — {resp.text[:200]}")
        return 0

# ── Main ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  vc-startup-tracker — YC Scraper")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env file.")
        print("Add your token to .env and try again.")
        return

    # 1. Fetch YC data
    companies = fetch_yc_companies()
    if not companies:
        print("No companies fetched. Exiting.")
        return

    # 2. Check existing records to avoid duplicates
    existing_names = fetch_existing_names()

    # 3. Transform and filter
    records = []
    skipped = 0
    for c in companies:
        transformed = transform(c)
        if transformed["Name"].lower().strip() in existing_names:
            skipped += 1
            continue
        records.append(transformed)

    print(f"\nNew records to write: {len(records)} (skipped {skipped} duplicates)")

    if not records:
        print("Nothing new to write. Airtable is already up to date.")
        return

    # 4. Write to Airtable in batches of 10
    total_written = 0
    batch_num = 1

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        written = write_batch(batch, batch_num)
        total_written += written
        batch_num += 1
        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n{'=' * 55}")
    print(f"  Done. {total_written} companies written to Airtable.")
    print(f"  Base:  {AIRTABLE_BASE_ID}")
    print(f"  Table: {AIRTABLE_TABLE}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
