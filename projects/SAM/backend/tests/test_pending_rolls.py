"""
Instrucción 239 — pending rolls por personaje.

Principio: cada personaje tiene su propio slot; un dado se enruta por el
character_id del que lo tira, nunca por nombre; un dado sin pending propio es
ORPHAN ROLL.

D1 a-g sobre MechanicEngine / _rehydrate_pending sin DB, más cobertura del
turn guard completo (C2/C3), la serialización (B6), el PROMPT PLAYER con
nombre y el contexto PENDING ROLLS (B8), y el GM sin ficha (B9).
"""
import json

from langchain_core.messages import HumanMessage  # stub from conftest

from agents.mechanic import MechanicEngine
from agents.combat_state import CombatState
from agents.orchestrator import SAMOrchestrator


# ── fixtures ────────────────────────────────────────────────────────────────

BJORN = {
    "id": "char-bjorn", "name": "Björn Glacierfist", "class": "Barbarian 7", "level": 7,
    "stats": {"str": 18, "dex": 14, "con": 16, "wis": 16},
    "status": {"hp_current": 60, "hp_max": 68, "ac": 14, "proficiency_bonus": 3,
               "skill_proficiencies": {"perception": "proficient"},
               "attacks": [{"name": "Greatsword", "bonus": "+7", "damage": "2d6+4"}]},
}
FEKAS = {
    "id": "char-fekas", "name": "Fekas Was", "class": "Rogue 7", "level": 7,
    "stats": {"str": 10, "dex": 20, "wis": 12},
    "status": {"hp_current": 45, "hp_max": 45, "ac": 15, "proficiency_bonus": 3,
               "skill_proficiencies": {"athletics": "none"},
               "attacks": [{"name": "Rapier", "bonus": "+8", "damage": "1d8+5"}]},
}
VEX = {"id": "char-vex", "name": "Vex", "class": "Wizard 5", "level": 5,
       "stats": {"int": 18}, "status": {"hp_current": 30, "hp_max": 30, "ac": 12}}
GM_NO_SHEET = {}  # GM without a character in the campaign (server.py A4 → empty ctx)
PARTY = [BJORN, FEKAS, VEX]


def d20(n):
    return {"dice": "1d20", "result": n, "rolls": [n]}


def sysev(name, dice, result, rolls):
    return f"[SYSTEM EVENT] {name} rolled {dice}. Result: {result} (Rolls: {', '.join(str(r) for r in rolls)})."


class FakeLLM:
    """Canned reply + captured calls (no network)."""

    def __init__(self, reply="narrado"):
        self.reply, self.calls = reply, []

    def invoke(self, messages):
        self.calls.append(messages)
        class R:  # noqa: N801
            content = self.reply
        return R()

    @property
    def last_system(self):
        return self.calls[-1][0].content if self.calls else ""

    @property
    def last_user(self):
        for m in reversed(self.calls[-1]):
            if isinstance(m, HumanMessage):
                return m.content
        return ""

    @property
    def campaign_ctx(self):
        """The CAMPAIGN CONTEXT section of the system prompt (rule 19 itself
        also says "PENDING ROLLS:", so assertions must look here, not at the whole prompt)."""
        return self.last_system.split("CAMPAIGN CONTEXT:", 1)[-1]


def orch(intent=None, narr="narrado"):
    i = FakeLLM(json.dumps(intent) if intent else '{"type": "roleplay"}')
    n = FakeLLM(narr)
    return SAMOrchestrator(i, n, knowledge_service=None), i, n


def slots(result):
    return (result["combat_state"] or {}).get("pending_rolls") or {}


def wolf_combat(current_index=0):
    """Björn (index 0) and Fekas (1) vs a Wolf (2); it's initiative_order[current_index]'s turn."""
    return {
        "active": True, "round": 1, "current_turn_index": current_index, "actions_remaining": 1,
        "initiative_order": [
            {"name": "Björn Glacierfist", "is_npc": False, "hp": 60, "hp_max": 68, "ac": 14,
             "class": "Barbarian 7", "level": 7},
            {"name": "Fekas Was", "is_npc": False, "hp": 45, "hp_max": 45, "ac": 15,
             "class": "Rogue 7", "level": 7},
            {"name": "Wolf", "is_npc": True, "hp": 50, "hp_max": 50, "ac": 10},
        ],
    }


