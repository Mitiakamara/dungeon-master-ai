from typing import Optional
from .dice import DiceRoller


class CombatState:
    """Manages combat state — initiative, turns, NPC HP."""

    def __init__(self, data: dict = None):
        data = data or {}
        self.active = data.get("active", False)
        self.round = data.get("round", 0)
        self.current_turn_index = data.get("current_turn_index", 0)
        self.initiative_order = data.get("initiative_order", [])
        self.pending_action = data.get("pending_action", None)  # Waiting for player dice

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
        return self.to_dict()

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
        """Update an NPC's HP."""
        for c in self.initiative_order:
            if c["name"] == name:
                c["hp"] = new_hp
                if new_hp <= 0:
                    self.remove_combatant(name)
                break

    def end_combat(self):
        """End combat."""
        self.active = False
        self.round = 0
        self.current_turn_index = 0
        self.pending_action = None

    def set_pending_action(self, action: dict):
        """Set a pending action waiting for player dice."""
        self.pending_action = action

    def clear_pending_action(self):
        """Clear pending action after player rolls."""
        self.pending_action = None

    def to_dict(self) -> dict:
        """Serialize for storage in campaigns.settings.combat."""
        return {
            "active": self.active,
            "round": self.round,
            "current_turn_index": self.current_turn_index,
            "initiative_order": self.initiative_order,
            "pending_action": self.pending_action
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CombatState':
        return cls(data)
