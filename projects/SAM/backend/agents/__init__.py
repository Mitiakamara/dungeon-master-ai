# SAM Multi-Agent System
# Each agent has a single responsibility:
#   orchestrator  — routes messages between agents
#   interpreter   — LLM: understands player intent
#   mechanic      — pure Python: dice, HP, rules math
#   narrator      — LLM: creative storytelling
#   knowledge     — RAG: spells, monsters, items lookup
#   combat_state  — persistent combat state machine
#   dice          — cryptographically secure RNG
#   rules         — D&D 5e tables and calculations
