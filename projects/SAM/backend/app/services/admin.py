
import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class AdminService:
    @staticmethod
    def handle_command(command_str: str, user_id: str = "gm") -> str:
        """
        Parses and executes admin commands.
        Returns a string response to be shown in the chat.
        """
        try:
            import time
            parts = command_str.strip().split()
            if not parts:
                return "Empty command."

            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == "/help":
                return AdminService.help_command()
            elif cmd == "/reset":
                return AdminService.reset_campaign(user_id)
            elif cmd == "/checkpoint":
                # Auto-name if not provided
                name = " ".join(args) if args else f"autosave_{int(time.time())}"
                return AdminService.create_checkpoint(name, user_id)
            elif cmd == "/load":
                if not args:
                    return "Usage: /load [name]"
                return AdminService.load_checkpoint(" ".join(args), user_id)
            elif cmd == "/list":
                return AdminService.list_checkpoints()
            else:
                return f"Unknown command: {cmd}. Type /help for list."
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"ADMIN ERROR: {trace}")
            return f"❌ CRITICAL ERROR in AdminService: {str(e)}"

    @staticmethod
    def help_command() -> str:
        return """
**⚔️ Admin Command Center ⚔️**

*   `/checkpoint [name]` - Save current state (Chat + Stats).
*   `/load [name]` - Restore a saved state (Wipes current chat).
*   `/reset` - Wipe chat history & Restore HP.
*   `/list` - Show all checkpoints.
*   `/help` - Show this menu.
"""

    @staticmethod
    def list_checkpoints() -> str:
        try:
            res = supabase.table("checkpoints").select("name, created_at").order("created_at", desc=True).execute()
            if not res.data:
                return "No checkpoints found."
            
            lines = ["**Saved Checkpoints:**"]
            for cp in res.data:
                lines.append(f"- **{cp['name']}** ({cp['created_at'][:16]})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing checkpoints: {e}"

    @staticmethod
    def create_checkpoint(name: str, user_id: str) -> str:
        try:
            # 1. Characters
            chars = supabase.table("characters").select("*").execute()
            
            # 2. Chat History
            chat = supabase.table("messages").select("*").eq("user_id", user_id).order("created_at").execute()
            
            data = {
                "name": name,
                "character_states": chars.data if chars.data else [],
                "chat_history": chat.data if chat.data else [], 
                "notes": "Full State Save via Admin Console"
            }
            
            # Upsert checkpoint (name is unique)
            supabase.table("checkpoints").upsert(data, on_conflict="name").execute()
            return f"✅ Checkpoint '**{name}**' saved (Chars + Chat)."
            
        except Exception as e:
            return f"❌ Error creating checkpoint: {e}"

    @staticmethod
    def load_checkpoint(name: str, user_id: str) -> str:
        try:
            # 1. Fetch Checkpoint
            res = supabase.table("checkpoints").select("*").eq("name", name).execute()
            if not res.data:
                return f"Checkpoint '{name}' not found."
            
            cp = res.data[0]
            
            # 2. Restore Characters
            saved_chars = cp.get("character_states", [])
            count_chars = 0
            if isinstance(saved_chars, list):
                for char in saved_chars:
                    # Upsert each char to restore stats/inventory
                    # Security: This overwrites current state with old state.
                    if "id" in char:
                        supabase.table("characters").upsert(char).execute()
                        count_chars += 1
            
            # 3. Restore Chat History
            saved_chat = cp.get("chat_history", [])
            count_msgs = 0
            if isinstance(saved_chat, list) and saved_chat:
                # Wipe current history for this user
                supabase.table("messages").delete().eq("user_id", user_id).execute()
                # Restore old history
                supabase.table("messages").insert(saved_chat).execute()
                count_msgs = len(saved_chat)

            return f"🔄 Loaded '**{name}**'. Restored {count_msgs} msgs & {count_chars} chars. <ACTION>REFRESH_CHARACTERS</ACTION><ACTION>RELOAD_CHAT</ACTION>"
            
        except Exception as e:
            return f"❌ Error loading checkpoint: {e}"

    @staticmethod
    def reset_campaign(user_id: str) -> str:
        try:
            # 1. Reset Character Health
            res = supabase.table("characters").select("*").execute()
            count = 0
            if res.data:
                for char in res.data:
                    status = char.get("status", {})
                    # Only reset if we know max HP
                    if status and "hp_max" in status:
                        status["hp_current"] = status["hp_max"]
                        # Optional: Reset other things like "conditions"?
                        # status["conditions"] = [] 
                        
                        # Reset Money
                        status["money"] = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
                        status["xp"] = 0
                        
                        # Update DB
                        supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
                        count += 1
            
            # 2. DELETE CHAT HISTORY from Database
            # STRATEGY: Delete by Campaign ID (clears all players), then fallback to User ID (clears orphans)
            
            # Find Campaign ID owned by this User (GM)
            camp_res = supabase.table("campaigns").select("id").eq("gm_id", user_id).limit(1).execute()
            
            messages_deleted = 0
            
            if camp_res.data:
                cid = camp_res.data[0]['id']
                print(f"DEBUG: Resetting Campaign ID: {cid}")
                
                # 1. Delete by Campaign ID (The Happy Path)
                del_camp = supabase.table("messages").delete().eq("campaign_id", cid).execute()
                if del_camp.data:
                    messages_deleted += len(del_camp.data)
                    print(f"DEBUG: Deleted {len(del_camp.data)} campaign messages.")

                # 2. Deep Clean 1: Delete by User IDs of players currently in this campaign
                try:
                    players = supabase.table("characters").select("user_id").eq("campaign_id", cid).execute()
                    if players.data:
                        player_ids = [p['user_id'] for p in players.data if p.get('user_id')]
                        if user_id and user_id not in player_ids:
                            player_ids.append(user_id)
                        
                        if player_ids:
                             del_players = supabase.table("messages").delete().in_("user_id", player_ids).execute()
                             if del_players.data:
                                 messages_deleted += len(del_players.data)
                except Exception as deep_err:
                    print(f"WARNING: Deep clean 1 failed: {deep_err}")
                
                # 3. Deep Clean 2: Wipe any message with NULL campaign_id (legacy orphans from multiplayer testing)
                try:
                     del_nulls = supabase.table("messages").delete().is_("campaign_id", "null").execute()
                     if del_nulls.data:
                         messages_deleted += len(del_nulls.data)
                         print(f"DEBUG: Cleaned {len(del_nulls.data)} NULL campaign_id messages.")
                except Exception as null_err:
                     print(f"WARNING: NULL cleanup failed: {null_err}")

            # Fallback / Cleanup 4: Delete messages owned by this user explicitly
            if user_id:
                try:
                    del_user = supabase.table("messages").delete().eq("user_id", user_id).execute()
                    if del_user.data:
                         messages_deleted += len(del_user.data)
                except Exception as del_err:
                     print(f"WARNING: Cleanup user history failed: {del_err}")

            # 3. Clear Chat (Frontend Action) & Refresh Data
            return f"⚠️ Campaign Reset! Chat History DB Cleared. {count} Characters fully healed. <ACTION>CLEAR_CHAT</ACTION><ACTION>REFRESH_CHARACTERS</ACTION>"
        except Exception as e:
            return f"❌ Reset Error: {e}"

