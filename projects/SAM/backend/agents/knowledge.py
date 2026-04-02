# TODO: Knowledge agent — RAG lookup for spells, monsters, items, and campaign lore.
# Wraps the existing compendium_tools.py and match_documents RPC logic.
# Returns structured data (not narrative text) for the mechanic and narrator to use.
# Methods (planned):
#   lookup_spell(name_or_query) -> dict
#   lookup_monster(name_or_query) -> dict  (includes AC, HP, attacks, XP value)
#   lookup_item(name_or_query) -> dict
#   get_campaign_lore(query, campaign_id) -> str  (RAG over uploaded PDFs)
