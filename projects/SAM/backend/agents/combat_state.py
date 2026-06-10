from typing import Optional
from .dice import DiceRoller


# D&D 5e classes that gain Extra Attack at level 5 (2 attacks/turn)
# Fighter gets a 3rd at 11, a 4th at 20 — simplified to 2 here.
EXTRA_ATTACK_CLASSES = {"barbarian", "fighter", "paladin", "ranger"}


def has_extra_attack(combatant: dict) -> bool:
    """
    True if this combatant is a player whose class grants Extra Attack
    (Barbarian/Fighter/Paladin/Ranger at level 5+).
    """
    if not combatant or combatant.get("is_npc"):
        return False
    # PDF import stores class with a level suffix ("Barbarian 7"); take the
    # first word so "barbarian 7" matches the class set. Guard against empty.
    cls_raw = str(combatant.get("class", "") or "").lower().strip()
    cls = cls_raw.split()[0] if cls_raw else ""
    try:
        level = int(combatant.get("level", 1) or 1)
    except (TypeError, ValueError):
        level = 1
    return cls in EXTRA_ATTACK_CLASSES and level >= 5


class CombatState:
    """Manages combat state — initiative, turns, NPC HP."""

    def __init__(self, data: dict = None):
        data = data or {}
        self.active = data.get("active", False)
        self.round = data.get("round", 0)
        self.current_turn_index = data.get("current_turn_index", 0)
        self.initiative_order = data.get("initiative_order", [])
        self.pending_action = data.get("pending_action", None)  # Waiting for player dice
        self.actions_remaining = data.get("actions_remaining", 0)
        self.sneak_used = data.get("sneak_used", False)  # Sneak Attack: once per turn (SAM-003)

    def _set_actions_for_current_turn(self):
        """Seed actions_remaining when entering a new player's turn."""
        self.sneak_used = False  # Sneak Attack refreshes each turn
        current = self.get_current_turn()
        if current and not current.get("is_npc"):
            self.actions_remaining = 2 if has_extra_attack(current) else 1
        else:
            self.actions_remaining = 0

    def start_combat(self, combatants: list[dict]) -> dict:
        """Start combat with a list of combatants. Rolls initiative for NPCs."""
        for c in combatants:
            if c.get("is_npc", False):
                init_roll = DiceRoller.roll(20)
                init_mod = c.get("initiative_modifier", 0)
                c["initiative"] = init_roll + init_mod
                c["initiative_roll"] = init_roll
            # Players already have their initiative from SYSTEM EVENT

        # Sort by initiative (descending), NPCs break ties
        self.initiative_order = sorted(
            combatants,
            key=lambda x: (-x["initiative"], x.get("is_npc", False))
        )
        self.active = True
        self.round = 1
        self.current_turn_index = 0
        self._set_actions_for_current_turn()
        print(f"⚔️ Combat STARTED with {len(combatants)} combatants")
        return self.to_dict()

    def get_current_turn(self) -> Optional[dict]:
        """Get whose turn it is."""
        if not self.active or not self.initiative_order:
            return None
        return self.initiative_order[self.current_turn_index]

    def advance_turn(self) -> dict:
        """Move to next combatant in initiative order."""
        if not self.active:
            return self.to_dict()
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.initiative_order):
            self.current_turn_index = 0
            self.round += 1
        self._set_actions_for_current_turn()
        return self.to_dict()

    def consume_action(self):
        """Decrement actions_remaining when a player completes an action (damage applied)."""
        if self.actions_remaining > 0:
            self.actions_remaining -= 1

    def mark_sneak_used(self):
        """Sneak Attack is once per turn — mark it spent (SAM-003)."""
        self.sneak_used = True

    def sneak_available(self) -> bool:
        """True if Sneak Attack hasn't been used this turn."""
        return not self.sneak_used

    def turn_is_over(self) -> bool:
        """True when the current combatant has no actions left and no pending dice."""
        return self.actions_remaining <= 0 and self.pending_action is None

    def remove_combatant(self, name: str):
        """Remove a combatant (dead/fled)."""
        self.initiative_order = [c for c in self.initiative_order if c["name"] != name]
        if self.current_turn_index >= len(self.initiative_order):
            self.current_turn_index = 0
        # End combat if no NPCs remain alive
        npcs_alive = [c for c in self.initiative_order if c.get("is_npc") and c.get("hp", 0) > 0]
        if not npcs_alive:
            self.end_combat()

    def update_npc_hp(self, name: str, new_hp: int):
        """Update an NPC's HP. Match is case/space-insensitive (SAM-038)."""
        matched = False
        for c in self.initiative_order:
            if c["name"].lower().strip() == name.lower().strip():
                old = c.get("hp", 0)
                c["hp"] = new_hp
                matched = True
                print(f"💢 NPC HP: {c['name']} {old} → {new_hp}")
                if new_hp <= 0:
                    print(f"☠️ NPC down: {c['name']} (removing from combat)")
                    self.remove_combatant(c["name"])
                break
        if not matched:
            print(f"⚠️ update_npc_hp: no combatant matched '{name}'. "
                  f"Order: {[c.get('name') for c in self.initiative_order]}")

    def end_combat(self):
        """End combat."""
        print(f"🏁 Combat ENDED (round was {self.round})")
        self.active = False
        self.round = 0
        self.current_turn_index = 0
        self.pending_action = None
        self.actions_remaining = 0
        self.sneak_used = False

    def set_pending_action(self, action: dict):
        """Set a pending action waiting for player dice."""
        self.pending_action = action

    def clear_pending_action(self):
        """Clear pending action after player rolls."""
        self.pending_action = None

    def to_dict(self) -> dict:
        """Serialize for storage in campaigns.settings.combat."""
        # current_turn: name of whose turn it is (for frontend convenience)
        current = self.get_current_turn()
        return {
            "active": self.active,
            "round": self.round,
            "current_turn_index": self.current_turn_index,
            "current_turn": current.get("name") if current else None,
            "initiative_order": self.initiative_order,
            "pending_action": self.pending_action,
            "actions_remaining": self.actions_remaining,
            "sneak_used": self.sneak_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CombatState':
        return cls(data)