# ── D1 (a) two characters declare → both pendings coexist ───────────────────

def test_a_two_skill_checks_coexist():
    e = MechanicEngine(CombatState())
    e.process_skill_check(BJORN, "Perception", 12)
    e.process_skill_check(FEKAS, "Athletics", 10)
    assert set(e.pending_rolls) == {"char-bjorn", "char-fekas"}
    assert e.get_pending("char-bjorn")["skill"] == "Perception"
    assert e.get_pending("char-fekas")["skill"] == "Athletics"
    # set_pending stamps owner id + name on every slot
    assert e.get_pending("char-bjorn")["character_id"] == "char-bjorn"
    assert e.get_pending("char-bjorn")["character_name"] == "Björn Glacierfist"
    assert e.get_pending("char-fekas")["character_name"] == "Fekas Was"
    assert len(e.all_pending()) == 2


# ── D1 (b) each rolls their own → own resolves, the other stays ─────────────

def test_b_each_resolves_own_pending_only():
    e = MechanicEngine(CombatState())
    e.process_skill_check(BJORN, "Perception", 12)
    e.process_skill_check(FEKAS, "Athletics", 10)

    r = e.process_player_roll(BJORN, d20(10))
    assert r["action"] == "skill_check_result"
    assert r["character"] == "Björn Glacierfist"
    assert r["total"] == 16  # 10 + WIS 3 + prof 3 — Björn's modifiers, not Fekas's
    assert e.get_pending("char-bjorn") is None
    assert e.get_pending("char-fekas") is not None, "Fekas's pending must survive Björn's roll"

    r2 = e.process_player_roll(FEKAS, d20(8))
    assert r2["action"] == "skill_check_result"
    assert r2["character"] == "Fekas Was"
    assert e.all_pending() == []


def test_b_die_from_other_player_never_resolves_a_pending():
    """The SAM-049 scenario, now by routing: Björn's slot, Fekas's die → Fekas is an orphan."""
    e = MechanicEngine(CombatState())
    e.process_skill_check(BJORN, "Perception", 12)
    r = e.process_player_roll(FEKAS, d20(18))
    assert r["action"] == "freeform_roll"
    assert "ORPHAN ROLL: Fekas Was rolled 1d20 = 18" in e.get_results_summary()
    assert e.get_pending("char-bjorn") is not None, "Björn's slot untouched"
    assert e.state_updates == []


# ── D1 (c) third character rolls with no pending → ORPHAN ROLL fact ─────────

def test_c_third_character_orphan_roll():
    e = MechanicEngine(CombatState())
    e.process_skill_check(BJORN, "Perception", 12)
    e.process_skill_check(FEKAS, "Athletics", 10)
    r = e.process_player_roll(VEX, d20(17))
    assert r["action"] == "freeform_roll"
    assert any(x.get("action") == "orphan_roll" for x in e.results)
    assert "ORPHAN ROLL: Vex rolled 1d20 = 17" in e.get_results_summary()
    assert len(e.all_pending()) == 2, "orphans never touch other slots"


# ── D1 (d) re-declaring replaces own slot, never someone else's ─────────────

def test_d_redeclare_replaces_own_slot_only():
    e = MechanicEngine(CombatState())
    e.process_skill_check(BJORN, "Perception", 12)
    e.process_skill_check(FEKAS, "Athletics", 10)
    e.process_skill_check(BJORN, "Stealth", 14)
    assert e.get_pending("char-bjorn")["skill"] == "Stealth"
    assert e.get_pending("char-fekas")["skill"] == "Athletics"
    assert len(e.all_pending()) == 2


