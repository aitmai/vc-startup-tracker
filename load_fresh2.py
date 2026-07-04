"""
vc-startup-tracker — Fresh Load v2
====================================
Less strict sector filter — includes companies
without tags but labels them "Technology" instead
of skipping. Still excludes Pre-Seed.
Target: 900 records.

Run: python load_fresh2.py
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
TARGET_COUNT     = 900
YC_API_URL       = "https://api.ycombinator.com/v0.1/companies"

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
    if status and status.lower() in ["acquired", "public"]:
        return "Series C+"
    year = batch_year(batch)
    current = datetime.now().year % 100
    age = current - year
    if age <= 1:   return "Pre-Seed"
    elif age <= 2: return "Seed"
    elif age <= 4: return "Series A"
    elif age <= 6: return "Series B"
    else:          return "Series C+"

def transform(c):
    batch  = c.get("batch", "") or ""
    status = c.get("status", "Active") or "Active"
    stage  = assign_stage(batch, status)
    tags   = c.get("tags") or []
    # Use tags if available, otherwise fall back to "Technology"
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

def write_batch(records, batch_num, total):
    payload = {"records": [{"fields": r} for r in records]}
    resp = requests.post(AIRTABLE_URL, headers=HEADERS, json=payload)
    if resp.status_code == 200:
        print(f"  Batch {batch_num}: {total} total written ✓", end='\r')
        return len(records)
    else:
        print(f"\n  ERROR batch {batch_num}: {resp.status_code} — {resp.text[:150]}")
        return 0

def main():
    print("=" * 55)
    print("  vc-startup-tracker — Fresh Load v2")
    print(f"  Seed+ Only | Target: {TARGET_COUNT} records")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env")
        return

    # Two passes:
    # Pass 1 — companies WITH sector tags (higher quality)
    # Pass 2 — companies WITHOUT sector tags (fill remaining slots)

    with_tags    = []
    without_tags = []
    skipped_preseed = 0
    page = 1

    print("\nFetching YC companies (all pages)...")
    print("-" * 55)

    while True:
        try:
            resp = requests.get(
                YC_API_URL,
                params={"page": page, "count": 100},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )

            if resp.status_code != 200:
                print(f"  YC API {resp.status_code} on page {page}. Done fetching.")
                break

            data = resp.json()
            companies = data.get("companies", [])
            if not companies:
                print(f"  No more companies at page {page}.")
                break

            for c in companies:
                batch  = c.get("batch", "") or ""
                status = c.get("status", "") or ""
                stage  = assign_stage(batch, status)

                if stage == "Pre-Seed":
                    skipped_preseed += 1
                    continue

                tags = c.get("tags") or []
                if tags:
                    with_tags.append(c)
                else:
                    without_tags.append(c)

            total_qualified = len(with_tags) + len(without_tags)
            print(f"  Page {page}: {len(with_tags)} with sector | {len(without_tags)} no sector | {skipped_preseed} Pre-Seed skipped")

            # Stop once we have enough to fill 900
            if total_qualified >= TARGET_COUNT:
                print(f"  Reached {total_qualified} qualified companies. Stopping.")
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error page {page}: {e}")
            break

    # Combine: tagged first, untagged to fill remaining slots
    combined = with_tags + without_tags
    to_load  = combined[:TARGET_COUNT]

    print(f"\n  Total Seed+ companies found: {len(combined)}")
    print(f"  With real sector tags:       {len(with_tags)}")
    print(f"  Without tags (→ Technology): {len(without_tags)}")
    print(f"  Skipped Pre-Seed:            {skipped_preseed}")
    print(f"  Will load:                   {len(to_load)}")

    # Stage breakdown
    stages = Counter(assign_stage(c.get("batch",""), c.get("status","")) for c in to_load)
    print(f"\n  Stage breakdown:")
    for stage, count in sorted(stages.items()):
        print(f"    {stage}: {count}")

    print(f"\n  Ready to write {len(to_load)} records.")
    confirm = input("  Proceed? (y/n): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Aborted.")
        return

    print("\nWriting to Airtable...")
    total_written = 0
    batch_num     = 1

    for i in range(0, len(to_load), 10):
        batch   = to_load[i:i+10]
        records = [transform(c) for c in batch]
        written = write_batch(records, batch_num, total_written + len(records))
        total_written += written
        batch_num     += 1
        time.sleep(0.25)

    print(f"\n\n{'=' * 55}")
    print(f"  Done.")
    print(f"  Total written: {total_written}")
    print(f"  Base:  {AIRTABLE_BASE_ID}")
    print(f"  Table: {AIRTABLE_TABLE}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
