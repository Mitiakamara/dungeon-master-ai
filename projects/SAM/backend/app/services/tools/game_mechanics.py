from langchain_core.tools import tool
from typing import List, Dict, Optional, Union

@tool
def apply_damage(current_hp: int, damage_amount: int) -> str:
    """
    Calculates new HP after damage and returns the REQUIRED <UPDATE> tag.
    USE THIS TOOL whenever the user or an enemy deals damage.
    
    Args:
        current_hp: The character's current HP (from context).
        damage_amount: The amount of damage taken.
        
    Returns:
        A string containing the calculation and the JSON update tag.
    """
    new_hp = max(0, current_hp - damage_amount)
    
    # We return the tag specifically so the LLM can just paste it
    return f"Calculation: {current_hp} - {damage_amount} = {new_hp}. <UPDATE>{{\"status\": {{\"hp_current\": {new_hp}}}}}</UPDATE>"

@tool
def apply_healing(current_hp: int, heal_amount: int, max_hp: int) -> str:
    """
    Calculates new HP after healing and returns the REQUIRED <UPDATE> tag.
    USE THIS TOOL whenever the user heals.
    
    Args:
        current_hp: The character's current HP.
        heal_amount: The amount of healing.
        max_hp: The character's maximum HP (to prevent overheating).
        
    Returns:
        A string containing the calculation and the JSON update tag.
    """
    new_hp = min(max_hp, current_hp + heal_amount)
    
    return f"Calculation: {current_hp} + {heal_amount} = {new_hp} (Max: {max_hp}). <UPDATE>{{\"status\": {{\"hp_current\": {new_hp}}}}}</UPDATE>"

@tool
def give_loot(money: Optional[Dict[str, int]] = None, items: Optional[List[Dict[str, Union[str, int]]]] = None) -> str:
    """
    Generates a structured loot drop.
    USE THIS TOOL whenever the player finds items or money.
    
    Args:
        money: Dictionary of currency, e.g., {'gp': 10, 'sp': 5}.
        items: List of item dictionaries. EACH item MUST have 'item' (str) and 'qty' (int). Example: [{'item': 'Potion', 'qty': 1}].
        
    Returns:
        The formatted <LOOT> tag for the frontend.
    """
    loot_data = {}
    description = []
    
    if money:
        loot_data["money"] = money
        money_desc = ", ".join([f"{v}{k}" for k, v in money.items()])
        description.append(f"Money: {money_desc}")
        
    if items:
        loot_data["items"] = items
        items_desc = ", ".join([f"{i.get('qty', 1)}x {i['item']}" for i in items])
        description.append(f"Items: {items_desc}")
        
    import json
    return f"Loot Generated: {'; '.join(description)}. <LOOT>{json.dumps(loot_data)}</LOOT>"

MECHANIC_TOOLS = [apply_damage, apply_healing, give_loot]
