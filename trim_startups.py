"""
vc-startup-tracker — Trim Startups Table
==========================================
Reduces the startups table to 900 records by:
1. Removing Dead / Inactive companies first
2. Removing companies from batches older than W20/S20
3. Deleting oldest batches until under 900 records

Run: python trim_startups.py
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE   = os.getenv("AIRTABLE_TABLE_NAME", "startups")
AIRTABLE_URL     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
TARGET_COUNT     = 900

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# Batches to remove — W19 and older, S19 and older
CUTOFF_YEAR = 20  # W20/S20 is the oldest we keep

# Statuses to remove
DEAD_STATUSES = {"dead", "inactive", "closed", "shutdown"}

# ── Fetch all records ────────────────────────────────────
def fetch_all_records():
    records = []
    offset = None
    print("Fetching all records from Airtable...")

    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset

        resp = requests.get(AIRTABLE_URL, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"  ERROR: {resp.status_code} — {resp.text[:200]}")
            break

        data = resp.json()
        batch = data.get("records", [])
        records.extend(batch)
        print(f"  Fetched {len(records)} records so far...")

        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.2)

    print(f"Total fetched: {len(records)}")
    return records

# ── Parse batch year ─────────────────────────────────────
def batch_year(batch_str):
    """Extract year from batch string like W21, S22, IK12, etc."""
    if not batch_str:
        return 0
    # Find 2-digit year in the batch string
    import re
    match = re.search(r'(\d{2,4})', batch_str)
    if not match:
        return 0
    year = int(match.group(1))
    # Handle 4-digit years
    if year > 2000:
        return year - 2000
    return year

# ── Classify records ─────────────────────────────────────
def classify_records(records):
    dead      = []  # Dead/Inactive status
    old_batch = []  # Active but W19 and older
    keep      = []  # Active + W20 or newer

    for r in records:
        f = r.get("fields", {})
        status = (f.get("Status") or "").strip().lower()
        batch  = (f.get("Batch") or "").strip()
        year   = batch_year(batch)

        if status in DEAD_STATUSES:
            dead.append(r)
        elif year > 0 and year < CUTOFF_YEAR:
            old_batch.append(r)
        else:
            keep.append(r)

    # Sort old_batch by year ascending (oldest first to delete first)
    old_batch.sort(key=lambda r: batch_year(r.get("fields", {}).get("Batch", "")))

    print(f"\nClassification:")
    print(f"  Dead/Inactive:     {len(dead)}")
    print(f"  Old batches (<W20): {len(old_batch)}")
    print(f"  Keep (Active+W20+): {len(keep)}")
    print(f"  Total:             {len(records)}")

    return dead, old_batch, keep

# ── Delete records in batches of 10 ─────────────────────
def delete_records(records, label):
    if not records:
        print(f"  No {label} records to delete.")
        return 0

    deleted = 0
    print(f"\nDeleting {len(records)} {label} records...")

    for i in range(0, len(records), 10):
        batch = records[i:i+10]
        ids   = [r["id"] for r in batch]

        # Airtable batch delete — pass record IDs as query params
        params = "&".join([f"records[]={rid}" for rid in ids])
        resp = requests.delete(
            f"{AIRTABLE_URL}?{params}",
            headers=HEADERS
        )

        if resp.status_code == 200:
            deleted += len(ids)
            print(f"  Deleted {deleted}/{len(records)} {label} records ✓")
        else:
            print(f"  ERROR deleting batch: {resp.status_code} — {resp.text[:100]}")

        time.sleep(0.25)  # rate limit

    return deleted

# ── Main ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  vc-startup-tracker — Trim Startups Table")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env file.")
        return

    print(f"\nBase:   {AIRTABLE_BASE_ID}")
    print(f"Table:  {AIRTABLE_TABLE}")
    print(f"Target: {TARGET_COUNT} records")

    # 1. Fetch all
    records = fetch_all_records()
    total   = len(records)

    if total <= TARGET_COUNT:
        print(f"\nAlready at {total} records — no trimming needed.")
        return

    # 2. Classify
    dead, old_batch, keep = classify_records(records)

    # 3. Delete dead/inactive first
    to_delete  = []
    to_delete += dead

    remaining_after_dead = total - len(dead)
    print(f"\nAfter removing dead: {remaining_after_dead} records")

    # 4. If still over target, delete old batches until under 900
    if remaining_after_dead > TARGET_COUNT:
        need_to_cut = remaining_after_dead - TARGET_COUNT
        print(f"Still need to cut {need_to_cut} more records from old batches")
        to_delete += old_batch[:need_to_cut]

    print(f"\nTotal records to delete: {len(to_delete)}")
    print(f"Records remaining after trim: {total - len(to_delete)}")

    # 5. Confirm before deleting
    print("\n" + "=" * 55)
    confirm = input("Proceed with deletion? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    # 6. Delete dead records
    delete_records(dead, "dead/inactive")

    # 7. Delete old batch records if needed
    if remaining_after_dead > TARGET_COUNT:
        need_to_cut = remaining_after_dead - TARGET_COUNT
        delete_records(old_batch[:need_to_cut], "old batch")

    # 8. Final count
    print("\nVerifying final count...")
    time.sleep(2)
    final_records = fetch_all_records()

    print(f"\n{'=' * 55}")
    print(f"  Trim complete.")
    print(f"  Before: {total}")
    print(f"  After:  {len(final_records)}")
    print(f"  Deleted: {total - len(final_records)}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
