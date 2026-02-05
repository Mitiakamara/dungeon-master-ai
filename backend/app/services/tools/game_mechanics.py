from langchain_core.tools import tool

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

MECHANIC_TOOLS = [apply_damage, apply_healing]
