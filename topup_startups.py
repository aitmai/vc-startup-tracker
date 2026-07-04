"""
vc-startup-tracker — Top-Up Load
==================================
Adds up to 400 more companies that are NOT
already in the Airtable startups table.

- Fetches existing company names from Airtable
- Pages through YC API skipping duplicates
- No Pre-Seed, no public companies
- Stops at 400 new records written

Run: python topup_startups.py
"""

import os
import time
import re
from datetime import datetime
from collections import Counter
import requests
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE   = os.getenv("AIRTABLE_TABLE_NAME", "startups")
AIRTABLE_URL     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
YC_API_URL       = "https://api.ycombinator.com/v0.1/companies"
TOPUP_TARGET     = 400

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

TECH_STACK = {
    "Seed": {
        "current": "• EC2 (compute)\n• RDS PostgreSQL\n• S3 (storage)\n• Lambda (async jobs)\n• CloudWatch\n• IAM",
        "next":    "• ECS (containers)\n• ElastiCache Redis\n• ALB (load balancer)\n• Bedrock AI layer\n• CloudFormation",
        "signals": "• MRR crosses $50K\n• Team grows to 10+\n• Traffic spikes break single server\n• Enterprise SLA requests"
    },
    "Series A": {
        "current": "• ECS (containers)\n• RDS read replicas\n• ElastiCache Redis\n• ALB\n• CloudFormation\n• WAF + Auth",
        "next":    "• Kubernetes (EKS)\n• Aurora Serverless\n• Multi-account governance\n• Custom ML models\n• Analytics dashboard\n• Enterprise isolation",
        "signals": "• MRR crosses $150K\n• Team grows to 25+\n• Enterprise SSO requests\n• Multi-region requirements"
    },
    "Series B": {
        "current": "• Kubernetes multi-region\n• Aurora Serverless\n• Multi-account governance\n• Custom ML (SageMaker)\n• Data privacy layer\n• DDoS protection",
        "next":    "• On-premise hybrid\n• Custom AI chips\n• Cloud governance layer\n• Reserved capacity (cost cut)\n• Cloud Marketplace listing",
        "signals": "• MRR crosses $1M\n• International expansion\n• Cloud spend $50K+/mo\n• Board-level cost optimization"
    },
    "Series C+": {
        "current": "• Full enterprise stack\n• Multi-region active-active\n• Custom AI chips\n• Cloud governance\n• Reserved capacity\n• Cloud Marketplace listed",
        "next":    "• Cloud partner co-sell\n• Enterprise support contracts\n• ARM processors (cost savings)\n• Industry-specific cloud solutions",
        "signals": "• ARR crosses $10M\n• IPO preparation begins\n• Cloud spend $200K+/mo\n• Strategic partnership discussions"
    }
}

def batch_year(batch_str):
    if not batch_str:
        return 99
    match = re.search(r'(\d{2,4})', str(batch_str))
    if not match:
        return 99
    year = int(match.group(1))
    return year - 2000 if year > 2000 else year

def assign_stage(batch, status):
    status_lower = (status or "").lower()
    if status_lower in ("public", "inactive", "dead", "closed", "shutdown"):
        return "skip"
    if status_lower == "acquired":
        return "Series C+"
    year = batch_year(batch)
    current = datetime.now().year % 100
    age = current - year
    if age <= 1:   return "Pre-Seed"
    elif age <= 2: return "Seed"
    elif age <= 4: return "Series A"
    elif age <= 6: return "Series B"
    else:          return "Series C+"

def transform(c, stage):
    batch  = c.get("batch", "") or ""
    status = c.get("status", "Active") or "Active"
    tags   = c.get("tags") or []
    sector = ", ".join(tags) if tags else "Technology"
    stack  = TECH_STACK.get(stage, TECH_STACK["Seed"])
    return {
        "Name":                     c.get("name", ""),
        "Batch":                    batch,
        "Sector":                   sector,
        "Description":              c.get("oneLiner", "") or "",
        "Website":                  c.get("website", "") or "",
        "Status":                   status,
        "Location":                 c.get("location", "") or "",
        "Stage":                    stage,
        "Current AWS Stack":        stack["current"],
        "Next AWS Recommendations": stack["next"],
        "Stage Signals":            stack["signals"],
        "Source":                   "YC Scrape",
        "Date Added":               datetime.now().strftime("%Y-%m-%d"),
        "Notes":                    ""
    }