# ── D1 (e) rehydration — legacy single slot WITH character_id → migrates ────

def test_e_rehydrate_legacy_with_id():
    o, _, _ = orch()
    legacy = {"active": False, "pending_player_roll": {
        "type": "skill_check", "skill": "Perception", "dc": 12,
        "character_id": "char-bjorn", "character_name": "Björn Glacierfist"}}
    s = o._rehydrate_pending(legacy, PARTY)
    assert list(s) == ["char-bjorn"]
    assert s["char-bjorn"]["type"] == "skill_check"
    assert s["char-bjorn"]["character_id"] == "char-bjorn"


# ── D1 (f) legacy WITHOUT id: resolvable name → migrates; else → discarded ─

def test_f_rehydrate_legacy_without_id_resolves_by_name(capsys):
    o, _, _ = orch()
    legacy = {"active": False, "pending_player_roll": {
        "type": "weapon_attack", "weapon": {"name": "Rapier"}, "character_name": "  fekas was "}}
    s = o._rehydrate_pending(legacy, PARTY)
    assert list(s) == ["char-fekas"]
    assert s["char-fekas"]["character_id"] == "char-fekas"
    assert "migrated to slot char-fekas" in capsys.readouterr().out


def test_f_rehydrate_legacy_without_id_unresolvable_is_discarded(capsys):
    o, _, _ = orch()
    legacy = {"active": False, "pending_player_roll": {
        "type": "skill_check", "skill": "Perception", "character_name": "Nadie"}}
    assert o._rehydrate_pending(legacy, PARTY) == {}
    out = capsys.readouterr().out
    assert "no resolvable character_id" in out and "DISCARDED" in out


def test_f_rehydrate_legacy_partial_name_is_not_a_match():
    """No fuzzy matching: 'Björn' alone must not route to 'Björn Glacierfist'."""
    o, _, _ = orch()
    legacy = {"pending_player_roll": {"type": "skill_check", "character_name": "Björn"}}
    assert o._rehydrate_pending(legacy, PARTY) == {}


# ── D1 (g) rehydration None → {} ; new form loads as is ─────────────────────

def test_g_rehydrate_none_and_new_form():
    o, _, _ = orch()
    assert o._rehydrate_pending(None, PARTY) == {}
    assert o._rehydrate_pending({}, PARTY) == {}
    assert o._rehydrate_pending({"active": False}, PARTY) == {}
    new = {"pending_rolls": {
        "char-bjorn": {"type": "skill_check", "skill": "Perception", "character_name": "Björn Glacierfist"},
        "char-fekas": {"type": "weapon_attack", "character_name": "Fekas Was"},
        "junk": "not a dict",
    }}
    s = o._rehydrate_pending(new, PARTY)
    assert set(s) == {"char-bjorn", "char-fekas"}
    assert s["char-bjorn"]["character_id"] == "char-bjorn"


# ── B1: set_pending refuses without an id (B9 GM without sheet) ─────────────

def test_set_pending_refuses_without_id(capsys):
    e = MechanicEngine(CombatState())
    assert e.set_pending(None, "GM", {"type": "skill_check"}) is False
    assert e.set_pending("", "GM", {"type": "skill_check"}) is False
    assert e.pending_rolls == {}
    assert "set_pending refused" in capsys.readouterr().out
    # A declaration by an id-less actor renders an honest fact, not a dice prompt
    e.process_skill_check(GM_NO_SHEET, "Perception", 10)
    summary = e.get_results_summary()
    assert "NO CHARACTER SHEET" in summary and "Do NOT ask for dice" in summary
    assert e.pending_rolls == {}
    assert e.results[-1]["needs_player_roll"] is False


