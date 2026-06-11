"""SAM-049 — pending_player_roll ownership (cross-player consumption guard).
Run: PYTHONUTF8=1 ./venv/Scripts/python.exe test_sam049.py"""
from agents.mechanic import MechanicEngine
from agents.combat_state import CombatState

results = []
def check(name, cond):
    results.append((name, cond)); print(f"  {'✅' if cond else '❌ FAIL'} {name}")

BJORN = {"name": "Björn Glacierfist", "stats": {"str": 18}, "status": {}}
FEKAS = {"name": "Fekas Was", "stats": {"dex": 16}, "status": {"skill_proficiencies": {}}}

def wolf_combat(hp=50):
    return CombatState({"active": True, "current_turn_index": 0, "actions_remaining": 1,
        "initiative_order": [{"name": "Wolf", "is_npc": True, "hp": hp, "hp_max": hp, "ac": 10}]})

# ── S1 — combat damage pending owned by Björn, Fekas rolls → freeform, intact ──
print("S1 — Fekas can't consume Björn's combat damage pending")
c = wolf_combat(); e = MechanicEngine(c)
e.pending_player_roll = {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "1d12+4", "target": "Wolf", "target_data": c.initiative_order[0],
    "character_name": "Björn Glacierfist"}
r = e.process_player_roll(FEKAS, {"dice": "1d12", "result": 10, "rolls": [10]})
check("Fekas roll → freeform_roll", r.get("action") == "freeform_roll")
check("wolf HP unchanged (50)", c.initiative_order[0]["hp"] == 50)
check("Björn's pending preserved", e.pending_player_roll is not None)

# ── S2 — same pending, Björn rolls → resolves ──
print("S2 — Björn resolves his own pending")
r = e.process_player_roll(BJORN, {"dice": "1d12", "result": 10, "rolls": [10]})
check("Björn roll resolves", r.get("action") == "weapon_damage_applied")
check("wolf HP 50 → 36", c.initiative_order[0]["hp"] == 36)

# ── S3 — OUT OF COMBAT: skill_check pending owned by Björn, Fekas rolls ──
print("S3 — out of combat, Fekas can't consume Björn's skill check")
e = MechanicEngine(CombatState())  # no active combat
e.pending_player_roll = {"type": "skill_check", "skill": "Perception", "dc": 12,
    "character_name": "Björn Glacierfist"}
r = e.process_player_roll(FEKAS, {"dice": "1d20", "result": 18, "rolls": [18]})
check("Fekas roll → freeform (no skill resolved)", r.get("action") == "freeform_roll")
check("Björn's skill pending preserved", e.pending_player_roll is not None)
# Björn then resolves it
r = e.process_player_roll(BJORN, {"dice": "1d20", "result": 18, "rolls": [18]})
check("Björn resolves the skill check", r.get("action") == "skill_check_result")

# ── S4 — case/space-insensitive owner match ──
print("S4 — owner match is normalized (case/space)")
e = MechanicEngine(CombatState())
e.pending_player_roll = {"type": "skill_check", "skill": "Stealth", "dc": 10,
    "character_name": "  björn glacierfist  "}
r = e.process_player_roll(BJORN, {"dice": "1d20", "result": 15, "rolls": [15]})
check("normalized name matches → resolves", r.get("action") == "skill_check_result")

# ── S5 — pending WITHOUT owner stays lenient (backward compat) ──
print("S5 — ownerless pending resolves for anyone (lenient)")
c = wolf_combat(); e = MechanicEngine(c)
e.pending_player_roll = {"type": "weapon_damage", "weapon": {"name": "Greataxe", "damage": "1d12+4"},
    "damage_spec": "1d12+4", "target": "Wolf", "target_data": c.initiative_order[0]}  # no character_name
r = e.process_player_roll(FEKAS, {"dice": "1d12", "result": 8, "rolls": [8]})
check("ownerless pending still resolves", r.get("action") == "weapon_damage_applied")

# ── S6 — spell pendings now carry an owner (process_spell) ──
print("S6 — spell pendings stamp character_name")
e = MechanicEngine(wolf_combat())
spell = {"name": "Sacred Flame", "save_atk": "DEX 13", "level": "Cantrip"}
target = {"name": "Wolf", "is_npc": True, "hp": 50, "hp_max": 50, "ac": 10, "saves": {"dex": 0}}
# force a failed save by rolling many times is non-deterministic; just check the
# pending owner field when a pending is produced.
import agents.mechanic as M
for _ in range(40):
    e2 = MechanicEngine(wolf_combat())
    e2.process_spell(BJORN, spell, dict(target))
    if e2.pending_player_roll and e2.pending_player_roll.get("type") == "spell_damage":
        break
ok = (e2.pending_player_roll is None) or (e2.pending_player_roll.get("character_name") == "Björn Glacierfist")
check("spell_damage pending owner = caster (or NPC saved)", ok)

passed = sum(1 for _, c in results if c)
print(f"\n{passed}/{len(results)} checks passed")
print("ALL PASS ✅" if passed == len(results) else "SOME FAILED ❌")
