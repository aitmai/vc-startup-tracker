"""
vc-startup-tracker — Trim Startups Table (Pass 2)
==================================================
Aggressively trims to 900 records by removing
old batches (W22 and older) until under target.

Run: python trim_startups2.py
"""

import os
import time
import re
import requests
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE   = os.getenv("AIRTABLE_TABLE_NAME", "startups")
AIRTABLE_URL     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
TARGET_COUNT     = 900

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

def fetch_all_records():
    records = []
    offset = None
    print("Fetching all records...")
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(AIRTABLE_URL, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"ERROR: {resp.status_code} — {resp.text[:200]}")
            break
        data = resp.json()
        records.extend(data.get("records", []))
        print(f"  {len(records)} records fetched...")
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.2)
    print(f"Total: {len(records)}")
    return records

def batch_year(batch_str):
    if not batch_str:
        return 99  # no batch = treat as recent, keep
    match = re.search(r'(\d{2,4})', str(batch_str))
    if not match:
        return 99
    year = int(match.group(1))
    if year > 2000:
        return year - 2000
    return year

def delete_batch(records_to_delete):
    deleted = 0
    for i in range(0, len(records_to_delete), 10):
        batch = records_to_delete[i:i+10]
        ids = [r["id"] for r in batch]
        params = "&".join([f"records[]={rid}" for rid in ids])
        resp = requests.delete(f"{AIRTABLE_URL}?{params}", headers=HEADERS)
        if resp.status_code == 200:
            deleted += len(ids)
            print(f"  Deleted {deleted}/{len(records_to_delete)} ✓", end='\r')
        else:
            print(f"\n  ERROR: {resp.status_code} — {resp.text[:100]}")
        time.sleep(0.25)
    print()
    return deleted

def main():
    print("=" * 55)
    print("  Trim Startups — Pass 2")
    print(f"  Target: {TARGET_COUNT} records")
    print("=" * 55)

    records = fetch_all_records()
    total = len(records)

    if total <= TARGET_COUNT:
        print(f"\nAlready at {total} records. Done.")
        return

    need_to_delete = total - TARGET_COUNT
    print(f"\nNeed to delete: {need_to_delete} records")

    # Sort all records by batch year ascending (oldest first)
    records.sort(key=lambda r: batch_year(r.get("fields", {}).get("Batch", "")))

    # Show breakdown by year
    from collections import Counter
    year_counts = Counter(
        batch_year(r.get("fields", {}).get("Batch", "")) 
        for r in records
    )
    print("\nBatch year breakdown (oldest first):")
    for yr in sorted(year_counts.keys()):
        label = f"W{yr:02d}/S{yr:02d}" if yr < 99 else "No batch"
        print(f"  {label}: {year_counts[yr]} companies")

    # Mark oldest records for deletion until we hit the target
    to_delete = records[:need_to_delete]
    to_keep   = records[need_to_delete:]

    # Show what will be deleted
    delete_years = Counter(
        batch_year(r.get("fields", {}).get("Batch", ""))
        for r in to_delete
    )
    print(f"\nWill delete {len(to_delete)} records from batches:")
    for yr in sorted(delete_years.keys()):
        label = f"W{yr:02d}/S{yr:02d}" if yr < 99 else "No batch"
        print(f"  {label}: {delete_years[yr]}")

    keep_years = Counter(
        batch_year(r.get("fields", {}).get("Batch", ""))
        for r in to_keep
    )
    print(f"\nWill keep {len(to_keep)} records from batches:")
    for yr in sorted(keep_years.keys()):
        label = f"W{yr:02d}/S{yr:02d}" if yr < 99 else "No batch"
        print(f"  {label}: {keep_years[yr]}")

    print("\n" + "=" * 55)
    confirm = input("Proceed with deletion? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    print(f"\nDeleting {len(to_delete)} records...")
    delete_batch(to_delete)

    # Verify
    time.sleep(2)
    final = fetch_all_records()
    print(f"\n{'=' * 55}")
    print(f"  Done.")
    print(f"  Before: {total}")
    print(f"  After:  {len(final)}")
    print(f"  Deleted: {total - len(final)}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