def test_set_pending_never_touches_other_slots_and_stamps_owner():
    e = MechanicEngine(CombatState())
    e.set_pending("char-fekas", "Fekas Was", {"type": "skill_check", "skill": "Stealth"})
    ok = e.set_pending("char-bjorn", "Björn Glacierfist", {"type": "skill_check", "skill": "Perception",
                                                           "character_id": "WRONG", "character_name": "WRONG"})
    assert ok is True
    assert e.get_pending("char-bjorn")["character_id"] == "char-bjorn"
    assert e.get_pending("char-bjorn")["character_name"] == "Björn Glacierfist"
    assert e.get_pending("char-fekas")["skill"] == "Stealth"
    e.clear_pending("char-bjorn")
    assert e.get_pending("char-bjorn") is None and e.get_pending("char-fekas") is not None


# ── B3: process_attack stamps the owner itself (no caller setdefault) ───────

def test_process_attack_stamps_owner_and_sneak():
    c = CombatState(wolf_combat())
    e = MechanicEngine(c)
    e.process_attack(FEKAS, FEKAS["status"]["attacks"][0], c.initiative_order[2], sneak_dice="4d6")
    p = e.get_pending("char-fekas")
    assert p["type"] == "weapon_attack"
    assert p["character_name"] == "Fekas Was" and p["character_id"] == "char-fekas"
    assert p["sneak_dice"] == "4d6"
    # chained damage pending stays on the same character
    r = e.process_player_roll(FEKAS, d20(15))
    assert r["hit"] is True
    assert e.get_pending("char-fekas")["type"] == "weapon_damage"
    assert e.get_pending("char-fekas")["sneak_dice"] == "4d6"


# ── SAM-039/042 regression under the new API: invalid dice keep the slot ────

def test_invalid_dice_preserves_own_slot():
    c = CombatState(wolf_combat())
    e = MechanicEngine(c)
    e.set_pending("char-bjorn", "Björn Glacierfist", {
        "type": "weapon_damage", "weapon": {"name": "Greatsword", "damage": "2d6+4"},
        "damage_spec": "2d6+4", "target": "Wolf", "target_data": c.initiative_order[2]})
    r = e.process_player_roll(BJORN, d20(5))
    assert r["action"] == "invalid_dice"
    assert e.get_pending("char-bjorn") is not None
    r2 = e.process_player_roll(BJORN, {"dice": "2d6", "result": 7, "rolls": [3, 4]})
    assert r2["action"] == "weapon_damage_applied" and r2["total_damage"] == 11
    assert e.get_pending("char-bjorn") is None


# ── B6/B8 end-to-end: serialization, named PROMPT PLAYER, PENDING ROLLS ─────

def test_end_to_end_two_players_out_of_combat():
    # Björn declares Perception
    o, _, n = orch({"type": "skill_check", "skill": "Perception"})
    r1 = o.process_message(message="busco trampas", sender_name="Björn Glacierfist",
                           character_context=BJORN, party_characters=PARTY, combat_data=None)
    assert list(slots(r1)) == ["char-bjorn"]
    assert "pending_player_roll" not in r1["combat_state"], "legacy key never written again"
    assert "→ PROMPT PLAYER (Björn Glacierfist): Tira 1d20 para Perception." in n.last_user
    assert "PENDING ROLLS:" not in n.campaign_ctx, "a slot armed this request is not 'outstanding'"

    # Fekas declares Athletics before Björn rolls → both coexist in the persisted dict
    o2, _, n2 = orch({"type": "skill_check", "skill": "Athletics"})
    r2 = o2.process_message(message="trepo el muro", sender_name="Fekas Was",
                            character_context=FEKAS, party_characters=PARTY,
                            combat_data=r1["combat_state"])
    assert set(slots(r2)) == {"char-bjorn", "char-fekas"}
    assert "PROMPT PLAYER (Fekas Was)" in n2.last_user
    assert "PENDING ROLLS: Björn Glacierfist (1d20 Perception)" in n2.campaign_ctx

    # Björn rolls → his check resolves with HIS modifiers; Fekas's slot survives
    o3, _, n3 = orch()
    r3 = o3.process_message(message=sysev("Björn Glacierfist", "1d20", 10, [10]),
                            sender_name="Björn Glacierfist", character_context=BJORN,
                            party_characters=PARTY, combat_data=r2["combat_state"])
    assert "rolled 10 + 6 = 16" in n3.last_user
    assert list(slots(r3)) == ["char-fekas"]
    assert "PENDING ROLLS: Fekas Was (1d20 Athletics)" in n3.campaign_ctx

    # Vex (no slot) rolls → orphan; nothing else changes
    o4, _, n4 = orch()
    r4 = o4.process_message(message=sysev("Vex", "1d20", 3, [3]), sender_name="Vex",
                            character_context=VEX, party_characters=PARTY,
                            combat_data=r3["combat_state"])
    assert "ORPHAN ROLL: Vex rolled 1d20 = 3" in n4.last_user
    assert list(slots(r4)) == ["char-fekas"]


