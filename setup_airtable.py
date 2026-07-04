"""
vc-startup-tracker — Airtable Table Setup
==========================================
Creates all required fields in your Airtable table
before running the scraper.

Run this ONCE before running scraper.py:
    python setup_airtable.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE   = os.getenv("AIRTABLE_TABLE_NAME", "startups")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# ── Field definitions ────────────────────────────────────
# Airtable field types:
# singleLineText, multilineText, url, singleSelect, date, checkbox
FIELDS = [
    {
        "name": "Name",
        "type": "singleLineText",
        "description": "Company name"
    },
    {
        "name": "Batch",
        "type": "singleLineText",
        "description": "YC batch e.g. W21, S22"
    },
    {
        "name": "Sector",
        "type": "singleLineText",
        "description": "Industry tags from YC"
    },
    {
        "name": "Description",
        "type": "multilineText",
        "description": "One-line company description"
    },
    {
        "name": "Website",
        "type": "url",
        "description": "Company website URL"
    },
    {
        "name": "Status",
        "type": "singleSelect",
        "description": "Current company status",
        "options": {
            "choices": [
                {"name": "Active",   "color": "greenBright"},
                {"name": "Acquired", "color": "blueBright"},
                {"name": "Public",   "color": "purpleBright"},
                {"name": "Dead",     "color": "redBright"},
                {"name": "Unknown",  "color": "grayBright"}
            ]
        }
    },
    {
        "name": "Location",
        "type": "singleLineText",
        "description": "Company HQ location"
    },
    {
        "name": "Stage",
        "type": "singleSelect",
        "description": "Current funding stage",
        "options": {
            "choices": [
                {"name": "Pre-Seed", "color": "grayBright"},
                {"name": "Seed",     "color": "greenBright"},
                {"name": "Series A", "color": "blueBright"},
                {"name": "Series B", "color": "purpleBright"},
                {"name": "Series C+","color": "yellowBright"}
            ]
        }
    },
    {
        "name": "Current AWS Stack",
        "type": "multilineText",
        "description": "AWS services active at this stage"
    },
    {
        "name": "Next AWS Recommendations",
        "type": "multilineText",
        "description": "AWS services to adopt next"
    },
    {
        "name": "Stage Signals",
        "type": "multilineText",
        "description": "Metrics that trigger next stage upgrade"
    },
    {
        "name": "Source",
        "type": "singleSelect",
        "description": "Where this record came from",
        "options": {
            "choices": [
                {"name": "YC Scrape",    "color": "greenBright"},
                {"name": "Manual Add",   "color": "blueBright"},
                {"name": "Crunchbase",   "color": "orangeBright"},
                {"name": "Other",        "color": "grayBright"}
            ]
        }
    },
    {
        "name": "Date Added",
        "type": "singleLineText",
        "description": "Date record was added"
    },
    {
        "name": "Notes",
        "type": "multilineText",
        "description": "Manager notes — free text"
    },
    # ── Manager Portfolio fields ─────────────────────────
    {
        "name": "Assigned To",
        "type": "singleLineText",
        "description": "Manager name responsible for this startup"
    },
    {
        "name": "Priority",
        "type": "singleSelect",
        "description": "Manager priority level",
        "options": {
            "choices": [
                {"name": "High",   "color": "redBright"},
                {"name": "Medium", "color": "yellowBright"},
                {"name": "Low",    "color": "grayBright"}
            ]
        }
    },
    {
        "name": "Relationship Status",
        "type": "singleSelect",
        "description": "Manager relationship with startup",
        "options": {
            "choices": [
                {"name": "Active",     "color": "greenBright"},
                {"name": "Monitoring", "color": "yellowBright"},
                {"name": "Dormant",    "color": "grayBright"}
            ]
        }
    },
    {
        "name": "Last Contact Date",
        "type": "singleLineText",
        "description": "Date of last contact with startup"
    },
    {
        "name": "Next Action",
        "type": "singleLineText",
        "description": "Next action item for this startup"
    },
    {
        "name": "Next Action Due",
        "type": "singleLineText",
        "description": "Due date for next action"
    },
    {
        "name": "Date Assigned",
        "type": "singleLineText",
        "description": "Date startup was assigned to manager"
    },
    # ── Funding round fields ─────────────────────────────
    {
        "name": "Funding Rounds",
        "type": "multilineText",
        "description": "JSON array of funding rounds with amount, date, investor"
    },
    {
        "name": "Total Raised",
        "type": "singleLineText",
        "description": "Total funding raised to date"
    },
    {
        "name": "Latest Round",
        "type": "singleLineText",
        "description": "Most recent funding round name"
    },
    {
        "name": "Latest Round Date",
        "type": "singleLineText",
        "description": "Date of most recent funding round"
    },
    {
        "name": "Lead Investor",
        "type": "singleLineText",
        "description": "Lead investor in latest round"
    },
    # ── AI advisory field ────────────────────────────────
    {
        "name": "Claude Advisory",
        "type": "multilineText",
        "description": "Claude-generated AWS advisory for this startup"
    },
    {
        "name": "Advisory Generated",
        "type": "singleLineText",
        "description": "Date Claude advisory was last generated"
    },
    {
        "name": "Added By",
        "type": "singleLineText",
        "description": "Manager who added this record"
    }
]

# ── Fetch existing fields in the table ───────────────────
def get_existing_fields() -> set:
    url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        print(f"ERROR fetching tables: {resp.status_code} — {resp.text[:300]}")
        return set()

    tables = resp.json().get("tables", [])
    for table in tables:
        if table.get("name") == AIRTABLE_TABLE:
            existing = {f["name"] for f in table.get("fields", [])}
            print(f"Found table '{AIRTABLE_TABLE}' with {len(existing)} existing fields.")
            return existing, table.get("id")

    print(f"Table '{AIRTABLE_TABLE}' not found in base.")
    return set(), None

# ── Create a single field ────────────────────────────────
def create_field(table_id: str, field: dict) -> bool:
    url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables/{table_id}/fields"

    payload = {
        "name": field["name"],
        "type": field["type"]
    }

    if "description" in field:
        payload["description"] = field["description"]

    if "options" in field:
        payload["options"] = field["options"]

    resp = requests.post(url, headers=HEADERS, json=payload)

    if resp.status_code == 200:
        print(f"  ✓ Created field: {field['name']}")
        return True
    else:
        err = resp.json().get("error", {})
        print(f"  ✗ Failed: {field['name']} — {err.get('type', '')} {err.get('message', resp.text[:100])}")
        return False

# ── Main ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  vc-startup-tracker — Airtable Setup")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env file.")
        print("Add your token to .env and try again.")
        return

    print(f"\nBase:  {AIRTABLE_BASE_ID}")
    print(f"Table: {AIRTABLE_TABLE}")
    print()

    # Get existing fields
    result = get_existing_fields()
    if isinstance(result, set):
        print("Could not retrieve table info. Exiting.")
        return

    existing_fields, table_id = result

    if not table_id:
        print(f"\nERROR: Table '{AIRTABLE_TABLE}' not found.")
        print("Please create the table manually in Airtable first, then re-run this script.")
        print("Steps:")
        print("  1. Go to airtable.com")
        print(f"  2. Open base {AIRTABLE_BASE_ID}")
        print(f"  3. Add a new table named '{AIRTABLE_TABLE}'")
        print("  4. Re-run this script")
        return

    # Create missing fields
    print(f"\nCreating fields (skipping existing):\n")
    created = 0
    skipped = 0

    # Note: Airtable always has a default "Name" field — skip creating it
    # but we still need to track it as existing
    existing_fields.add("Name")

    for field in FIELDS:
        if field["name"] in existing_fields:
            print(f"  — Skipped (exists): {field['name']}")
            skipped += 1
        else:
            success = create_field(table_id, field)
            if success:
                created += 1
            import time
            time.sleep(0.3)  # rate limit

    print(f"\n{'=' * 55}")
    print(f"  Setup complete.")
    print(f"  Fields created: {created}")
    print(f"  Fields skipped: {skipped}")
    print(f"\n  Next step: run python scraper.py")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
