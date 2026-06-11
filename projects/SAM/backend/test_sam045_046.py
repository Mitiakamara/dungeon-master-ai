"""SAM-045 (attack-roll count) + SAM-046 (Unarmed = 1d4+STR) + fail-closed
_check_dice. Run: PYTHONUTF8=1 ./venv/Scripts/python.exe test_sam045_046.py"""
from agents.mechanic import MechanicEngine
from agents.combat_state import CombatState
from agents.orchestrator import SAMOrchestrator
from agents.narrator import Narrator

orch = SAMOrchestrator(None, None)
results = []
def check(name, cond):
    results.append((name, cond)); print(f"  {'✅' if cond else '❌ FAIL'} {name}")

def fresh_combat(hp=50):
    return CombatState({"active": True, "current_turn_index": 0, "actions_remaining": 1,
        "initiative_order": [{"name": "Wolf", "is_npc": True, "hp": hp, "hp_max": hp, "ac": 10}]})

# str 18 → +4 mod; Greataxe for the good-path attack
CHAR = {"name": "Björn", "stats": {"str": 18}, "status": {"attacks": [
    {"name": "Unarmed Strike", "bonus": "+7", "damage": "5"},   # fixed-damage from PDF
    {"name": "Greataxe", "bonus": "+7", "damage": "1d12+4"},
]}}

def attack_pending(c, weapon):
    return {"type": "weapon_attack", "weapon": weapon, "target": "Wolf",
            "target_data": c.initiative_order[0], "character_name": "Björn"}

# ── S1 — attack 1d20 → valid, resolves ──
print("S1 — 1d20 attack valid")
c = fresh_combat(); e = MechanicEngine(c); e.pending_player_roll = attack_pending(c, CHAR["status"]["attacks"][1])
r = e.process_player_roll(CHAR, {"dice": "1d20", "result": 15, "rolls": [15]})
check("resolves (not invalid)", r.get("action") == "weapon_attack_result")

# ── S2 — attack 2d20 → valid (advantage/disadvantage) ──
print("S2 — 2d20 attack accepted")
c = fresh_combat(); e = MechanicEngine(c); e.pending_player_roll = attack_pending(c, CHAR["status"]["attacks"][1])
r = e.process_player_roll(CHAR, {"dice": "2d20", "result": 15, "rolls": [5, 15]})
check("2d20 not rejected", r.get("action") != "invalid_dice")

# ── S3 — attack 4d20 → REJECTED ──
print("S3 — 4d20 attack rejected")
c = fresh_combat(); e = MechanicEngine(c); e.pending_player_roll = attack_pending(c, CHAR["status"]["attacks"][1])
r = e.process_player_roll(CHAR, {"dice": "4d20", "result": 40, "rolls": [10, 10, 10, 10]})
check("rejected (attack reason)", r.get("action") == "invalid_dice" and r.get("reason") == "attack")
check("pending preserved", e.pending_player_roll is not None)

# ── S4 — attack 3d20 → REJECTED ──
print("S4 — 3d20 attack rejected")
c = fresh_combat(); e = MechanicEngine(c); e.pending_player_roll = attack_pending(c, CHAR["status"]["attacks"][1])
r = e.process_player_roll(CHAR, {"dice": "3d20", "result": 30, "rolls": [10, 10, 10]})
check("rejected (attack reason)", r.get("action") == "invalid_dice" and r.get("reason") == "attack")

# ── S5 — Unarmed → damage_spec 1d4+4, prompt 1d4+4 (no 1d1/5) ──
print("S5 — Unarmed normalizes to 1d4+STR")
c = fresh_combat(); e = MechanicEngine(c); e.pending_player_roll = attack_pending(c, CHAR["status"]["attacks"][0])
r = e.process_player_roll(CHAR, {"dice": "1d20", "result": 15, "rolls": [15]})  # 15+7=22 hit
check("hit", r.get("hit") is True)
pend = e.pending_player_roll
check("damage_spec == 1d4+4", pend.get("damage_spec") == "1d4+4")
prompt = orch._get_roll_prompt(pend)
check("prompt has 1d4+4, no 1d1, no bare 5", "1d4+4" in prompt and "1d1" not in prompt)

# ── S6 — Unarmed pending 1d4, roll 1d20 → REJECTED (faces) ──
print("S6 — Unarmed 1d4 rejects 1d20")
r = e.process_player_roll(CHAR, {"dice": "1d20", "result": 19, "rolls": [19]})
check("rejected (faces)", r.get("action") == "invalid_dice" and r.get("reason") == "faces")
check("wolf HP unchanged", c.initiative_order[0]["hp"] == 50)
check("pending preserved", e.pending_player_roll is not None)

# ── S7 — Unarmed pending 1d4, roll 1d4 → resolves, damage = roll + STR ──
print("S7 — Unarmed 1d4 resolves with +STR")
r = e.process_player_roll(CHAR, {"dice": "1d4", "result": 3, "rolls": [3]})
check("resolves weapon_damage_applied", r.get("action") == "weapon_damage_applied")
check("total damage = 3 + 4 (STR) = 7", r.get("total_damage") == 7)
check("wolf HP 50 → 43", c.initiative_order[0]["hp"] == 43)

# ── S8 — degenerate damage_spec → fail-closed reject ──
print("S8 — fail-closed on bad damage_spec")
c = fresh_combat(); e = MechanicEngine(c)
e.pending_player_roll = {"type": "weapon_damage", "weapon": {"name": "X", "damage": "1d1+4"},
    "damage_spec": "1d1+4", "target": "Wolf", "target_data": c.initiative_order[0], "character_name": "Björn"}
r = e.process_player_roll(CHAR, {"dice": "1d4", "result": 3, "rolls": [3]})
check("rejected (unparseable, fail-closed)", r.get("action") == "invalid_dice" and r.get("reason") == "unparseable")
check("HP unchanged", c.initiative_order[0]["hp"] == 50)
# also garbage spec
e.pending_player_roll = {"type": "weapon_damage", "weapon": {"name": "X", "damage": "xyz"},
    "damage_spec": "xyz", "target": "Wolf", "target_data": c.initiative_order[0]}
r = e.process_player_roll(CHAR, {"dice": "1d6", "result": 4, "rolls": [4]})
check("garbage spec rejected too", r.get("action") == "invalid_dice" and r.get("reason") == "unparseable")

# ── Regression — Greataxe normal damage still resolves (no breakage) ──
print("Regression — Greataxe damage path intact")
c = fresh_combat(); e = MechanicEngine(c)
e.pending_player_roll = {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "1d12+4", "target": "Wolf", "target_data": c.initiative_order[0], "character_name": "Björn"}
r = e.process_player_roll(CHAR, {"dice": "1d12", "result": 10, "rolls": [10]})
check("Greataxe resolves, dmg 14", r.get("action") == "weapon_damage_applied" and r.get("total_damage") == 14)

# ── S9 — RULE 16 .format() smoke test ──
print("S9 — narrator RULE 16 .format() smoke test")
try:
    Narrator.SYSTEM_PROMPT.format(dm_style="x", campaign_context="x", character_context="x", party_context="x")
    check("SYSTEM_PROMPT.format() OK", True)
except Exception as ex:
    check(f"format raised: {ex}", False)

passed = sum(1 for _, c in results if c)
print(f"\n{passed}/{len(results)} checks passed")
print("ALL PASS ✅" if passed == len(results) else "SOME FAILED ❌")
