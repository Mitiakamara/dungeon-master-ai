"""SAM-053 / SAM-054 / SAM-059 — Python recupera el control de los números.

Cubre:
  SAM-054  la regla 15 ya no licencia aritmética al LLM
  SAM-053  (a) el narrator no pide tiradas por su cuenta
           (b) el interpreter reconoce skill checks fuera de combate
           (c) el dado huérfano produce un fact ORPHAN ROLL (no roleplay)
  SAM-059  ventaja/desventaja toma el dado correcto, nunca rolls[0] en silencio

Run: PYTHONUTF8=1 python3.14 test_sam053_054_059.py
(el venv del repo apunta a una ruta muerta; langchain_core se stubbea abajo)
"""
import sys
import types

# ── stub langchain_core.messages ────────────────────────────────────────────
# narrator/interpreter importan estos símbolos DENTRO de sus métodos, así que
# basta con inyectar el módulo antes de la primera llamada.
_lc = types.ModuleType("langchain_core")
_msgs = types.ModuleType("langchain_core.messages")


class _Msg:
    def __init__(self, content=""):
        self.content = content

    def __repr__(self):
        return f"{type(self).__name__}({self.content[:50]!r})"


class SystemMessage(_Msg):
    pass


class HumanMessage(_Msg):
    pass


class AIMessage(_Msg):
    pass


_msgs.SystemMessage, _msgs.HumanMessage, _msgs.AIMessage = SystemMessage, HumanMessage, AIMessage
_lc.messages = _msgs
sys.modules.setdefault("langchain_core", _lc)
sys.modules.setdefault("langchain_core.messages", _msgs)

from agents.mechanic import MechanicEngine  # noqa: E402
from agents.combat_state import CombatState  # noqa: E402
from agents.narrator import Narrator  # noqa: E402
from agents.interpreter import IntentInterpreter  # noqa: E402
from agents.orchestrator import SAMOrchestrator  # noqa: E402

results = []


def check(name, cond):
    results.append((name, cond))
    print(f"  {'✅' if cond else '❌ FAIL'} {name}")


class FakeLLM:
    """Devuelve una respuesta canned y guarda los mensajes recibidos."""

    def __init__(self, reply="ok"):
        self.reply = reply
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        text = self.reply(messages) if callable(self.reply) else self.reply
        return _Msg(text)

    @property
    def last_user(self):
        """Contenido del último HumanMessage enviado (el template)."""
        for m in reversed(self.calls[-1]):
            if isinstance(m, HumanMessage):
                return m.content
        return ""

    @property
    def last_system(self):
        return self.calls[-1][0].content if self.calls else ""


BJORN = {
    "id": "char-bjorn",
    "name": "Björn Glacierfist",
    "class": "Barbarian 7",
    "level": 7,
    "stats": {"str": 18, "dex": 14, "con": 16, "wis": 16, "int": 10, "cha": 8},
    "status": {
        "hp_current": 60, "hp_max": 68, "ac": 14,
        "proficiency_bonus": 3,
        "skill_proficiencies": {"perception": "proficient", "stealth": "none",
                                "athletics": "proficient"},
        "attacks": [
            {"name": "Unarmed Strike", "bonus": "+7", "damage": "5"},
            {"name": "Greatsword", "bonus": "+7", "damage": "2d6+4"},
        ],
    },
}

VEX = {
    "id": "char-vex",
    "name": "Vex Was",
    "class": "Rogue 7",
    "level": 7,
    "stats": {"dex": 20, "int": 14, "wis": 12},
    "status": {
        "hp_current": 45, "hp_max": 45, "ac": 15,
        "proficiency_bonus": 3,
        "skill_proficiencies": {"stealth": "expertise", "history": "proficient"},
        "attacks": [{"name": "Rapier", "bonus": "+8", "damage": "1d8+5"}],
    },
}


def orch(intent_json, narr_reply="narrado"):
    """Orchestrator con LLMs falsos. Devuelve (orchestrator, interp_llm, narr_llm)."""
    i, n = FakeLLM(intent_json), FakeLLM(narr_reply)
    return SAMOrchestrator(i, n, knowledge_service=None), i, n


def sysev(name, dice, result, rolls):
    return f"[SYSTEM EVENT] {name} rolled {dice}. Result: {result} (Rolls: {', '.join(str(r) for r in rolls)})."


def pend_of(result, char_id="char-bjorn"):
    """Instrucción 239: el pending persiste en combat_state.pending_rolls[character_id]."""
    return ((result["combat_state"] or {}).get("pending_rolls") or {}).get(char_id)


def arm(e, pending, char_id="char-bjorn", name="Björn Glacierfist"):
    e.set_pending(char_id, name, pending)


