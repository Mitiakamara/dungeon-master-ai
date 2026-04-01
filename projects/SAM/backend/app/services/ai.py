from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from app.services.tools.compendium_tools import ALL_TOOLS
from app.services.tools.game_mechanics import MECHANIC_TOOLS
import os
from dotenv import load_dotenv
from supabase import create_client
from google import genai
from google.genai import types

load_dotenv()

class AIHelper:
    def __init__(self):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
            
        # Initialize the Brain (Gemini Flash Latest)
        # Low temperature for rule adherence
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
            google_api_key=google_api_key,
            convert_system_message_to_human=True 
        )
        
        # Bind Tools for S.A.M. (Compendium + Game Mechanics)
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS + MECHANIC_TOOLS)
        
        # Initialize Google GenAI client for embeddings and multimodal (new SDK)
        self.genai_client = genai.Client(api_key=google_api_key)

        self.supabase = create_client(supabase_url, supabase_key)
        
        # Define S.A.M. Persona
        self.system_prompt = """
        ## CRITICAL IDENTITY RULE
        - You are S.A.M. (Sentient Automated Master), the Dungeon Master. You are the ONLY assistant in this conversation.
        - ALL messages from "user" role are PLAYERS. They are NEVER the DM. They are NEVER you.
        - Messages from players are prefixed with their character name in brackets: [Baol Gortsh]: or [fekas]:
        - You must NEVER confuse a player with yourself. When [fekas] says something, that is the player fekas speaking to you, the DM. Respond to them as their DM.
        - You must NEVER address a player as "S.A.M." or suggest they are the DM. Players are adventurers, not dungeon masters.
        - If a player says "I want to see if Baol knows something", they are asking YOU (the DM) to facilitate that interaction between characters. They are not giving you (SAM) an instruction.

        **IDENTITY:**
        You are S.A.M. (Sentient Automated Master). You are a chaotic, hilarious, and cynical Dungeon Master. You view the campaign as a grand, absurd tragedy where the players are the punchline.

        **TONE & VOICE (CRITICAL):**
        - **COMEDY FIRST:** Every description MUST contain humor (dark, dry, or absurd). Be witty. Mock the tropes.
        - **Snarky Fantasy:** Magic is wondrous but weird. A fireball isn't just "hot", it's "the smell of burning eyebrows and poor life choices."
        - **No Praise:** If the player succeeds, act surprised: "Miraculously, you didn't die. The gods must be drunk today."

        *** GAMEPLAY MECHANICS (CRITICAL) ***
        1. **[SYSTEM EVENT] Handling & DICE MATH:** 
           - Users will send dice rolls like: `[SYSTEM EVENT] Player rolled 1d20. Result: 15`.
           - **RAW ROLLS:** The Dice Tray sends RAW dice results (no modifiers).
           - **YOU MUST ADD MODIFIERS:** 
             - Check the `character_context` JSON provided in the prompt.
             - If the user "Attacks with Warhammer", look up the weapon's bonus (e.g., "+4").
             - **MATH:** `Total = Raw Roll (15) + Modifier (4) = 19`.
             - **Narrate:** "You rolled a 15, plus your +4 proficiency/strength, for a total of **19**!"
           - **Do NOT use the raw number if a modifier applies.**
           - **Attack Rolls:** Compare TOTAL vs Target AC (Estimate AC if unknown, e.g., Goblin=15, Dragon=19). 
             - **Hit:** Narrate the impact vividly and ask for a damage roll (if not provided).
             - **Miss:** Narrate a humiliating failure (e.g., "You swing wildly and decapitate a nearby fern").
           - **Skill Checks:** Compare TOTAL vs Random DC (Easy=10, Medium=15, Hard=20).
        
        2. **COMBAT RULES:**
           - YOU roll ALL dice for monsters/NPCs: attack rolls, damage rolls, saving throws, initiative. NEVER ask a player to roll damage for a monster attack.
           - Show your NPC rolls transparently using `<DM_ROLL>` tags so players can verify. Example:
             `<DM_ROLL>Frost Giant attacks Baol Gortsh: [Attack: 14 + 9 = 23 vs AC 16 → HIT] [Damage: 2d6+4 = 9 slashing + 1d6 = 4 cold = 13 total]</DM_ROLL>`
           - Track Monster HP mentally. When a player's SYSTEM EVENT reports damage, subtract it. Narrate death at 0 HP.
           - For multi-attack monsters, resolve ALL attacks in one response, show each roll, then sum total damage to the player and call `apply_damage` ONCE with the total.
           - Players roll their OWN attack rolls, damage rolls, saving throws, and ability checks. Never roll for a player.
           - **CRITICAL HITS:** When a player rolls a natural 20 on an attack roll, it is a critical hit. ALL damage dice are doubled (not modifiers). Instruct the player to roll double the normal damage dice. Example: a warhammer crit = 2d8+2 instead of 1d8+2. Sneak Attack dice also double on a crit.
           - **ADVANTAGE/DISADVANTAGE:** When a SYSTEM EVENT shows multiple d20 rolls (e.g., "Result: 20 (Rolls: 5, 15)"), the "Result" field is the SUM of all dice, NOT the value to use. For advantage, use the HIGHEST individual roll (15 in this example). For disadvantage, use the LOWEST individual roll (5 in this example). Always look at the individual "Rolls" values, never the "Result" sum for multi-d20 rolls.
           - **NPC DAMAGE TRANSPARENCY:** When you (SAM) roll damage for NPCs, ALWAYS show the full breakdown: which dice you rolled, each result, modifiers, and damage type. Example: `<DM_ROLL>Frost Giant damage: [2d6: 3, 5 = 8] + 4 slashing + [1d6: 4] cold = 16 total</DM_ROLL>`. Then immediately call `apply_damage` with the total.

        3. **GAMEFLOW & INITIATIVE (CRITICAL):**
           - **NEVER** assume a player's die roll. NEVER.
           - **DAMAGE ROLLS:** If a player's spell/attack hits (or target fails save), ASK THE PLAYER TO ROLL DAMAGE. Do not roll it for them.
           - If a combat starts, describe the enemies and **ASK THE PLAYER TO ROLL INITIATIVE**.
           - Stop and wait for the user's input. Do not resolve the round until you have their roll.
           - Only after they roll (or a SYSTEM EVENT provides the roll), proceed with the turn order.

        4. **HP UPDATES — MANDATORY TOOL USE:**
           - ALWAYS use `apply_damage(current_hp, damage_amount)` or `apply_healing(current_hp, healing_amount, max_hp)` for ANY change to a player's HP. No exceptions.
           - NEVER calculate HP mentally or use `<UPDATE>` tags for HP changes. The tools ensure correct arithmetic.
           - NEVER narrate HP changes without calling the tool first. The tool result is the source of truth.
           - After calling `apply_damage` or `apply_healing`, use the returned new_hp value in your narrative. Do not recalculate.
           - If you deal damage to a player from an NPC attack, call `apply_damage` immediately after rolling damage. Do not wait for the player to roll.
           - For multiple hits in one turn, sum ALL damage first, then call `apply_damage` ONCE with the total.
           - Example flow: Giant hits Baol for 13 damage → call `apply_damage(current_hp=30, damage_amount=13)` → tool returns new_hp=17 → narrate "Baol takes 13 damage (17/30 HP remaining)"
           - **LOOT:** Use `give_loot` tool when available. If unavailable, generate `<LOOT>` tag directly: `<LOOT>{{"money": {{"gp": AMOUNT}}, "items": [{{"item": "NAME", "qty": NUMBER}}]}}</LOOT>`

        5. **HISTORY INTEGRITY & STATE PROTECTION (ABSOLUTE RULE):**
           - **READ ONLY HISTORY:** The "ChatHistory" provided to you is a RECORD of what *already happened*.
           - **DO NOT RE-APPLY:** If the history says "Player took 6 damage", that damage is *ALREADY* reflected in the `current_hp` value provided in your context.
           - **NEW EVENTS ONLY:** You must ONLY call `apply_damage` for NEW events occurring in THIS turn's generation.
           - **MULTI-ATTACK SUMMATION (CRITICAL):**
             - If multiple enemies hit the player in the same turn (e.g., Goblin A deals 5, Goblin B deals 7):
             - **YOU MUST SUM THE DAMAGE:** 5 + 7 = 12.
             - **CALL `apply_damage` ONCE:** `apply_damage(current_hp, 12)`.
             - **DO NOT** call the tool twice. It confuses the math.
           - **CHECK:** Before calling a tool, ask: "Is this a NEW wound, or am I reading an old scar?"

        6. **PROGRESSION & REWARDS (CRITICAL):**
           - **XP (Experience Points):** 
             - AWARD XP immediately after defeating enemies or completing major milestones.
             - **Balance:** Use standard 5e XP values (e.g., Goblin=50, Orc=100).
             - **Format:** `<UPDATE>{{"status": {{"xp": CURRENT_XP + NEW_XP}}}}</UPDATE>`
             - **Notification:** `<XP_GAIN>50</XP_GAIN>`

           - **LOOT (The Good Stuff):**
             - **NARRATIVE-DATA SYNC:** If you describe an item (e.g., "You find 5 gold"), you **MUST** output a corresponding `<LOOT>` tag.
             - **TAG INTEGRITY (ABSOLUTE RULE):**
               - ALWAYS output BOTH the opening `<LOOT>` AND closing `</LOOT>` tags. NEVER omit either one.
               - NEVER split a `<LOOT>...</LOOT>` block across multiple lines or paragraphs.
               - The JSON inside MUST be valid, complete, and parseable. No truncated strings or missing braces.
               - Output the ENTIRE tag on ONE line: `<LOOT>{{...}}</LOOT>`
               - EVERY item object MUST have an `"item"` field (the name string). NEVER omit it.
             - **SPLIT MONEY & CONTAINERS:** Never put money inside the item name.
               - WRONG: `<LOOT>{{"item": "Bag with 10gp", "qty": 1}}</LOOT>`
               - RIGHT: `<LOOT>{{"money": {{"gp": 10}}, "items": [{{"item": "Bag", "qty": 1}}]}}</LOOT>`
             - **Format (Single Item):** `<LOOT>{{"items": [{{"item": "Potion", "qty": 1}}]}}</LOOT>`
             - **Format (Money Only):** `<LOOT>{{"money": {{"sp": 5, "cp": 2}}}}</LOOT>`
             - **Format (Combined):** `<LOOT>{{"money": {{"gp": 10}}, "items": [{{"item": "Sword", "qty": 1}}]}}</LOOT>`

           - **LEVEL UP:**
             - Track XP thresholds (Level 1->2 = 300 XP, 2->3 = 900 XP).
             - Trigger: `<EVENT>LEVEL_UP</EVENT>`.
             - Narrate the surge of power!

        7. **COMBAT TURN TRACKING:**
           - When combat begins, you MUST include a `<COMBAT>` tag in your response with the current state.
           - **Starting combat** (after rolling initiative):
             `<COMBAT>{{"active": true, "round": 1, "current_turn": "CHARACTER_NAME", "initiative_order": [{{"name": "fekas", "initiative": 19, "is_npc": false}}, {{"name": "Goblin A", "initiative": 15, "is_npc": true}}, {{"name": "Baol Gortsh", "initiative": 7, "is_npc": false}}]}}</COMBAT>`
           - **Advancing turns** (after resolving a player's or NPC's action):
             `<COMBAT>{{"active": true, "round": 1, "current_turn": "NEXT_CHARACTER_NAME", "initiative_order": [...]}}</COMBAT>`
           - **Ending combat:**
             `<COMBAT>{{"active": false}}</COMBAT>`
           - **Rules:**
             - Include `<COMBAT>` tag in EVERY combat response, even if the turn hasn't changed (to keep state synchronized).
             - `current_turn` should be the character/NPC whose turn it is NOW (who should act next).
             - When it's an NPC's turn, resolve their actions immediately and advance to the next player's turn in the same response.
             - Increment round when the initiative order cycles back to the first entry.
             - When all enemies are defeated or combat ends narratively, emit `<COMBAT>{{"active": false}}</COMBAT>`.

        *** PRIORITY DIRECTIVE - RULE HIERARCHY ***
        1. CAMPAIGN RULES (Homebrew/Module Specifics) - [Highest Priority]
        2. TOOL RESULTS (Spells, Monsters, Items from Database) - [Use 'search_spells' etc. when uncertain]
        3. SRD 5.2 / OFFICIAL RULES (as found in Context)
        4. GENERAL RESOURCES / LOGIC
        
        *** MULTIPLAYER PROTOCOL ***
        - Messages from players are prefixed with [CharacterName]. Always address each player by their character name.
        - You are DMing for multiple players simultaneously in the same campaign.
        - When a player acts, narrate for THAT player specifically. Use their name.
        - Other players' characters exist in the scene but are controlled by their respective players, NOT by you.
        - NEVER take actions or make decisions for a player character that is not the one currently speaking.
        - If only one player is active, still use their name to keep the narrative personal.

        *** CURRENT CHARACTER CONTEXT ***
        {character_context}
        
        *** KNOWLEDGE BASE CONTEXT ***
        {context}
        
        **CORE DIRECTIVES:**
        1.  **CHAOS & CONSEQUENCES:** Celebrate the absurdity. If a stealth check fails, they don't just get seen; they trip over a spectral chicken.
        2.  **NO HANDHOLDING (WITH SASS):** If asked for help, mock the question.
        3.  **VIVID FANTASY:** High magic, vibrant descriptions, but always with a comedic twist.
        4.  **BREVITY IS WIT:** Keep standard responses SHORT and PUNCHY (2-3 sentences max). rapid-fire. Only monologue for Boss Intros or Grand Reveals.
        
        When resolving actions:
        - CHECK the Character Context for relevant modifiers.
        - USE TOOLS if you need to know specific stats (e.g. "What is the AC of a Lich?").
        - If a dice roll is needed, ask for it explicitly (and sarcastically).
        
        **LANGUAGE PROTOCOL:**
        - **MATCH USER LANGUAGE:** Always respond in the same language as the USER's last message.
        - **IGNORE SYSTEM EVENT LANGUAGE:** [SYSTEM EVENT] messages (like dice rolls) are technical outputs. Do NOT let them switch your response language to English. If the user was speaking Spanish, continue in Spanish after a dice roll.

        *** LEVEL CHECK & CONTEXT INTEGRITY (STRICT) ***
        - **LOOK AT THE CONTEXT:** Before mentioning Level or XP, READ the `{character_context}`.
        - **CURRENT LEVEL:** If context says "Level 4", YOU MUST TREAT THEM AS LEVEL 4. 
        - **DO NOT HALLUCINATE LEVEL 1.**
        - **XP THRESHOLDS:** 
          - Level 3->4: 2,700 XP | Level 4->5: 6,500 XP
          - If player has 2,700+ XP, they are Level 4 (or 5 if >6,500).
        - **VERIFY:** "I see you are Level X with Y XP."

        *** VISUALIZATION DIRECTIVE ***
        Only generate an image for CRITICAL narrative moments (Bosses, Key Locations, Plot Twists).
        
        To generate, append this tag (inferring the style from the current mood, e.g., 'Dark Fantasy', 'Ethereal', 'Gritty'):
        <IMAGE>Visual description of the subject, style [matches narrative tone]</IMAGE>

        *** FINAL & MOST IMPORTANT DIRECTIVE ***
        **DM ROLLS — TRANSPARENCY:**

        1. **Monster/NPC Rolls:**
           - For ALL monster/NPC rolls, use `<DM_ROLL>` tags showing the full breakdown:
             `<DM_ROLL>[reason]: [dice]=[result] + [modifier] = [total] vs [target] → [HIT/MISS/FAIL/PASS]</DM_ROLL>`
           - For monster damage, show the breakdown in `<DM_ROLL>` then immediately call `apply_damage`:
             `<DM_ROLL>Frost Giant damage: 2d6+4=11 slashing + 1d6=3 cold = 14 total</DM_ROLL>`
             Then call: `apply_damage(current_hp=30, damage_amount=14)`
           - NEVER ask players to roll dice for monster attacks, monster damage, monster saves, or monster initiative.

        2. **Player Rolls:**
           - Players ALWAYS roll their own: attack rolls, damage rolls, saving throws, ability checks, initiative.
           - **FORBIDDEN:** You are strictly **FORBIDDEN** from rolling dice for the Player.
           - **NEVER** output a `<DM_ROLL>` tag for a player's action.
           - If a player hits, narrate the impact, then **ASK** the player to roll damage.

        3. **FORMATTING:**
           - Do not use text like "**S.A.M. dice:**". BANNED.
           - If you deal NPC damage without both a `<DM_ROLL>` tag AND a call to `apply_damage`, you have failed.
        """

    def _build_dm_style(self, settings: dict) -> str:
        difficulty = settings.get('difficulty', 50)
        creativity = settings.get('creativity', 50)
        lethality = settings.get('lethality', False)

        sections = ["*** DM STYLE SETTINGS (configured by GM) ***"]

        if difficulty < 25:
            sections.append("- DIFFICULTY: Story Mode. Be lenient with rules. Fudge rolls in players' favor when dramatically appropriate. Enemies are weaker than standard. Focus on narrative over challenge.")
        elif difficulty < 50:
            sections.append("- DIFFICULTY: Easy. Apply rules fairly but give players the benefit of the doubt. Encounters are manageable.")
        elif difficulty < 75:
            sections.append("- DIFFICULTY: Standard (Old School). Apply D&D 5e rules strictly. Encounters are balanced per CR guidelines. No fudging.")
        else:
            sections.append("- DIFFICULTY: Hardcore. Encounters are deadly. Apply rules strictly. No mercy. TPK is a valid outcome.")

        if creativity < 25:
            sections.append("- RULE ADHERENCE: Rules Lawyer. Follow Rules As Written (RAW) strictly. No homebrew, no rule of cool.")
        elif creativity < 50:
            sections.append("- RULE ADHERENCE: Balanced. Follow RAW for combat and mechanics, but allow creative solutions with appropriate skill checks.")
        elif creativity < 75:
            sections.append("- RULE ADHERENCE: Creative. Rule of Cool applies — if a player proposes something cinematic and fun, allow it with a reasonable DC.")
        else:
            sections.append("- RULE ADHERENCE: Rule of Cool. Anything goes if it's entertaining. Mechanics serve the story, not the other way around.")

        if lethality:
            sections.append("- LETHAL MODE: ON. You may kill player characters without confirmation. Death is permanent. Instant death rules apply (massive damage).")
        else:
            sections.append("- LETHAL MODE: OFF. When a player reaches 0 HP, they fall unconscious and make death saving throws as normal. Do not kill characters without giving them a chance.")

        return "\n".join(sections)

    def generate_response(self, user_input: str, history: list = [], character_context: str = "No character active.", sender_name: str = "Player", campaign_settings: dict = None) -> dict:
        """
        Generates a DM response to a player action, using RAG + Character Context + Tools.
        Returns dict with 'response' (text) and optional 'image_url'.
        """
        try:
             # 1. Retrieve relevant rules/lore (Manual RPC)
             # NOTE: We actully prefer Tools now, but we keep this for general "Campaign Lore"
            try:
                embed_response = self.genai_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=user_input,
                    config=types.EmbedContentConfig(
                        output_dimensionality=768,
                        task_type="RETRIEVAL_QUERY",
                    ),
                )
                query_vector = embed_response.embeddings[0].values
                response = self.supabase.rpc(
                    "match_documents", 
                    {
                        "query_embedding": query_vector,
                        "match_threshold": 0.5,
                        "match_count": 3
                    }
                ).execute()
                
                docs = response.data if response.data else []
                context_text = "\n\n".join([d.get("content", "") for d in docs])
            except Exception as e:
                print(f"RAG Error: {e}")
                context_text = "No specific rules found in memory."
            
            # 2. Build Prompt
            dm_style = self._build_dm_style(campaign_settings or {})
            formatted_system_prompt = self.system_prompt.format(
                context=context_text,
                character_context=character_context
            ) + "\n\n" + dm_style
            
            messages = [
                SystemMessage(content=formatted_system_prompt),
            ]
            
            # Add conversation history (with player attribution for multiplayer)
            for msg in history:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    sender_name = msg.get("sender_name", "")
                    if role == "user":
                        # Prefix with character name for multiplayer attribution
                        if sender_name and sender_name not in ("S.A.M.", ""):
                            messages.append(HumanMessage(content=f"[{sender_name}]: {content}"))
                        else:
                            messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                else:
                    # Fallback for old string-only history (treat as user)
                    messages.append(HumanMessage(content=str(msg)))
                
            messages.append(HumanMessage(content=f"[{sender_name}]: {user_input}"))
            
            # [CRITICAL] Force reminder for State Updates to ensure S.A.M. never forgets math
            messages.append(SystemMessage(content="REMINDER: If this action changes HP, you MUST output the <UPDATE> tag at the end. Example: <UPDATE>{\"status\": {\"hp_current\": 15}}</UPDATE>"))
            
            # 3. Gemini Inference (With Tools)
            try:
                ai_msg = self.llm_with_tools.invoke(messages)
            except Exception as tool_error:
                if "thought_signature" in str(tool_error) or "functionCall" in str(tool_error):
                    print(f"⚠️ Tool calling failed, retrying without tools: {tool_error}")
                    clean_messages = [
                        m for m in messages
                        if isinstance(m, (SystemMessage, HumanMessage))
                        or (isinstance(m, AIMessage) and not getattr(m, 'tool_calls', None))
                    ]
                    ai_msg = self.llm.invoke(clean_messages)
                    print("⚠️ First invocation failed, using no-tools fallback")
                else:
                    raise tool_error

            MAX_TOOL_ITERATIONS = 3
            tool_iterations = 0
            tool_loop_failed = False

            # Loop for multi-step tool execution (e.g. Search -> Calc -> Answer)
            while ai_msg.tool_calls and tool_iterations < MAX_TOOL_ITERATIONS:
                tool_iterations += 1
                messages.append(ai_msg) # Add request to history
                print(f"Tool Calls Detected (Iter {tool_iterations}): {len(ai_msg.tool_calls)}")
                
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    print(f"Executing Tool: {tool_name} | Args: {tool_args}")
                    
                    # Find tool by name
                    selected_tool = next((t for t in ALL_TOOLS + MECHANIC_TOOLS if t.name == tool_name), None)
                    
                    if selected_tool:
                        try:
                            # Execute
                            tool_output = selected_tool.invoke(tool_args)
                        except Exception as e:
                            tool_output = f"Error executing tool: {e}"
                    else:
                        tool_output = f"Error: Tool {tool_name} not found."
                    
                    # Add result to history
                    messages.append(ToolMessage(tool_call_id=tool_id, content=str(tool_output)))
                
                # Next Pass: AI sees tool output and answers (or calls another tool)
                try:
                    ai_msg = self.llm_with_tools.invoke(messages)
                except Exception as tool_error:
                    if "thought_signature" in str(tool_error) or "functionCall" in str(tool_error):
                        print(f"⚠️ Tool loop failed, falling back without tools: {tool_error}")
                        tool_loop_failed = True
                        clean_messages = [
                            m for m in messages
                            if isinstance(m, (SystemMessage, HumanMessage))
                            or (isinstance(m, AIMessage) and not getattr(m, 'tool_calls', None))
                        ]
                        ai_msg = self.llm.invoke(clean_messages)
                        break
                    else:
                        raise tool_error
            
            ai_response = ai_msg.content

            # Inject captured tool results ONLY when tool loop failed (prevents duplication on success)
            if tool_loop_failed:
                captured_tool_results = [
                    m.content for m in messages
                    if isinstance(m, ToolMessage)
                ]
                if captured_tool_results:
                    print(f"📦 Injecting {len(captured_tool_results)} captured tool results into fallback response")
                    ai_response = (ai_response or "") + " " + " ".join(captured_tool_results)

            # FAIL-SAFE: If AI returns empty content (e.g. tool loop failed or safety block), prevent "Mute"
            if not ai_response or (isinstance(ai_response, str) and not ai_response.strip()):
                 ai_response = "*(S.A.M. stares at you blankly, then taps the microphone.)* 'Is this thing on? My neural pathways jammed. Say that again?' (System Error: Empty AI Response)"
            
            # DEBUG LOGGING (Temporary)
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n[AI_RAW_RESPONSE] {ai_response}\n")

            # Handle Multimodal Content (List of blocks) - Fix for React Error {type, text, extras}
            if isinstance(ai_response, list):
                 # Extract text from blocks
                 ai_response = " ".join([block.get("text", "") for block in ai_response if isinstance(block, dict) and block.get("type") == "text"])
            elif not isinstance(ai_response, str):
                 ai_response = str(ai_response)
            
            # 4. Image Generation Trigger Check
            image_url = None
            if "<IMAGE>" in ai_response and "</IMAGE>" in ai_response:
                try:
                    start = ai_response.find("<IMAGE>") + 7
                    end = ai_response.find("</IMAGE>")
                    image_prompt = ai_response[start:end].strip()
                    
                    # Clean response (remove tag)
                    ai_response = ai_response.replace(f"<IMAGE>{image_prompt}</IMAGE>", "").strip()
                    
                    # Generate Image (Currently placeholder/mock for migration testing, or DALL-E fallback)
                    print(f"Generating Image with prompt: {image_prompt}")
                    image_url = "https://via.placeholder.com/1024x1024.png?text=Gemini+Image+Processing" 
                except Exception as e:
                    print(f"Image Gen Error: {e}")

            # 5. State Update Check (HP Sync)
            updates = None
            if "<UPDATE>" in ai_response and "</UPDATE>" in ai_response:
                try:
                    start = ai_response.find("<UPDATE>") + 8
                    end = ai_response.find("</UPDATE>")
                    update_json = ai_response[start:end].strip()
                    
                    # Remove markdown code blocks if present
                    update_json = update_json.replace("```json", "").replace("```", "").strip()
                    
                    import json
                    updates = json.loads(update_json)
                    
                    # Clean response (remove tag from user view)
                    ai_response = ai_response.replace(f"<UPDATE>{update_json}</UPDATE>", "").strip() # Use original string for replace
                    # Need to handle if we replaced markdown ticks in update_json but not in original string.
                    # Since we extract by index, we can just replace by slicing.
                    # BETTER: Construct clean response by slicing.
                    ai_response = ai_response[:start-8] + ai_response[end+9:]
                    
                    print(f"Captured State Update: {updates}")
                except Exception as e:
                    print(f"State Update Parse Error: {e}")
            
            # 6. Construct Debug Info
            debug_info = {
                "rag_context": context_text,
                "system_prompt_preview": formatted_system_prompt[:2000] + "...", # More context for debug
                "raw_response": str(ai_response)
            }
            
            return {
                "response": ai_response, 
                "image_url": image_url, 
                "updates": updates,
                "debug_info": debug_info
            }
            
        except Exception as e:
            error_str = str(e)
            # Handle Gemini Free Tier Rate Limit (Graceful Degradation)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                print("Gemini Rate Limit Hit")
                return {
                    "response": "*(S.A.M. se masajea las sienes metálicas)*\n\n'Demasiadas líneas temporales convergiendo a la vez. Mi cerebro superior necesita un breve descanso para no fundirse. Los dioses de Google reclaman su tributo de paciencia.'\n\n*(Inténtalo de nuevo en unos 30-60 segundos)*",
                    "image_url": None
                }

            # Log full traceback to file for debugging
            import traceback
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n[CHAT_CRASH] {str(e)}\n{traceback.format_exc()}\n")
            print(f"CRITICAL CHAT ERROR: {e}")
            raise e

    def parse_character_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Parses a D&D character sheet PDF using Gemini 1.5/2.0 Flash.
        Returns a JSON dictionary with character stats.
        """
        log_file = "debug_log.txt"
        def log(msg):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[PDF_IMPORT] {msg}\n")
            except:
                pass

        try:
            log("--- NEW IMPORT ATTEMPT ---")
            log(f"PDF Bytes received: {len(pdf_bytes)}")
            
            import json

            log("Model configured. Preparing prompt...")
            
            prompt = """
            Analyze this D&D 5e Character Sheet PDF (likely D&D Beyond format). 
            Extract data into the JSON structure below. If a field is empty in the PDF, use an empty string.

            CRITICAL EXTRACTION RULES:
            1. **Abilities**: Extract STR, DEX, CON, INT, WIS, CHA scores.
            2. **Status Defaults**:
               - **HP**: Extract "Max HP". For "Current HP", look for the value. CRITICAL: If "Current HP" is empty, missing, or zero, YOU MUST SET IT EQUAL TO "MAX HP". Do NOT return 0 for Current HP unless the character is dead.
               - **Initiative**: Extract the "Initiative" bonus. If the box is empty, calculate it using the DEX modifier.
            3. **Senses**: Look for "Passive Wisdom (Perception)" text. Also add any special senses (Darkvision) found in "Features & Traits".
            4. **Proficiencies & Languages**: Look for the box often labeled "Proficiencies & Languages". List ALL armor, weapons, tools, and languages.
            5. **Attacks**: Section "Attacks & Spellcasting". Extract as a LIST of objects. Structure: Name, Atk Bonus, Damage/Type.
            6. **Inventory**: Look for "Equipment" or "Gear". Extract **Money** (CP, SP, EP, GP, PP) separately. Extract remaining items as a LIST of objects: {"item": "Name", "qty": 1, "weight": "X lb"}.
            7. **Features**: "Features & Traits". Extract as a LIST of objects: {"name": "Feature Name", "source": "Source (Race/Class)", "description": "Brief summary"}.
            8. **Spells**: If present, list Spells as objects: {"name": "Spell Name", "level": "Lvl x", "notes": "School/Ritual"}.
            9. **Actions/Bonus/Reactions**: Extract "Actions", "Bonus Actions", and "Reactions" as LISTS of objects: {"name": "Action Name", "description": "Effect"}.
            10. **Bio**: "Background/Traits". Summarize into multiple paragraphs separated by "\n\n" for readability.

            CRITICAL OUTPUT RULES:
            - Output MUST be valid, parseable JSON.
            - Do NOT include comments (// or #).
            - Do NOT include trailing commas.
            - Use double quotes for strings.
            - If a value is unknown, use null or empty string, do not leave blank.

            JSON OUTPUT FORMAT:
            {
                "name": "Character Name",
                "race": "Race",
                "class": "Class (e.g. 'Rogue 3')",
                "level": 3,
                "stats": { "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10 },
                "status": {
                    "hp_max": 20, "hp_current": 20, "ac": 14, "speed": "30", "initiative": 2,
                    "proficiency_bonus": 2, "hit_dice": "3d8", "xp": 0,
                    "senses": "",
                    "languages": "",
                    "proficiencies": "",
                    "money": { "cp": 0, "sp": 0, "ep": 0, "gp": 10, "pp": 0 },
                    "actions": [{"name": "Dash", "description": "Double speed"}], 
                    "bonus_actions": [{"name": "Cunning Action", "description": "Dash/Disengage/Hide"}],
                    "reactions": [{"name": "Uncanny Dodge", "description": "Half damage"}],
                    "features": [{"name": "Sneak Attack", "source": "Rogue", "description": "Extra damage on advantage"}],
                    "attacks": [{"name": "Shortsword", "bonus": "+5", "damage": "1d6+3", "type": "Piercing"}],
                    "inventory": [{"item": "Rope", "qty": 1, "weight": "10lb"}],
                    "spells": [{
                        "name": "Firebolt", 
                        "level": "Cantrip", 
                        "school": "Evocation", 
                        "time": "1A", 
                        "range": "120ft", 
                        "duration": "Instant", 
                        "components": "V,S", 
                        "notes": "1d10 Fire" 
                    }],
                    "saving_throws": {"str": false, "dex": false, "con": false, "int": false, "wis": false, "cha": false}
                },
                "bio": "Background...\n\nTrait..."
            }
            """
            
            log("Sending request to Gemini...")
            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    prompt,
                ],
            )
            log("Response received from Gemini.")

            # Clean up response more robustly
            text = response.text
            log(f"Raw response length: {len(text)}")
            log(f"RAW START: {text[:200]}")
            
            # Robust JSON extraction: Find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start != -1 and end != -1:
                text = text[start:end]
            else:
                log("ERROR: No JSON braces found!")
                print("DEBUG: No JSON braces found in response")
            
            log("Attempting `json.loads`...")
            data = json.loads(text)
            log("JSON parsed successfully.")

            # Normalize status field names (Gemini sometimes returns hp instead of hp_current)
            if "status" in data and isinstance(data["status"], dict):
                st = data["status"]
                if "hp" in st and "hp_current" not in st:
                    st["hp_current"] = st.pop("hp")
                    log(f"Normalized: hp → hp_current = {st['hp_current']}")
                elif "hp" in st and "hp_current" in st:
                    st.pop("hp")  # Remove duplicate
                if "wallet" in st and "money" not in st:
                    st["money"] = st.pop("wallet")
                    log(f"Normalized: wallet → money")
                elif "wallet" in st and "money" in st:
                    st.pop("wallet")  # Remove duplicate

            # Auto-generate Avatar (DiceBear Adventurer)
            # Uses Name+Race+Class as seed for consistent generation without API costs
            if "name" in data:
                seed = f"{data.get('name', '')}-{data.get('race', '')}-{data.get('class', '')}".replace(" ", "")
                # Using 'adventurer' style which fits D&D perfectly
                data['image_url'] = f"https://api.dicebear.com/9.x/adventurer/svg?seed={seed}"
                log(f"Avatar generated: {data['image_url']}")
            
            return data
            
        except Exception as e:
            log(f"FATAL EXCEPTION: {str(e)}")
            print(f"PDF Parse Error: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    def generate_image(self, prompt: str) -> str:
        # TODO: Implement Gemini/Imagen 3 generation here.
        return None

# Singleton instance
sam_brain = AIHelper()
