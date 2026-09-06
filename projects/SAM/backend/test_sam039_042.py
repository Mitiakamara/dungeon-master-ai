"""SAM-039 + SAM-042 harness — strict dice validation, single-source damage
spec, weapon matching. Run: PYTHONUTF8=1 python3.14 test_sam039_042.py
(instrucción 239: pendings viven en engine.pending_rolls por character_id)"""
import inspect
from agents.mechanic import MechanicEngine
from agents.combat_state import CombatState
from agents.orchestrator import SAMOrchestrator
from agents.narrator import Narrator

orch = SAMOrchestrator(None, None)
results = []
def check(name, cond):
    results.append((name, cond))
    print(f"  {'✅' if cond else '❌ FAIL'} {name}")

def fresh_combat(hp=50):
    return CombatState({"active": True, "current_turn_index": 0, "actions_remaining": 1,
        "initiative_order": [{"name": "Wolf", "is_npc": True, "hp": hp, "hp_max": hp, "ac": 10}]})

CHAR = {"id": "b1", "name": "Björn", "status": {"attacks": [
    {"name": "Handaxe", "bonus": "+7", "damage": "1d6+4"},
    {"name": "Greataxe", "bonus": "+7", "damage": "1d12+4 slashing"},
]}}

def arm(eng, pending):
    eng.set_pending("b1", "Björn", pending)

# ── S1 — Nat 20 Greataxe → damage_spec="2d12+4", prompt matches (SAM-042) ──
print("S1 — nat 20 crit damage_spec + prompt")
c = fresh_combat(); eng = MechanicEngine(c)
arm(eng, {"type": "weapon_attack",
    "weapon": {"name": "Greataxe", "bonus": "+7", "damage": "1d12+4 slashing"},
    "target": "Wolf", "target_data": c.initiative_order[0]})
res = eng.process_player_roll(CHAR, {"dice": "1d20", "result": 20, "rolls": [20]})
check("crit detected", res.get("critical") is True)
pend = eng.get_pending("b1")
check("damage_spec doubled to 2d12+4", pend.get("damage_spec") == "2d12+4")
check("prompt says 2d12+4", "2d12+4" in orch._get_roll_prompt(pend))

# ── S2 — declared 'Greataxe' resolves to Greataxe, not Handaxe (SAM-039) ──
print("S2 — declared weapon match")
w = orch._find_weapon(CHAR, "Greataxe")
check("finds Greataxe (not Handaxe/Unarmed)", w and w["name"] == "Greataxe")

# ── S3 — colloquial names resolve to Greataxe ──
print("S3 — colloquial weapon names")
for q in ["great axe", "GreatAxe", "greataxe", "GREATAXE", "Great Axe"]:
    w = orch._find_weapon(CHAR, q)
    check(f"'{q}' → Greataxe", bool(w) and w["name"] == "Greataxe")

# ── S4 — expected 1d12, roll 1d6 → REJECT (faces), no state change ──
print("S4 — wrong faces rejected")
c = fresh_combat(); eng = MechanicEngine(c)
arm(eng, {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "1d12+4", "target": "Wolf", "target_data": c.initiative_order[0]})
res = eng.process_player_roll(CHAR, {"dice": "1d6", "result": 4, "rolls": [4]})
check("rejected as invalid_dice", res.get("action") == "invalid_dice")
check("reason = faces", res.get("reason") == "faces")
check("wolf HP unchanged (50)", c.initiative_order[0]["hp"] == 50)
check("pending preserved", eng.get_pending("b1") is not None)

# ── S5 — after reject, roll 1d12 → resolves normally ──
print("S5 — correct die after rejection resolves")
res = eng.process_player_roll(CHAR, {"dice": "1d12", "result": 10, "rolls": [10]})
check("resolves weapon_damage_applied", res.get("action") == "weapon_damage_applied")
check("wolf HP reduced to 36", c.initiative_order[0]["hp"] == 36)  # 50 - (10+4)
check("pending cleared", eng.get_pending("b1") is None)

# ── S6 — crit 2d12, roll 1d12 → REJECT (count); roll 2d12 → resolve ──
print("S6 — crit needs 2 dice")
c = fresh_combat(); eng = MechanicEngine(c)
arm(eng, {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "2d12+4", "critical": True, "target": "Wolf",
    "target_data": c.initiative_order[0]})
r1 = eng.process_player_roll(CHAR, {"dice": "1d12", "result": 10, "rolls": [10]})
check("1d12 rejected (count)", r1.get("action") == "invalid_dice" and r1.get("reason") == "count")
check("HP unchanged", c.initiative_order[0]["hp"] == 50)
r2 = eng.process_player_roll(CHAR, {"dice": "2d12", "result": 14, "rolls": [7, 7]})
check("2d12 resolves", r2.get("action") == "weapon_damage_applied")

# ── S7 — expected 1d12, roll 2d12 → REJECT (count); roll 1d12 → resolve ──
print("S7 — too many dice rejected")
c = fresh_combat(); eng = MechanicEngine(c)
arm(eng, {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "1d12+4", "target": "Wolf", "target_data": c.initiative_order[0]})
r1 = eng.process_player_roll(CHAR, {"dice": "2d12", "result": 14, "rolls": [7, 7]})
check("2d12 rejected (count)", r1.get("action") == "invalid_dice" and r1.get("reason") == "count")
r2 = eng.process_player_roll(CHAR, {"dice": "1d12", "result": 9, "rolls": [9]})
check("1d12 resolves", r2.get("action") == "weapon_damage_applied")

# ── S8 — anti-deadlock: end_turn handler clears the actor's abandoned pending ──
print("S8 — end_turn escape (anti-deadlock)")
src = inspect.getsource(SAMOrchestrator.process_message)
check("end_turn handler clears the actor's pending (239: clear_pending(actor_id))",
      "end_turn" in src and "engine.clear_pending(actor_id)" in src)

# ── Extra — advantage attack (two d20s) is NOT rejected on count ──
print("Extra — advantage attack roll accepted")
c = fresh_combat(); eng = MechanicEngine(c)
arm(eng, {"type": "weapon_attack", "weapon": {"name": "Greataxe", "bonus": "+7", "damage": "1d12+4"},
    "target": "Wolf", "target_data": c.initiative_order[0]})
res = eng.process_player_roll(CHAR, {"dice": "1d20", "result": 15, "rolls": [5, 15]})
check("advantage (2 rolls) not rejected", res.get("action") != "invalid_dice")

# ── Change 4 — _display_dice never emits a bare number ──
print("Change 4 — no bare-number prompts")
check("'5' → 1d1+4", orch._display_dice("5") == "1d1+4")
check("'1' → 1d1", orch._display_dice("1") == "1d1")
check("'' → 1d4", orch._display_dice("") == "1d4")
check("'1d12+4' stays", orch._display_dice("1d12+4") == "1d12+4")

# ── S9 — RULE 16 .format() smoke test ──
print("S9 — narrator RULE 16 .format() smoke test")
try:
    Narrator.SYSTEM_PROMPT.format(dm_style="x", campaign_context="x", character_context="x", party_context="x")
    check("SYSTEM_PROMPT.format() no KeyError", True)
except Exception as e:
    check(f"SYSTEM_PROMPT.format() raised: {e}", False)

passed = sum(1 for _, c in results if c)
print(f"\n{passed}/{len(results)} checks passed")
print("ALL PASS ✅" if passed == len(results) else "SOME FAILED ❌")