def test_roleplay_with_own_stale_pending_is_not_reprompted():
    """A slot left from an earlier request is context (PENDING ROLLS), not a synthesized re-prompt."""
    o, _, n = orch({"type": "roleplay", "description": "miro alrededor"})
    stale = {"active": False, "pending_rolls": {"char-bjorn": {
        "type": "skill_check", "skill": "Perception", "character_name": "Björn Glacierfist"}}}
    r = o.process_message(message="miro alrededor", sender_name="Björn Glacierfist",
                          character_context=BJORN, party_characters=PARTY, combat_data=stale)
    assert "MECHANICAL FACTS" not in n.last_user, "must go to the roleplay template"
    assert "PENDING ROLLS: Björn Glacierfist (1d20 Perception)" in n.campaign_ctx
    assert list(slots(r)) == ["char-bjorn"], "roleplay never clears a slot"


# ── C2/C3: turn guard covers skill_check / self_damage / item / freeform ────

def test_turn_guard_blocks_skill_check_out_of_turn_without_pending():
    o, _, n = orch({"type": "skill_check", "skill": "Intimidation"})
    r = o.process_message(message="intento intimidarlo", sender_name="Fekas Was",
                          character_context=FEKAS, party_characters=PARTY,
                          combat_data=wolf_combat(current_index=0))  # Björn's turn
    assert "OUT_OF_TURN: It's Björn Glacierfist's turn, not Fekas Was's" in n.last_user
    assert slots(r) == {}, "a blocked intent never reaches set_pending"
    assert r["prompt_player_roll"] is None


def test_turn_guard_blocks_self_damage_and_item_out_of_turn():
    for intent in ({"type": "self_damage", "description": "me corto", "damage_dice": "1d4"},
                   {"type": "item", "item": "Potion of Healing", "target": "self",
                    "is_healing": True, "healing_dice": "2d4+2"}):
        o, _, n = orch(intent)
        r = o.process_message(message="x", sender_name="Fekas Was", character_context=FEKAS,
                              party_characters=PARTY, combat_data=wolf_combat(current_index=0))
        assert "OUT_OF_TURN" in n.last_user, intent["type"]
        assert slots(r) == {}, intent["type"]
        assert r["state_updates"] == [], "no inventory_remove either"


def test_turn_guard_freeform_die_out_of_turn_is_blocked_before_arming():
    o, _, n = orch()
    r = o.process_message(message=sysev("Fekas Was", "1d20", 19, [19]), sender_name="Fekas Was",
                          character_context=FEKAS, party_characters=PARTY,
                          combat_data=wolf_combat(current_index=0))
    assert "OUT_OF_TURN" in n.last_user
    assert slots(r) == {}, "freeform pending must not be armed for an out-of-turn roller"
    wolf = next(c for c in r["combat_state"]["initiative_order"] if c["name"] == "Wolf")
    assert wolf["hp"] == 50


