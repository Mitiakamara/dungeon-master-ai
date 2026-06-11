"""SAM-044 / SAM-029 harness — atomic per-character state_update consolidation.
Run: ./venv/Scripts/python.exe _test_sam044.py   (temp; delete after)."""
from types import SimpleNamespace
from server import apply_state_updates


class FakeQuery:
    def __init__(self, recorder, table, fail_ids):
        self.recorder, self.table, self.fail_ids = recorder, table, fail_ids
        self._payload = None
        self._id = None

    def update(self, payload):
        self._payload = payload
        return self

    def eq(self, field, val):
        self._id = val
        return self

    def execute(self):
        if self._id in self.fail_ids:
            raise RuntimeError(f"simulated flush failure for {self._id}")
        self.recorder.append({"id": self._id, "payload": self._payload})
        return SimpleNamespace(data=[{}])


class FakeSupabase:
    def __init__(self, fail_ids=()):
        self.writes = []
        self.fail_ids = set(fail_ids)

    def table(self, name):
        return FakeQuery(self.writes, name, self.fail_ids)


def bjorn():
    return {"id": "B", "name": "Björn Glacierfist", "class": "Barbarian 7", "level": 7,
            "stats": {"con": 16}, "status": {"money": {"gp": 0}, "xp": 0,
            "inventory": [], "hp_current": 30, "hp_max": 50}}

def vex():
    return {"id": "V", "name": "Vex Was", "class": "Rogue 7", "level": 7,
            "status": {"money": {"gp": 0}, "xp": 0, "inventory": [], "hp_current": 40, "hp_max": 40}}


results = []
def check(name, cond):
    results.append((name, cond))
    print(f"  {'✅' if cond else '❌ FAIL'} {name}")


# ── Scenario 1 — EL CASO BJÖRN: xp + money + item, same char, one request ──
print("Scenario 1 — Björn: xp_update + money_award + item_award")
sb = FakeSupabase()
out = apply_state_updates(sb, [bjorn(), vex()], [
    {"type": "xp_update", "character_id": "B", "new_xp": 350, "xp_gained": 350},
    {"type": "money_award", "character_id": "B", "gp": 17},
    {"type": "item_award", "character_id": "B", "item": {"item": "Smooth River Stone", "qty": 1}},
])
b_writes = [w for w in sb.writes if w["id"] == "B"]
check("exactly ONE write for Björn", len(b_writes) == 1)
st = b_writes[0]["payload"]["status"]
check("xp = 350 survived", st.get("xp") == 350)
check("money.gp = 17 survived", st.get("money", {}).get("gp") == 17)
check("item in inventory", any(i.get("item") == "Smooth River Stone" for i in st.get("inventory", [])))

# ── Scenario 2 — two characters interleaved, no cross-contamination ──
print("Scenario 2 — interleaved updates to two characters")
sb = FakeSupabase()
apply_state_updates(sb, [bjorn(), vex()], [
    {"type": "xp_update", "character_id": "B", "new_xp": 350},
    {"type": "xp_update", "character_id": "V", "new_xp": 350},
    {"type": "money_award", "character_id": "B", "gp": 17},
    {"type": "money_award", "character_id": "V", "gp": 17},
    {"type": "item_award", "character_id": "B", "item": {"item": "Stone", "qty": 1}},
])
check("one write each (2 total)", len(sb.writes) == 2)
bw = next(w for w in sb.writes if w["id"] == "B")["payload"]["status"]
vw = next(w for w in sb.writes if w["id"] == "V")["payload"]["status"]
check("Björn has xp+gp+item", bw.get("xp") == 350 and bw["money"]["gp"] == 17 and len(bw["inventory"]) == 1)
check("Vex has xp+gp, NO item", vw.get("xp") == 350 and vw["money"]["gp"] == 17 and len(vw["inventory"]) == 0)

# ── Scenario 3 — player_hp + money_award same char both survive ──
print("Scenario 3 — player_hp + money_award same char")
sb = FakeSupabase()
apply_state_updates(sb, [bjorn()], [
    {"type": "player_hp", "character_id": "B", "new_hp": 10},
    {"type": "money_award", "character_id": "B", "gp": 5},
])
st = sb.writes[0]["payload"]["status"]
check("hp_current = 10 AND money.gp = 5", st.get("hp_current") == 10 and st["money"]["gp"] == 5)

# ── Scenario 4 — xp_update with level-up: status + level + class in ONE write ──
print("Scenario 4 — level-up flushes status + top-level columns together")
sb = FakeSupabase()
apply_state_updates(sb, [bjorn()], [
    {"type": "xp_update", "character_id": "B", "new_xp": 34000, "leveled_up": True,
     "new_level": 8, "new_hp_max": 62, "new_hp_current": 42},
])
p = sb.writes[0]["payload"]
check("single update call", len(sb.writes) == 1)
check("status + level + class in same payload",
      "status" in p and p.get("level") == 8 and p.get("class") == "Barbarian 8")
check("hp_max grown in status", p["status"].get("hp_max") == 62)

# ── Scenario 5 — find_char by id (wins over wrong name) and by name fallback ──
print("Scenario 5 — id resolution vs name fallback")
sb = FakeSupabase()
apply_state_updates(sb, [bjorn(), vex()], [
    # id=V wins even though name points elsewhere
    {"type": "money_award", "character_id": "V", "character_name": "WRONGNAME", "gp": 9},
    # no id → name fallback, case-insensitive
    {"type": "money_award", "character_name": "björn glacierfist", "gp": 3},
])
vw = next((w for w in sb.writes if w["id"] == "V"), None)
bw = next((w for w in sb.writes if w["id"] == "B"), None)
check("id wins → Vex got the 9 gp", vw and vw["payload"]["status"]["money"]["gp"] == 9)
check("name fallback (case-insensitive) → Björn got 3 gp", bw and bw["payload"]["status"]["money"]["gp"] == 3)

# ── Scenario 6 — flush fails for one char, the other still persists ──
print("Scenario 6 — flush failure isolated per character")
sb = FakeSupabase(fail_ids=["B"])
try:
    apply_state_updates(sb, [bjorn(), vex()], [
        {"type": "money_award", "character_id": "B", "gp": 17},
        {"type": "money_award", "character_id": "V", "gp": 17},
    ])
    no_raise = True
except Exception:
    no_raise = False
check("no exception propagated", no_raise)
check("Vex persisted despite Björn flush failure",
      len(sb.writes) == 1 and sb.writes[0]["id"] == "V")

# ── Summary ──
passed = sum(1 for _, c in results if c)
print(f"\n{passed}/{len(results)} checks passed")
print("ALL PASS ✅" if passed == len(results) else "SOME FAILED ❌")
