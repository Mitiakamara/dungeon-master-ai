# TODO: Interpreter agent — LLM with a short, focused prompt.
# Input:  raw player message + character context + combat state
# Output: structured intent dict, e.g.:
#   {"action": "attack", "target": "Goblin A", "weapon": "Warhammer", "modifier": 4}
#   {"action": "skill_check", "skill": "Perception", "modifier": 3}
#   {"action": "cast_spell", "spell": "Fireball", "targets": ["Goblin A", "Goblin B"]}
#   {"action": "roleplay", "text": "..."}