# ═══════════════════════════════════════════════════════════════════════════
print("\nT1 — skill check fuera de combate: Python calcula el total")
# WIS 16 → +3; proficiency_bonus 3; perception proficient → modificador +6
o, illm, nllm = orch('{"type": "skill_check", "skill": "Perception"}')
r1 = o.process_message(
    message="hago una tirada de percepción",
    sender_name="Björn Glacierfist",
    character_context=BJORN,
    party_characters=[BJORN],
    combat_data=None,
)
pend = pend_of(r1)
check("declaración arma pending skill_check", bool(pend) and pend["type"] == "skill_check")
check("pending estampa character_name", (pend or {}).get("character_name") == "Björn Glacierfist")
check("pending estampa character_id", (pend or {}).get("character_id") == "char-bjorn")
check("prompt de tirada emitido", "1d20" in (r1["prompt_player_roll"] or ""))

r2 = o.process_message(
    message=sysev("Björn Glacierfist", "1d20", 10, [10]),
    sender_name="Björn Glacierfist",
    character_context=BJORN,
    party_characters=[BJORN],
    combat_data=r1["combat_state"],
)
facts = nllm.last_user
check("el narrator recibió MECHANICAL FACTS (no roleplay)", "MECHANICAL FACTS" in facts)
check("Python calculó el total: rolled 10 + 6 = 16", "rolled 10 + 6 = 16" in facts)
check("el fact marca la proficiencia", "(Proficient)" in facts)
check("pending consumido", not pend_of(r2))

# ═══════════════════════════════════════════════════════════════════════════
print("\nT2 — nombres de habilidad en español")
e = MechanicEngine(CombatState())
mod_es, _, _, prof_es, ab_es = e._calculate_skill_modifier(VEX, "Sigilo")
mod_en, _, _, prof_en, ab_en = e._calculate_skill_modifier(VEX, "Stealth")
check("'Sigilo' == 'Stealth' (modificador)", mod_es == mod_en == 11)  # DEX +5 + expertise 6
check("'Sigilo' conserva la expertise", prof_es == "expertise" == prof_en)
check("'Sigilo' usa DEX, no el default WIS", ab_es == ab_en == "dex")
check("'Percepción' con acento → perception",
      e._calculate_skill_modifier(BJORN, "Percepción")[0] == 6)
check("'Historia' → history (proficient)",
      e._calculate_skill_modifier(VEX, "Historia")[3] == "proficient")
check("'Wisdom (Perception)' sigue funcionando",
      e._calculate_skill_modifier(BJORN, "Wisdom (Perception)")[0] == 6)
check("'prueba de sigilo' (frase) → stealth",
      e._calculate_skill_modifier(VEX, "prueba de sigilo")[4] == "dex")
# el prompt del interpreter debe enseñarle la traducción
ip = IntentInterpreter.SYSTEM_PROMPT
check("prompt interpreter: mapeo sigilo→Stealth", "sigilo → Stealth" in ip)
check("prompt interpreter: 'quiero lanzar historia'", "quiero lanzar historia" in ip)
check("prompt interpreter: 'podemos lanzar sigilo'", "podemos lanzar sigilo" in ip)
check("prompt interpreter: 'investigar la sala'", "investigar la sala" in ip)
check("prompt interpreter: 'lanzar' no es hechizo", "lanzar sigilo" in ip and "NOT to cast a spell" in ip)
check("prompt interpreter: skill_check gana a roleplay",
      'ALWAYS use "skill_check"' in ip)

# ═══════════════════════════════════════════════════════════════════════════
print("\nT3 — dado huérfano: fact ORPHAN ROLL, sin total inventado")
o, illm, nllm = orch('{"type": "roleplay"}')
r = o.process_message(
    message=sysev("Björn Glacierfist", "1d20", 17, [17]),
    sender_name="Björn Glacierfist",
    character_context=BJORN,
    party_characters=[BJORN],
    combat_data=None,
)
facts = nllm.last_user
check("va a narrate_mechanics, NO a roleplay", "MECHANICAL FACTS" in facts)
check("no usó el template de roleplay", "NO COMBAT MECHANICS IN ROLEPLAY MODE" not in facts)
check("fact ORPHAN ROLL presente", "ORPHAN ROLL" in facts)
check("cita el dado crudo (17)", "1d20 = 17" in facts)
check("pide declarar la acción", "declare the action" in facts)
check("sin state_updates", r["state_updates"] == [])
check("sin pending nuevo", not (r["combat_state"] or {}).get("pending_rolls"))
check("no pide una tirada", r["prompt_player_roll"] is None)
# el motor no debe mutar nada
e = MechanicEngine(CombatState())
res = e.process_player_roll(BJORN, {"dice": "1d20", "result": 17, "rolls": [17]})
check("process_player_roll sigue devolviendo freeform_roll", res.get("action") == "freeform_roll")
check("orphan_roll appendea a results", any(x.get("action") == "orphan_roll" for x in e.results))
check("orphan no toca state_updates", e.state_updates == [])

