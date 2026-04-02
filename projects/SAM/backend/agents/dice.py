import secrets


class DiceRoller:
    """Cryptographically secure dice roller for NPCs and system rolls."""

    @staticmethod
    def roll(sides: int) -> int:
        """Roll a single die. Returns 1-sides."""
        return secrets.randbelow(sides) + 1

    @staticmethod
    def roll_multiple(count: int, sides: int) -> list[int]:
        """Roll multiple dice. Returns list of individual results."""
        return [DiceRoller.roll(sides) for _ in range(count)]

    @staticmethod
    def roll_with_modifier(count: int, sides: int, modifier: int = 0) -> dict:
        """Roll dice with modifier. Returns breakdown."""
        rolls = DiceRoller.roll_multiple(count, sides)
        total = sum(rolls) + modifier
        mod_str = ('+' + str(modifier)) if modifier > 0 else (str(modifier) if modifier < 0 else '')
        return {
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
            "notation": f"{count}d{sides}{mod_str}"
        }

    @staticmethod
    def roll_advantage() -> dict:
        """Roll 2d20, take highest."""
        rolls = DiceRoller.roll_multiple(2, 20)
        return {"rolls": rolls, "result": max(rolls), "type": "advantage"}

    @staticmethod
    def roll_disadvantage() -> dict:
        """Roll 2d20, take lowest."""
        rolls = DiceRoller.roll_multiple(2, 20)
        return {"rolls": rolls, "result": min(rolls), "type": "disadvantage"}
