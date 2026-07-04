"""
vc-startup-tracker — Balanced Fresh Load
==========================================
Loads 900 YC companies with a balanced stage mix:
  Seed:      350 (newest first)
  Series A:  300
  Series B:  150
  Series C+: 100 (no public companies)

- No Pre-Seed
- No public companies
- Real sector tags prioritized
- Newer batches preferred within each stage

Run: python load_balanced.py
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

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# Stage quotas
QUOTAS = {
    "Seed":      350,
    "Series A":  300,
    "Series B":  150,
    "Series C+": 100,
}
TARGET_COUNT = sum(QUOTAS.values())  # 900

# Statuses to exclude
EXCLUDE_STATUSES = {"public"}

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
    if status_lower in ["acquired"]:
        return "Series C+"
    if status_lower == "public":
        return "public"  # flag for exclusion
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

def write_batch(records, written_so_far):
    payload = {"records": [{"fields": r} for r in records]}
    resp = requests.post(AIRTABLE_URL, headers=HEADERS, json=payload)
    if resp.status_code == 200:
        total = written_so_far + len(records)
        print(f"  {total}/{TARGET_COUNT} written ✓", end='\r')
        return len(records)
    else:
        print(f"\n  ERROR: {resp.status_code} — {resp.text[:150]}")
        return 0

def main():
    print("=" * 55)
    print("  vc-startup-tracker — Balanced Fresh Load")
    print(f"  Target: {TARGET_COUNT} records")
    print(f"  Quotas: Seed={QUOTAS['Seed']} | A={QUOTAS['Series A']} | B={QUOTAS['Series B']} | C+={QUOTAS['Series C+']}")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env")
        return

    # Buckets per stage — two tiers: with tags, without tags
    buckets = {
        "Seed":      {"tagged": [], "untagged": []},
        "Series A":  {"tagged": [], "untagged": []},
        "Series B":  {"tagged": [], "untagged": []},
        "Series C+": {"tagged": [], "untagged": []},
    }

    skipped_preseed  = 0
    skipped_public   = 0
    page = 1

    print("\nFetching YC companies...")
    print("-" * 55)

    while True:
        # Check if all quotas are satisfied
        filled = all(
            len(b["tagged"]) + len(b["untagged"]) >= QUOTAS[stage]
            for stage, b in buckets.items()
        )
        if filled:
            print(f"\n  All quotas filled. Stopping at page {page}.")
            break

        try:
            resp = requests.get(
                YC_API_URL,
                params={"page": page, "count": 100},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )

            if resp.status_code != 200:
                print(f"\n  YC API {resp.status_code} on page {page}. Done.")
                break

            data = resp.json()
            companies = data.get("companies", [])
            if not companies:
                print(f"\n  No more companies at page {page}.")
                break

            for c in companies:
                batch  = c.get("batch", "") or ""
                status = c.get("status", "") or ""
                stage  = assign_stage(batch, status)

                # Skip public
                if stage == "public" or (status or "").lower() == "public":
                    skipped_public += 1
                    continue

                # Skip Pre-Seed
                if stage == "Pre-Seed":
                    skipped_preseed += 1
                    continue

                # Skip unknown stages
                if stage not in buckets:
                    continue

                # Skip if this bucket is already full
                bucket = buckets[stage]
                if len(bucket["tagged"]) + len(bucket["untagged"]) >= QUOTAS[stage]:
                    continue

                # Add to appropriate tier
                tags = c.get("tags") or []
                if tags:
                    bucket["tagged"].append(c)
                else:
                    bucket["untagged"].append(c)

            # Progress
            counts = {s: len(b["tagged"])+len(b["untagged"]) for s,b in buckets.items()}
            print(f"  Page {page}: Seed={counts['Seed']} A={counts['Series A']} B={counts['Series B']} C+={counts['Series C+']} | skip public={skipped_public} preseed={skipped_preseed}", end='\r')
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"\n  Error page {page}: {e}")
            break

    # Compile final list — tagged first within each stage
    final = []
    for stage, quota in QUOTAS.items():
        bucket = buckets[stage]
        combined = bucket["tagged"] + bucket["untagged"]
        selected = combined[:quota]
        final.extend([(c, stage) for c in selected])
        print(f"\n  {stage}: {len(selected)}/{quota} (tagged={len(bucket['tagged'][:quota])}, untagged={max(0, len(selected)-len(bucket['tagged'][:quota]))})")

    print(f"\n  Total to write: {len(final)}")
    print(f"  Skipped public:   {skipped_public}")
    print(f"  Skipped Pre-Seed: {skipped_preseed}")

    # Batch year range per stage
    print(f"\n  Batch range per stage:")
    for stage in QUOTAS:
        stage_companies = [c for c, s in final if s == stage]
        years = [batch_year(c.get("batch","")) for c in stage_companies if batch_year(c.get("batch","")) != 99]
        if years:
            print(f"    {stage}: W{min(years):02d} – W{max(years):02d}")

    print(f"\n  Ready to write {len(final)} records.")
    confirm = input("  Proceed? (y/n): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Aborted.")
        return

    print("\nWriting to Airtable...")
    total_written = 0
    batch_num = 1
    records_buffer = []

    for c, stage in final:
        records_buffer.append(transform(c, stage))
        if len(records_buffer) == 10:
            written = write_batch(records_buffer, total_written)
            total_written += written
            records_buffer = []
            batch_num += 1
            time.sleep(0.25)

    # Write remaining
    if records_buffer:
        written = write_batch(records_buffer, total_written)
        total_written += written

    print(f"\n\n{'=' * 55}")
    print(f"  Done.")
    print(f"  Total written: {total_written}")
    print(f"  Base:  {AIRTABLE_BASE_ID}")
    print(f"  Table: {AIRTABLE_TABLE}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
