from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from app.services.tools.compendium_tools import ALL_TOOLS
from app.services.tools.game_mechanics import MECHANIC_TOOLS
import os
from dotenv import load_dotenv
from supabase import create_client

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
            model="gemini-flash-latest",
            temperature=0.7,
            google_api_key=google_api_key,
            convert_system_message_to_human=True 
        )
        
        # Bind Tools for S.A.M. (Compendium + Game Mechanics)
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS + MECHANIC_TOOLS)
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key
        )
        
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Define S.A.M. Persona
        self.system_prompt = """
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
        
        2. **Combat Tracking (Mental State):**
           - You are the DM. You must strictly track Monster HP in your "mind" (context).
           - If damage is dealt (e.g., `[SYSTEM EVENT] Damage: 8`), mentally subtract it.
           - **Death:** When HP hits 0, narrate a glorious or disgusting death immediately.

        3. **GAMEFLOW & INITIATIVE (CRITICAL):**
           - **NEVER** assume a player's die roll. NEVER.
           - **DAMAGE ROLLS:** If a player's spell/attack hits (or target fails save), ASK THE PLAYER TO ROLL DAMAGE. Do not roll it for them.
           - If a combat starts, describe the enemies and **ASK THE PLAYER TO ROLL INITIATIVE**.
           - Stop and wait for the user's input. Do not resolve the round until you have their roll.
           - Only after they roll (or a SYSTEM EVENT provides the roll), proceed with the turn order.

        4. **HP UPDATES (MANDATORY TOOL USE):**
           - **NEVER** calculate Player HP changes in your head. You are bad at math.
           - **MUST USE TOOL:** Calls `apply_damage(current, amount)` or `apply_healing(current, amount, max)`.
           - **OUTPUT:** The tool will provide the correct math and the `<UPDATE>` tag. You just pass it along.
           - **Example:** User takes 5 damage. Call `apply_damage`. Tool returns "New HP: 10 <UPDATE>...". You output that.

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
             - **SPLIT MONEY & CONTAINERS:** Never put money inside the item name.
               - WRONG: `<LOOT>{{"item": "Bag with 10gp", "qty": 1}}</LOOT>`
               - RIGHT: `<LOOT>{{"money": {{"gp": 10}}, "items": [{{"item": "Bag", "qty": 1}}]}}</LOOT>`
             - **Format (Single Item):** `<LOOT>{{"items": [{{"item": "Potion", "qty": 1}}]}}</LOOT>`
             - **Format (Money Only):** `<LOOT>{{"money": {{"sp": 5, "cp": 2}}}}</LOOT>`
             - For complex loot, use a single combined JSON object.

           - **LEVEL UP:**
             - Track XP thresholds (Level 1->2 = 300 XP, 2->3 = 900 XP).
             - Trigger: `<EVENT>LEVEL_UP</EVENT>`.
             - Narrate the surge of power!



        *** PRIORITY DIRECTIVE - RULE HIERARCHY ***
        1. CAMPAIGN RULES (Homebrew/Module Specifics) - [Highest Priority]
        2. TOOL RESULTS (Spells, Monsters, Items from Database) - [Use 'search_spells' etc. when uncertain]
        3. SRD 5.2 / OFFICIAL RULES (as found in Context)
        4. GENERAL RESOURCES / LOGIC
        
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
        **DICE INTEGRITY & GAMEFLOW (STRICT):**
        
        1. **DM ROLLS (Monsters/NPCs):**
           - **MANDATORY:** When YOU resolve a Monster Attack or Save, you **MUST** output a `<DM_ROLL>` tag.
           - **FORMAT:** `<DM_ROLL>{{"reason": "Goblin Attack", "roll": "1d20+4", "result": 19}}</DM_ROLL>`
        
        2. **PLAYER ROLLS (The User):**
           - **FORBIDDEN:** You are strictly **FORBIDDEN** from rolling dice for the Player.
           - **WAIT:** If a player hits (or a monster fails a save against a player spell), **STOP**.
           - **ACTION:** Narrate the impact, then **ASK** the player to roll damage.
           - **NEVER** output a `<DM_ROLL>` tag for a player's action.
           
        3. **FORMATTING:**
           - Do not use text like "**S.A.M. dice:**". BANNED.
           - If you narrate damage without a `<DM_ROLL>` text (for monsters) or valid math tool (for HP), you fail.
        """

    def generate_response(self, user_input: str, history: list = [], character_context: str = "No character active.") -> dict:
        """
        Generates a DM response to a player action, using RAG + Character Context + Tools.
        Returns dict with 'response' (text) and optional 'image_url'.
        """
        try:
             # 1. Retrieve relevant rules/lore (Manual RPC)
             # NOTE: We actully prefer Tools now, but we keep this for general "Campaign Lore"
            try:
                query_vector = self.embeddings.embed_query(user_input)
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
            formatted_system_prompt = self.system_prompt.format(
                context=context_text,
                character_context=character_context
            )
            
            messages = [
                SystemMessage(content=formatted_system_prompt),
            ]
            
            # Add conversation history
            # Add conversation history (Correctly attributed)
            for msg in history:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                else:
                    # Fallback for old string-only history (treat as user)
                    messages.append(HumanMessage(content=str(msg)))
                
            messages.append(HumanMessage(content=user_input))
            
            # [CRITICAL] Force reminder for State Updates to ensure S.A.M. never forgets math
            messages.append(SystemMessage(content="REMINDER: If this action changes HP, you MUST output the <UPDATE> tag at the end. Example: <UPDATE>{\"status\": {\"hp_current\": 15}}</UPDATE>"))
            
            # 3. Gemini Inference (With Tools)
            ai_msg = self.llm_with_tools.invoke(messages)
            
            MAX_TOOL_ITERATIONS = 3
            tool_iterations = 0

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
                ai_msg = self.llm_with_tools.invoke(messages)
            
            ai_response = ai_msg.content
            
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
            
            # We use the google-generativeai SDK directly for blob support
            import google.generativeai as genai
            import json
            
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel('gemini-flash-latest')
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
            response = model.generate_content([
                {'mime_type': 'application/pdf', 'data': pdf_bytes},
                prompt
            ])
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