# ═══════════════════════════════════════════════════════════════════════════
print("\nT4 — el template de roleplay ya no pide dados")
rp = Narrator.ROLEPLAY_TEMPLATE
check("prohibición explícita de pedir dados", "NEVER ASK FOR DICE HERE" in rp)
check("condiciona a PROMPT PLAYER", "PROMPT PLAYER" in rp)
check("manda declarar la acción", "DECLARE the action" in rp)
check("removida la vieja invitación",
      "tell them which skill and ask them to roll" not in rp)

print("\nT4b — SAM-054: la regla 15 ya no licencia aritmética")
sp = Narrator.SYSTEM_PROMPT
check("removido 'calculate the total: d20 result + ability modifier'",
      "calculate the total: d20 result" not in sp)
check("removido el ejemplo \"that's a total of 19\"", "total of 19" not in sp)
check("regla 15a prohíbe calcular", "NEVER calculate any total, modifier, damage, or HP value" in sp)
check("regla 15a exige números literales de los facts",
      "Report ONLY numbers that appear literally in the mechanical facts" in sp)
check("conserva CHARACTER KNOWLEDGE", "CHARACTER KNOWLEDGE" in sp)
check("regla ORPHAN ROLL presente y fuera del bloque de combate",
      "ORPHAN ROLLS (applies in AND out of combat)" in sp)
check("regla ADVANTAGE ASSUMED presente", "ADVANTAGE ASSUMED" in sp)

# ═══════════════════════════════════════════════════════════════════════════
print("\nT5 — SAM-059: 2d20 sin estado de ventaja → el mayor, y lo dice")
e = MechanicEngine(CombatState())
a, na = e._pick_d20({"dice": "2d20", "result": 26, "rolls": [19, 7]})
b, nb = e._pick_d20({"dice": "2d20", "result": 26, "rolls": [7, 19]})
check("[19, 7] → 19", a == 19)
check("[7, 19] → 19 (mismo resultado)", b == 19)
check("orden irrelevante", a == b)
check("fact ADVANTAGE ASSUMED en ambos", "ADVANTAGE ASSUMED" in (na or "") and "ADVANTAGE ASSUMED" in (nb or ""))
check("el fact cita ambos dados", "(7, 19)" in (nb or ""))
check("1d20 normal no emite nota", e._pick_d20({"dice": "1d20", "result": 12, "rolls": [12]}) == (12, None))
check("sin rolls cae al result", e._pick_d20({"dice": "1d20", "result": 9, "rolls": []}) == (9, None))
check("no-d20 múltiple no miente sobre ventaja",
      e._pick_d20({"dice": "2d6", "result": 9, "rolls": [4, 5]}) == (4, None))


def wolf(hp=50, ac=10):
    return CombatState({"active": True, "current_turn_index": 0, "actions_remaining": 1,
                        "initiative_order": [{"name": "Wolf", "is_npc": True,
                                              "hp": hp, "hp_max": hp, "ac": ac}]})


# el ataque real usa el mayor y el fact viaja al narrator
for order in ([7, 19], [19, 7]):
    c = wolf(ac=20)  # AC 20: con 7+7=14 falla, con 19+7=26 pega
    e = MechanicEngine(c)
    arm(e, {"type": "weapon_attack",
            "weapon": {"name": "Greatsword", "bonus": "+7", "damage": "2d6+4"},
            "target": "Wolf", "target_data": c.initiative_order[0]})
    r = e.process_player_roll(BJORN, {"dice": "2d20", "result": 26, "rolls": order})
    check(f"weapon_attack {order} → usa 19 (HIT)", r.get("attack_roll") == 19 and r.get("hit"))
    check(f"weapon_attack {order} → nota en el summary",
          "ADVANTAGE ASSUMED" in e.get_results_summary())

e = MechanicEngine(CombatState())
arm(e, {"type": "skill_check", "skill": "Perception", "dc": 15})
r = e.process_player_roll(BJORN, {"dice": "2d20", "result": 12, "rolls": [3, 9]})
check("skill_check 2d20 → usa 9, no 3", r.get("roll") == 9 and r.get("total") == 15)
check("skill_check emite la nota", "ADVANTAGE ASSUMED" in e.get_results_summary())

