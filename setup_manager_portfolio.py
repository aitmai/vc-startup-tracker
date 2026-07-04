"""
vc-startup-tracker — Manager Portfolio Table Setup
===================================================
Creates all required fields in the manager_portfolio
Airtable table.

Run this ONCE before using the dashboard:
    python setup_manager_portfolio.py
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME       = "manager_portfolio"
TABLE_ID         = "tblQImKHs7SgsvDCW"

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# ── Field definitions ────────────────────────────────────
FIELDS = [
    # ── Identity ─────────────────────────────────────────
    {
        "name": "Manager Name",
        "type": "singleLineText",
        "description": "Full name of the investor manager"
    },
    {
        "name": "Manager Email",
        "type": "email",
        "description": "Manager email address"
    },
    # ── Startup reference ────────────────────────────────
    {
        "name": "Startup Name",
        "type": "singleLineText",
        "description": "Company name — matches Name field in startups table"
    },
    {
        "name": "Startup Website",
        "type": "url",
        "description": "Company website"
    },
    {
        "name": "Sector",
        "type": "singleLineText",
        "description": "Industry sector"
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
    # ── Assignment ───────────────────────────────────────
    {
        "name": "Date Assigned",
        "type": "singleLineText",
        "description": "Date this startup was assigned to the manager"
    },
    {
        "name": "Priority",
        "type": "singleSelect",
        "description": "Manager priority level for this startup",
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
        "description": "Current relationship status with startup",
        "options": {
            "choices": [
                {"name": "Active",     "color": "greenBright"},
                {"name": "Monitoring", "color": "yellowBright"},
                {"name": "Dormant",    "color": "grayBright"}
            ]
        }
    },
    # ── Contact tracking ─────────────────────────────────
    {
        "name": "Last Contact Date",
        "type": "singleLineText",
        "description": "Date of last contact with this startup"
    },
    {
        "name": "Last Contact Type",
        "type": "singleSelect",
        "description": "Type of last contact",
        "options": {
            "choices": [
                {"name": "Email",   "color": "blueBright"},
                {"name": "Call",    "color": "greenBright"},
                {"name": "Meeting", "color": "purpleBright"},
                {"name": "Event",   "color": "orangeBright"},
                {"name": "Other",   "color": "grayBright"}
            ]
        }
    },
    {
        "name": "Days Since Contact",
        "type": "singleLineText",
        "description": "Auto-calculated days since last contact"
    },
    # ── Next action ──────────────────────────────────────
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
        "name": "Next Action Status",
        "type": "singleSelect",
        "description": "Status of next action",
        "options": {
            "choices": [
                {"name": "Pending",     "color": "yellowBright"},
                {"name": "In Progress", "color": "blueBright"},
                {"name": "Done",        "color": "greenBright"},
                {"name": "Overdue",     "color": "redBright"}
            ]
        }
    },
    # ── Funding rounds ───────────────────────────────────
    {
        "name": "Funding Rounds",
        "type": "multilineText",
        "description": "JSON array of funding rounds: [{round, amount, date, investor}]"
    },
    {
        "name": "Total Raised",
        "type": "singleLineText",
        "description": "Total funding raised to date"
    },
    {
        "name": "Latest Round",
        "type": "singleSelect",
        "description": "Most recent funding round",
        "options": {
            "choices": [
                {"name": "Pre-Seed", "color": "grayBright"},
                {"name": "Seed",     "color": "greenBright"},
                {"name": "Series A", "color": "blueBright"},
                {"name": "Series B", "color": "purpleBright"},
                {"name": "Series C", "color": "yellowBright"},
                {"name": "Series D+","color": "orangeBright"},
                {"name": "IPO",      "color": "pinkBright"}
            ]
        }
    },
    {
        "name": "Latest Round Date",
        "type": "singleLineText",
        "description": "Date of most recent funding round"
    },
    {
        "name": "Latest Round Amount",
        "type": "singleLineText",
        "description": "Amount raised in most recent round"
    },
    {
        "name": "Lead Investor",
        "type": "singleLineText",
        "description": "Lead investor in latest round"
    },
    # ── AWS / Tech stack ─────────────────────────────────
    {
        "name": "Current Tech Stack",
        "type": "multilineText",
        "description": "Tech services active at current stage"
    },
    {
        "name": "Next Tech Recommendations",
        "type": "multilineText",
        "description": "Tech services recommended for next stage"
    },
    {
        "name": "Stage Signals",
        "type": "multilineText",
        "description": "Metrics that would trigger next stage upgrade"
    },
    # ── Claude advisory ──────────────────────────────────
    {
        "name": "Claude Advisory",
        "type": "multilineText",
        "description": "Claude-generated investment advisory for this startup"
    },
    {
        "name": "Advisory Generated",
        "type": "singleLineText",
        "description": "Date Claude advisory was last generated"
    },
    # ── Notes log ────────────────────────────────────────
    {
        "name": "Notes",
        "type": "multilineText",
        "description": "Manager notes — timestamped log entries"
    },
    {
        "name": "Internal Tags",
        "type": "singleLineText",
        "description": "Comma-separated internal tags for filtering"
    },
    # ── Meta ─────────────────────────────────────────────
    {
        "name": "Date Added",
        "type": "singleLineText",
        "description": "Date this record was created"
    },
    {
        "name": "Added By",
        "type": "singleLineText",
        "description": "Manager who created this record"
    },
    {
        "name": "Source",
        "type": "singleSelect",
        "description": "How this startup was added to portfolio",
        "options": {
            "choices": [
                {"name": "YC Database",  "color": "greenBright"},
                {"name": "Manual Add",   "color": "blueBright"},
                {"name": "Referral",     "color": "purpleBright"},
                {"name": "Event",        "color": "orangeBright"},
                {"name": "Inbound",      "color": "yellowBright"},
                {"name": "Other",        "color": "grayBright"}
            ]
        }
    }
]

# ── Get existing fields ──────────────────────────────────
def get_existing_fields() -> set:
    url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        print(f"ERROR fetching tables: {resp.status_code} — {resp.text[:300]}")
        return set()

    tables = resp.json().get("tables", [])
    for table in tables:
        if table.get("name") == TABLE_NAME:
            existing = {f["name"] for f in table.get("fields", [])}
            print(f"Found table '{TABLE_NAME}' with {len(existing)} existing fields.")
            return existing

    print(f"Table '{TABLE_NAME}' not found.")
    return set()

# ── Create a single field ────────────────────────────────
def create_field(field: dict) -> bool:
    url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables/{TABLE_ID}/fields"

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
        print(f"  ✓ Created: {field['name']}")
        return True
    else:
        err = resp.json().get("error", {})
        print(f"  ✗ Failed:  {field['name']} — {err.get('type', '')} {err.get('message', resp.text[:100])}")
        return False

# ── Main ────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  vc-startup-tracker — Manager Portfolio Setup")
    print("=" * 55)

    if not AIRTABLE_TOKEN or "XXXX" in AIRTABLE_TOKEN:
        print("\nERROR: AIRTABLE_TOKEN not set in .env file.")
        return

    print(f"\nBase:  {AIRTABLE_BASE_ID}")
    print(f"Table: {TABLE_NAME}")
    print(f"ID:    {TABLE_ID}")
    print()

    existing_fields = get_existing_fields()
    if not existing_fields and existing_fields != set():
        return

    # Airtable default Name field always exists
    existing_fields.add("Name")

    print(f"\nCreating fields (skipping existing):\n")
    created = 0
    skipped = 0

    for field in FIELDS:
        if field["name"] in existing_fields:
            print(f"  — Skipped (exists): {field['name']}")
            skipped += 1
        else:
            success = create_field(field)
            if success:
                created += 1
            time.sleep(0.3)

    print(f"\n{'=' * 55}")
    print(f"  Setup complete.")
    print(f"  Fields created: {created}")
    print(f"  Fields skipped: {skipped}")
    print(f"\n  Next step: build the React dashboard")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    main()
