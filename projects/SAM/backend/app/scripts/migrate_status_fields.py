"""
Migration script: Normalize status field names in characters table.
- hp → hp_current (if hp_current missing)
- wallet → money (if money is empty/zeros)
- Remove ghost items from inventory (missing 'item' field)
- Remove obsolete fields (hp, wallet) after migration

Usage: cd projects/SAM/backend && python -m app.scripts.migrate_status_fields
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_money_empty(money: dict) -> bool:
    """Check if money dict is all zeros or empty."""
    if not money:
        return True
    return all(v == 0 for v in money.values())


def migrate():
    res = supabase.table("characters").select("id, name, status").execute()
    if not res.data:
        print("No characters found.")
        return

    updated = 0
    for char in res.data:
        name = char["name"]
        status = char.get("status") or {}
        changes = []

        # 1. hp → hp_current
        if "hp" in status:
            if "hp_current" not in status or status["hp_current"] is None:
                status["hp_current"] = status["hp"]
                changes.append(f"hp({status['hp']}) → hp_current")
            del status["hp"]
            changes.append("removed obsolete 'hp'")

        # 2. wallet → money
        if "wallet" in status:
            if "money" not in status or is_money_empty(status.get("money")):
                status["money"] = status["wallet"]
                changes.append(f"wallet → money({json.dumps(status['wallet'])})")
            del status["wallet"]
            changes.append("removed obsolete 'wallet'")

        # 3. Remove ghost items (no 'item' field)
        if "inventory" in status and isinstance(status["inventory"], list):
            before = len(status["inventory"])
            status["inventory"] = [
                item for item in status["inventory"]
                if isinstance(item, dict) and item.get("item")
            ]
            removed = before - len(status["inventory"])
            if removed > 0:
                changes.append(f"removed {removed} ghost items from inventory")

        if changes:
            print(f"[{name}] {', '.join(changes)}")
            supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
            updated += 1
        else:
            print(f"[{name}] OK — no changes needed")

    print(f"\nDone. Updated {updated}/{len(res.data)} characters.")


if __name__ == "__main__":
    migrate()
