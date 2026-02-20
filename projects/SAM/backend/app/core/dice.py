import re
import secrets
from enum import Enum
from typing import List, Dict, Any, Optional

class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"  # Only GM/System sees
    WHISPER = "whisper" # GM + Specific Player

class DiceRoller:
    """
    Handles secure random number generation and dice notation parsing.
    """
    
    @staticmethod
    def roll(expression: str) -> Dict[str, Any]:
        """
        Parses a dice expression (e.g., '1d20', '2d6+5') and returns detailed results.
        Current support: Simple AdX+B format.
        """
        expression = expression.lower().replace(" ", "")
        
        # Regex for 'AdX' or 'AdX+B' or 'AdX-B'
        match = re.match(r"^(\d+)d(\d+)([+-]\d+)?$", expression)
        
        if not match:
            raise ValueError(f"Invalid dice expression: {expression}")
            
        count = int(match.group(1))
        sides = int(match.group(2))
        modifier_str = match.group(3)
        modifier = int(modifier_str) if modifier_str else 0
        
        if count > 100:
            raise ValueError("Too many dice! Max 100.")
        if sides < 2 or sides > 1000:
            raise ValueError("Invalid number of sides.")

        rolls = []
        for _ in range(count):
            # secure random number 1 to sides
            r = secrets.randbelow(sides) + 1
            rolls.append(r)
            
        total = sum(rolls) + modifier
        
        return {
            "expression": expression,
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
            "natural_20": 20 in rolls if sides == 20 else False,
            "natural_1": 1 in rolls if sides == 20 else False
        }

    @staticmethod
    def resolve_visibility(roll_result: Dict, visibility: Visibility, user_id: str, target_id: Optional[str] = None) -> Dict:
        """
        Filters the roll result based on who is asking.
        (Logic to be expanded when integrating with WebSocket/Users)
        """
        return {
            "result": roll_result,
            "visibility": visibility,
            "owner": user_id
        }