def fetch_existing_names():
    names = set()
    offset = None
    print("Fetching existing Airtable company names...")
    while True:
        params = {"pageSize": 100, "fields[]": "Name"}
        if offset:
            params["offset"] = offset
        resp = requests.get(AIRTABLE_URL, headers=HEADERS, params=params)
        data = resp.json()
        for r in data.get("records", []):
            name = r.get("fields", {}).get("Name", "").strip().lower()
            if name:
                names.add(name)
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.2)
    print(f"  Found {len(names)} existing companies")
    return names

def write_batch(records, written_so_far):
    payload = {"records": [{"fields": r} for r in records]}
    resp = requests.post(AIRTABLE_URL, headers=HEADERS, json=payload)
    if resp.status_code == 200:
        total = written_so_far + len(records)
        print(f"  {total}/{TOPUP_TARGET} written ✓", end='\r')
        return len(records)
    else:
        print(f"\n  ERROR: {resp.status_code} — {resp.text[:150]}")
        return 0

def main():
    print("=" * 55)
    print("  vc-startup-tracker — Top-Up Load")
    print(f"  Adding {TOPUP_TARGET} new companies (no duplicates)")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env")
        return

    # 1. Get existing names to avoid duplicates
    existing_names = fetch_existing_names()

    # 2. Page through YC and collect new companies
    new_companies = []
    page          = 1
    skipped_dupe  = 0
    skipped_preseed = 0
    skipped_public  = 0

    print(f"\nFetching new YC companies (skipping {len(existing_names)} already loaded)...")
    print("-" * 55)

    while len(new_companies) < TOPUP_TARGET:
        try:
            resp = requests.get(
                YC_API_URL,
                params={"page": page, "count": 100},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )

            if resp.status_code != 200:
                print(f"\n  YC API {resp.status_code} on page {page}. Stopping.")
                break

            data = resp.json()
            companies = data.get("companies", [])
            if not companies:
                print(f"\n  No more companies at page {page}.")
                break

            for c in companies:
                if len(new_companies) >= TOPUP_TARGET:
                    break

                name   = (c.get("name") or "").strip().lower()
                batch  = c.get("batch", "") or ""
                status = c.get("status", "") or ""
                stage  = assign_stage(batch, status)

                # Skip duplicates
                if name in existing_names:
                    skipped_dupe += 1
                    continue

                # Skip public and inactive
                if stage == "skip":
                    skipped_public += 1
                    continue

                # Skip Pre-Seed
                if stage == "Pre-Seed":
                    skipped_preseed += 1
                    continue

                new_companies.append((c, stage))
                existing_names.add(name)  # prevent future dupes in same run

            print(f"  Page {page}: {len(new_companies)} new | skip dupe={skipped_dupe} public={skipped_public} preseed={skipped_preseed}", end='\r')
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"\n  Error page {page}: {e}")
            break

    print(f"\n\n  New companies found:   {len(new_companies)}")
    print(f"  Skipped duplicates:    {skipped_dupe}")
    print(f"  Skipped public:        {skipped_public}")
    print(f"  Skipped Pre-Seed:      {skipped_preseed}")

    # Stage breakdown
    stages = Counter(s for _, s in new_companies)
    print(f"\n  Stage breakdown:")
    for stage, count in sorted(stages.items()):
        print(f"    {stage}: {count}")

    if not new_companies:
        print("\n  No new companies to add.")
        return

    print(f"\n  Ready to write {len(new_companies)} records.")
    confirm = input("  Proceed? (y/n): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Aborted.")
        return

    print("\nWriting to Airtable...")
    total_written  = 0
    records_buffer = []

    for c, stage in new_companies:
        records_buffer.append(transform(c, stage))
        if len(records_buffer) == 10:
            total_written += write_batch(records_buffer, total_written)
            records_buffer = []
            time.sleep(0.25)

    if records_buffer:
        total_written += write_batch(records_buffer, total_written)

    print(f"\n\n{'=' * 55}")
    print(f"  Done.")
    print(f"  New records written: {total_written}")
    print(f"  Total in table now:  {len(existing_names)}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