def test_turn_guard_allows_out_of_turn_die_with_own_pending():
    """Fekas declared Perception before combat; she may still roll it on Björn's turn."""
    combat = wolf_combat(current_index=0)
    combat["pending_rolls"] = {"char-fekas": {"type": "skill_check", "skill": "Perception",
                                              "character_name": "Fekas Was", "consumes_action": False}}
    o, _, n = orch()
    r = o.process_message(message=sysev("Fekas Was", "1d20", 12, [12]), sender_name="Fekas Was",
                          character_context=FEKAS, party_characters=PARTY, combat_data=combat)
    assert "OUT_OF_TURN" not in n.last_user
    assert "Fekas Was Perception" in n.last_user
    assert slots(r) == {}
    assert r["combat_state"]["current_turn"] == "Björn Glacierfist", "reactive roll never advances the turn"


def test_in_turn_freeform_die_arms_and_resolves_for_actor_only():
    combat = wolf_combat(current_index=0)
    combat["pending_rolls"] = {"char-fekas": {"type": "skill_check", "skill": "Perception",
                                              "character_name": "Fekas Was"}}
    o, _, n = orch()
    r = o.process_message(message=sysev("Björn Glacierfist", "1d20", 18, [18]),
                          sender_name="Björn Glacierfist", character_context=BJORN,
                          party_characters=PARTY, combat_data=combat)
    assert "HIT!" in n.last_user
    assert slots(r)["char-bjorn"]["type"] == "weapon_damage"
    assert slots(r)["char-fekas"]["type"] == "skill_check", "Fekas's slot untouched by Björn's attack"
    assert "PROMPT PLAYER (Björn Glacierfist)" in n.last_user


def test_end_turn_clears_only_the_actors_slot():
    combat = wolf_combat(current_index=0)
    combat["pending_rolls"] = {
        "char-bjorn": {"type": "weapon_attack", "weapon": {"name": "Greatsword"}, "character_name": "Björn Glacierfist"},
        "char-fekas": {"type": "skill_check", "skill": "Perception", "character_name": "Fekas Was"},
    }
    o, _, _ = orch({"type": "end_turn"})
    r = o.process_message(message="paso", sender_name="Björn Glacierfist", character_context=BJORN,
                          party_characters=PARTY, combat_data=combat)
    assert "char-bjorn" not in slots(r)
    assert slots(r)["char-fekas"]["type"] == "skill_check"


def test_other_players_stale_slot_does_not_freeze_the_turn():
    """Björn's attack chain completes → turn advances even though Fekas still owes a die."""
    combat = wolf_combat(current_index=0)
    combat["pending_rolls"] = {
        "char-bjorn": {"type": "weapon_damage", "weapon": {"name": "Greatsword", "damage": "2d6+4"},
                       "damage_spec": "2d6+4", "target": "Wolf", "target_data": combat["initiative_order"][2],
                       "character_name": "Björn Glacierfist"},
        "char-fekas": {"type": "skill_check", "skill": "Perception", "character_name": "Fekas Was"},
    }
    o, _, n = orch()
    r = o.process_message(message=sysev("Björn Glacierfist", "2d6", 7, [3, 4]),
                          sender_name="Björn Glacierfist", character_context=BJORN,
                          party_characters=PARTY, combat_data=combat)
    assert "deals 11 damage" in n.last_user
    assert r["combat_state"]["current_turn"] == "Fekas Was", "turn advanced past Björn"
    assert list(slots(r)) == ["char-fekas"]


# ── B9: GM without a sheet never arms anything, dies are orphans ────────────

def test_gm_without_sheet_declaration_and_die():
    o, _, n = orch({"type": "skill_check", "skill": "Perception"})
    r = o.process_message(message="hago percepción", sender_name="Player", character_context=GM_NO_SHEET,
                          party_characters=PARTY, combat_data=None)
    assert slots(r) == {}
    assert "NO CHARACTER SHEET" in n.last_user
    assert r["prompt_player_roll"] is None
    o2, _, n2 = orch()
    r2 = o2.process_message(message=sysev("Player", "1d20", 9, [9]), sender_name="Player",
                            character_context=GM_NO_SHEET, party_characters=PARTY, combat_data=None)
    assert "ORPHAN ROLL" in n2.last_user and slots(r2) == {}
