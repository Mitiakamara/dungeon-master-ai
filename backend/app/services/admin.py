
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
                if not args:
                    return "Usage: /checkpoint [name]"
                return AdminService.create_checkpoint(" ".join(args))
            elif cmd == "/load":
                if not args:
                    return "Usage: /load [name]"
                return AdminService.load_checkpoint(" ".join(args))
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

*   `/checkpoint [name]` - Save current state manually.
*   `/load [name]` - Restore a saved state.
*   `/reset` - Wipe chat history & Restore HP.
*   `/list` - Show all checkpoints.
*   `/help` - Show this menu.

*Note: Checkpoints save Chat History + All Character Statuses.*
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
    def create_checkpoint(name: str) -> str:
        try:
            # Retrieving all characters
            chars = supabase.table("characters").select("*").execute()
            
            data = {
                "name": name,
                "character_states": chars.data if chars.data else [],
                "notes": "Manual Save via Admin Console"
            }
            
            # Upsert checkpoint (name is unique)
            supabase.table("checkpoints").upsert(data, on_conflict="name").execute()
            return f"✅ Checkpoint '**{name}**' saved successfully."
            
        except Exception as e:
            return f"❌ Error creating checkpoint: {e}"

    @staticmethod
    def load_checkpoint(name: str) -> str:
        try:
            # 1. Fetch Checkpoint
            res = supabase.table("checkpoints").select("*").eq("name", name).execute()
            if not res.data:
                return f"Checkpoint '{name}' not found."
            
            cp = res.data[0]
            
            # 2. Restore Characters
            saved_chars = cp.get("character_states", [])
            count = 0
            if isinstance(saved_chars, list):
                for char in saved_chars:
                    # Upsert each char to restore stats/inventory
                    # Security: This overwrites current state with old state.
                    if "id" in char:
                        supabase.table("characters").upsert(char).execute()
                        count += 1
            
            return f"🔄 Loaded checkpoint '**{name}**'. Restored {count} characters. <ACTION>REFRESH_CHARACTERS</ACTION>"
            
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
                        
                        # Update DB
                        supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
                        count += 1
            
            # 2. DELETE CHAT HISTORY from Database
            # We delete all messages where user_id matches the GM/User
            # (In a real app, this might be campaign_id scoped)
            if user_id:
                try:
                    supabase.table("messages").delete().eq("user_id", user_id).execute()
                except Exception as del_err:
                     print(f"Warning: Failed to delete user messages: {del_err}")

            # 3. Clear Chat (Frontend Action) & Refresh Data
            return f"⚠️ Campaign Reset! Chat History DB Cleared. {count} Characters fully healed. <ACTION>CLEAR_CHAT</ACTION><ACTION>REFRESH_CHARACTERS</ACTION>"
        except Exception as e:
            return f"❌ Reset Error: {e}"

