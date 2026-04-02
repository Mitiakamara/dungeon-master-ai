# TODO: Mechanic agent — pure Python, no LLM.
# Receives structured intent from interpreter + current game state.
# Executes all deterministic game logic:
#   - Rolls NPC dice via agents/dice.py (secrets.randbelow)
#   - Resolves attack hits via rules.check_hit()
#   - Applies HP changes via rules.calculate_hp_change()
#   - Advances combat turns via CombatState.advance_turn()
#   - Awards XP, calculates level-ups via rules.get_level_for_xp()
#   - Generates loot structures
# Returns: MechanicResult dict with all state changes + roll breakdown for narrator.
