
import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional
from app.core.access import is_gm_or_admin

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class AdminService:
    @staticmethod
    def handle_command(command_str: str, user_id: str = "gm", campaign_id: str = None) -> str:
        """
        Parses and executes admin commands.
        Returns a string response to be shown in the chat.
        campaign_id: the campaign /api/chat resolved for this message (239);
        lets /delegate accept a platform admin who is not the GM (SAM-004).
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
            elif cmd == "/delegate":
                if not args:
                    return "Usage: /delegate [character_name]"
                return AdminService.delegate_character(" ".join(args), user_id, campaign_id)
            elif cmd == "/undelegate":
                if not args:
                    return "Usage: /undelegate [character_name]"
                return AdminService.undelegate_character(" ".join(args), user_id, campaign_id)
            elif cmd == "/gold":
                if len(args) < 3:
                    return "Usage: /gold <character_name> <amount> <coin_type>\nExamples: /gold Baol -5 gp, /gold Baol Gortsh +10 sp"
                # Last arg = coin type, second-to-last = amount, rest = name
                coin_type = args[-1].lower()
                amount_str = args[-2]
                char_name = " ".join(args[:-2])
                return AdminService.adjust_gold(user_id, char_name, amount_str, coin_type)
            elif cmd == "/memory":
                if not args:
                    return "Usage: /memory [list|add <type> <text>|delete <id_or_number>]"
                sub = args[0].lower()
                if sub == "list":
                    return AdminService.memory_list(user_id)
                elif sub == "add":
                    if len(args) < 3:
                        return "Usage: /memory add <type> <text>\nValid types: fact, npc, location, plot, item, decision"
                    mem_type = args[1].lower()
                    mem_text = " ".join(args[2:])
                    return AdminService.memory_add(user_id, mem_type, mem_text)
                elif sub == "delete":
                    if len(args) < 2:
                        return "Usage: /memory delete <id_or_number>"
                    return AdminService.memory_delete(user_id, args[1])
                else:
                    return f"Unknown /memory subcommand: {sub}. Use list, add, or delete."
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
*   `/delegate [character]` - Hand control of a player character to S.A.M.
*   `/undelegate [character]` - Return character to player control.
*   `/gold <character> <±amount> <coin>` - Adjust character money. Coin: cp, sp, ep, gp, pp. Example: `/gold Baol -5 gp`.
*   `/memory list` - Show campaign memories (top 20).
*   `/memory add <type> <text>` - Add manual memory (types: fact, npc, location, plot, item, decision).
*   `/memory delete <id_or_number>` - Delete a memory (number from /memory list, or full UUID).
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
                    if status and "hp_max" in status:
                        status["hp_current"] = status["hp_max"]
                        status["money"] = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
                        status["xp"] = 0
                        supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
                        count += 1

            # 2. DELETE ALL MESSAGES — 3-pass strategy
            messages_deleted = 0

            # Pass 1: Delete by campaign_id if GM owns a campaign
            camp_res = supabase.table("campaigns").select("id").eq("gm_id", user_id).limit(1).execute()
            if camp_res.data:
                cid = camp_res.data[0]['id']
                del1 = supabase.table("messages").delete().eq("campaign_id", cid).execute()
                if del1.data:
                    messages_deleted += len(del1.data)

            # Pass 2: Delete orphan messages with NULL campaign_id (always runs)
            del2 = supabase.table("messages").delete().is_("campaign_id", "null").execute()
            if del2.data:
                messages_deleted += len(del2.data)

            # Pass 3: Nuclear fallback — if messages still remain, wipe everything
            # TODO: scope to campaign_id when multi-campaign is live
            remaining = supabase.table("messages").select("id", count="exact").execute()
            if remaining.count and remaining.count > 0:
                print(f"WARNING: {remaining.count} orphan messages found. Executing full wipe.")
                supabase.table("messages").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                messages_deleted += remaining.count

            # 3. Clear combat state
            if camp_res.data:
                cid = camp_res.data[0]['id']
                supabase.table("campaigns").update({"settings": {}}).eq("id", cid).execute()
                print("🧹 Combat state cleared")

            # 4. Clear campaign memories
            if camp_res.data:
                try:
                    supabase.table("campaign_memories").delete().eq("campaign_id", cid).execute()
                    print("🧹 Campaign memories cleared")
                except Exception as e:
                    print(f"Warning: Could not clear campaign memories: {e}")

            # 5. Broadcast CLEAR_CHAT to all clients via Realtime INSERT
            if camp_res.data:
                supabase.table("messages").insert({
                    "role": "system",
                    "content": "<ACTION>CLEAR_CHAT</ACTION><ACTION>REFRESH_CHARACTERS</ACTION>",
                    "campaign_id": cid,
                    "user_id": user_id,
                }).execute()

            return f"⚠️ Campaign Reset! {count} characters healed. {messages_deleted} messages deleted. Memories cleared. <ACTION>CLEAR_CHAT</ACTION><ACTION>REFRESH_CHARACTERS</ACTION>"

        except Exception as e:
            import traceback
            print(f"RESET ERROR: {traceback.format_exc()}")
            return f"❌ Reset Error: {e}"

    @staticmethod
    def _find_character_in_active_campaign(name: str, user_id: str, campaign_id: str = None):
        """
        Find a character by name in the campaign the caller manages.
        Instrucción 239 / SAM-004: with an explicit campaign_id the caller may
        be its GM OR a platform admin (core.access.is_gm_or_admin). Without one
        — or without rights on it — fall back to the first campaign the caller
        owns as GM (legacy behaviour).
        """
        cid = campaign_id if (campaign_id and is_gm_or_admin(user_id, campaign_id)) else None
        if not cid:
            camp_res = supabase.table("campaigns").select("id").eq("gm_id", user_id).limit(1).execute()
            if not camp_res.data:
                return None, None
            cid = camp_res.data[0]["id"]
        char_res = supabase.table("characters").select("id, name, user_id").eq("campaign_id", cid).execute()
        target_lower = name.lower()
        for c in (char_res.data or []):
            if target_lower in (c.get("name", "") or "").lower():
                return c, cid
        return None, cid

    @staticmethod
    def delegate_character(name: str, user_id: str, campaign_id: str = None) -> str:
        try:
            target_char, cid = AdminService._find_character_in_active_campaign(name, user_id, campaign_id)
            if not cid:
                return "No active campaign found for GM."
            if not target_char:
                return f"Character '{name}' not found in campaign."
            supabase.table("characters").update({"controlled_by": user_id}).eq("id", target_char["id"]).execute()
            print(f"🤖 Delegated: {target_char['name']} → SAM/GM control")
            return f"🤖 **{target_char['name']}** is now delegated to S.A.M. control. SAM will act for them in combat."
        except Exception as e:
            import traceback
            print(f"DELEGATE ERROR: {traceback.format_exc()}")
            return f"❌ Delegate Error: {e}"

    @staticmethod
    def undelegate_character(name: str, user_id: str, campaign_id: str = None) -> str:
        try:
            target_char, cid = AdminService._find_character_in_active_campaign(name, user_id, campaign_id)
            if not cid:
                return "No active campaign found for GM."
            if not target_char:
                return f"Character '{name}' not found in campaign."
            supabase.table("characters").update({"controlled_by": None}).eq("id", target_char["id"]).execute()
            print(f"✅ Undelegated: {target_char['name']} → player control")
            return f"✅ **{target_char['name']}** returned to player control."
        except Exception as e:
            import traceback
            print(f"UNDELEGATE ERROR: {traceback.format_exc()}")
            return f"❌ Undelegate Error: {e}"

    # ─────────────────────────────────────────────
    # Gold / Money Adjustment
    # ─────────────────────────────────────────────

    VALID_COIN_TYPES = ("cp", "sp", "ep", "gp", "pp")

    @staticmethod
    def adjust_gold(user_id: str, char_name: str, amount_str: str, coin_type: str) -> str:
        try:
            char_name = (char_name or "").strip()
            if not char_name:
                return "Usage: /gold <character_name> <amount> <coin_type>"

            if coin_type not in AdminService.VALID_COIN_TYPES:
                valid = ", ".join(AdminService.VALID_COIN_TYPES)
                return f"❌ Invalid coin type '{coin_type}'. Valid: {valid}"

            try:
                amount = int(amount_str)
            except (TypeError, ValueError):
                return f"❌ Amount '{amount_str}' is not a valid integer (use +N or -N)."

            target_char, cid = AdminService._find_character_in_active_campaign(char_name, user_id)
            if not cid:
                return "No active campaign found for GM."
            if not target_char:
                return f"Character '{char_name}' not found in campaign."

            # Fetch the full character to read status (the helper only returns id/name/user_id)
            full_res = supabase.table("characters").select("status").eq("id", target_char["id"]).execute()
            if not full_res.data:
                return f"❌ Could not load character data for {target_char['name']}."

            status = dict(full_res.data[0].get("status") or {})
            money = dict(status.get("money") or {})
            current = int(money.get(coin_type, 0) or 0)
            new_amount = max(0, current + amount)
            money[coin_type] = new_amount
            status["money"] = money

            supabase.table("characters").update({"status": status}).eq("id", target_char["id"]).execute()

            sign = "+" if amount >= 0 else "−"
            print(f"💰 Gold adjusted: {target_char['name']} {coin_type} {sign}{abs(amount)} → {new_amount}")
            return f"💰 **{target_char['name']}**: {coin_type} → **{new_amount}** ({sign}{abs(amount)})"
        except Exception as e:
            import traceback
            print(f"GOLD ADJUST ERROR: {traceback.format_exc()}")
            return f"❌ Gold Adjust Error: {e}"

    # ─────────────────────────────────────────────
    # Campaign Memories
    # ─────────────────────────────────────────────

    VALID_MEMORY_TYPES = ("fact", "npc", "location", "plot", "item", "decision")

    @staticmethod
    def _get_active_campaign_id(user_id: str):
        """Resolve the active campaign id for a GM user. Returns uuid or None."""
        camp_res = supabase.table("campaigns").select("id").eq("gm_id", user_id).limit(1).execute()
        if camp_res.data:
            return camp_res.data[0]["id"]
        return None

    @staticmethod
    def _fetch_memories(cid: str, limit: int = 20):
        """Fetch top memories ordered by importance then recency."""
        return (
            supabase.table("campaign_memories")
            .select("id, content, type, importance, created_at, source")
            .eq("campaign_id", cid)
            .order("importance", desc=True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    @staticmethod
    def memory_list(user_id: str) -> str:
        try:
            cid = AdminService._get_active_campaign_id(user_id)
            if not cid:
                return "No active campaign found for GM."
            res = AdminService._fetch_memories(cid, limit=20)
            if not res.data:
                return "📭 No memories yet for this campaign."

            lines = ["**🧠 Campaign Memories (top 20):**"]
            for idx, m in enumerate(res.data, start=1):
                mtype = (m.get("type") or "fact").upper()
                imp = m.get("importance", 5)
                content = m.get("content", "")
                lines.append(f"#{idx} [{mtype}] (imp:{imp}) {content}")
            return "\n".join(lines)
        except Exception as e:
            import traceback
            print(f"MEMORY LIST ERROR: {traceback.format_exc()}")
            return f"❌ Memory List Error: {e}"

    @staticmethod
    def memory_add(user_id: str, mem_type: str, text: str) -> str:
        try:
            if mem_type not in AdminService.VALID_MEMORY_TYPES:
                valid = ", ".join(AdminService.VALID_MEMORY_TYPES)
                return f"❌ Invalid type '{mem_type}'. Valid types: {valid}"

            text = text.strip()
            if not text:
                return "❌ Memory text cannot be empty."

            cid = AdminService._get_active_campaign_id(user_id)
            if not cid:
                return "No active campaign found for GM."

            supabase.table("campaign_memories").insert({
                "campaign_id": cid,
                "content": text,
                "type": mem_type,
                "importance": 7,
                "source": "manual",
                "created_by": user_id,
            }).execute()

            print(f"🧠 Manual memory added by GM: [{mem_type.upper()}] {text[:60]}")
            return f"✅ Memory added: **[{mem_type.upper()}]** {text}"
        except Exception as e:
            import traceback
            print(f"MEMORY ADD ERROR: {traceback.format_exc()}")
            return f"❌ Memory Add Error: {e}"

    @staticmethod
    def memory_delete(user_id: str, id_or_number: str) -> str:
        try:
            cid = AdminService._get_active_campaign_id(user_id)
            if not cid:
                return "No active campaign found for GM."

            target_id = None

            # If it looks like a small number, treat as #N from /memory list
            if id_or_number.lstrip("#").isdigit():
                n = int(id_or_number.lstrip("#"))
                if n < 1:
                    return "❌ Number must be 1 or higher."
                res = AdminService._fetch_memories(cid, limit=20)
                if not res.data or n > len(res.data):
                    return f"❌ No memory at position #{n} (only {len(res.data) if res.data else 0} memories)."
                target_id = res.data[n - 1]["id"]
            else:
                # Treat as UUID
                target_id = id_or_number.strip()

            del_res = (
                supabase.table("campaign_memories")
                .delete()
                .eq("id", target_id)
                .eq("campaign_id", cid)
                .execute()
            )
            if not del_res.data:
                return f"❌ No memory found with id `{target_id}` in this campaign."

            print(f"🗑️ Memory deleted: {target_id}")
            return f"✅ Memory deleted (`{target_id[:8]}...`)."
        except Exception as e:
            import traceback
            print(f"MEMORY DELETE ERROR: {traceback.format_exc()}")
            return f"❌ Memory Delete Error: {e}"