# ═══════════════════════════════════════════════════════════════════════════
print("\nT6 — regresión: combate normal intacto")
o, illm, nllm = orch('{"type": "attack", "weapon": "Greatsword", "target": "Wolf"}')
combat0 = wolf().to_dict()
combat0["initiative_order"].append({"name": "Björn Glacierfist", "is_npc": False,
                                    "hp": 60, "hp_max": 68, "ac": 14,
                                    "class": "Barbarian 7", "level": 7})
combat0["current_turn_index"] = 1
combat0["actions_remaining"] = 2
r1 = o.process_message(message="ataco con mi greatsword", sender_name="Björn Glacierfist",
                       character_context=BJORN, party_characters=[BJORN], combat_data=combat0)
p = pend_of(r1)
check("declaración → pending weapon_attack", (p or {}).get("type") == "weapon_attack")
check("arma correcta (Greatsword, no attacks[0])", (p or {}).get("weapon", {}).get("name") == "Greatsword")

r2 = o.process_message(message=sysev("Björn Glacierfist", "1d20", 18, [18]),
                       sender_name="Björn Glacierfist", character_context=BJORN,
                       party_characters=[BJORN], combat_data=r1["combat_state"])
p2 = pend_of(r2)
check("d20 → pending weapon_damage 2d6+4", (p2 or {}).get("damage_spec") == "2d6+4")
check("sin ADVANTAGE ASSUMED en 1d20 normal", "ADVANTAGE ASSUMED" not in nllm.last_user)

r3 = o.process_message(message=sysev("Björn Glacierfist", "2d6", 8, [5, 3]),
                       sender_name="Björn Glacierfist", character_context=BJORN,
                       party_characters=[BJORN], combat_data=r2["combat_state"])
check("daño aplicado al NPC (50 → 38)",
      any(c.get("name") == "Wolf" and c.get("hp") == 38
          for c in (r3["combat_state"] or {}).get("initiative_order", [])))
e = MechanicEngine(wolf())
arm(e, {"type": "weapon_damage", "weapon": {"name": "Greatsword", "damage": "2d6+4"},
        "damage_spec": "2d6+4", "target": "Wolf",
        "target_data": e.combat.initiative_order[0]})
e.process_player_roll(BJORN, {"dice": "1d20", "result": 5, "rolls": [5]})
check("SAM-039/042: dado equivocado sigue rechazado", "INVALID DICE" in e.get_results_summary())
check("SAM-039/042: pending preservado", e.get_pending("char-bjorn") is not None)

# ═══════════════════════════════════════════════════════════════════════════
print("\nT7 — smoke test .format() de todos los prompts tocados")
try:
    Narrator.SYSTEM_PROMPT.format(dm_style="X", campaign_context="Y",
                                  character_context="Z", party_context="W")
    check("Narrator.SYSTEM_PROMPT.format()", True)
except Exception as ex:
    check(f"Narrator.SYSTEM_PROMPT.format() → {ex}", False)
try:
    Narrator.ROLEPLAY_TEMPLATE.format(character_name="A", player_message="B")
    check("Narrator.ROLEPLAY_TEMPLATE.format()", True)
except Exception as ex:
    check(f"Narrator.ROLEPLAY_TEMPLATE.format() → {ex}", False)
try:
    Narrator.NARRATE_TEMPLATE.format(mechanical_facts="F", character_name="A", player_message="B")
    check("Narrator.NARRATE_TEMPLATE.format()", True)
except Exception as ex:
    check(f"Narrator.NARRATE_TEMPLATE.format() → {ex}", False)
try:
    out = IntentInterpreter.SYSTEM_PROMPT.format(
        character_name="A", character_class="B", character_level=1,
        spell_list="S", attack_list="T", in_combat=False, target_options="None")
    check("IntentInterpreter.SYSTEM_PROMPT.format()", True)
    check("los ejemplos JSON sobreviven al format()", '{"type": "skill_check"' in out)
except Exception as ex:
    check(f"IntentInterpreter.SYSTEM_PROMPT.format() → {ex}", False)
try:
    SAMOrchestrator.LOOT_ITEM_PROMPT.format(monster_name="M", count=1, rarity="trinket")
    check("SAMOrchestrator.LOOT_ITEM_PROMPT.format()", True)
except Exception as ex:
    check(f"SAMOrchestrator.LOOT_ITEM_PROMPT.format() → {ex}", False)

passed = sum(1 for _, c in results if c)
print(f"\n{passed}/{len(results)} checks passed")
print("ALL PASS ✅" if passed == len(results) else "SOME FAILED ❌")
sys.exit(0 if passed == len(results) else 1)
