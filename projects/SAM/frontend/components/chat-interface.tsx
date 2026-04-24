"use client"

import * as React from "react"
import { Send, Brain } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { createClient } from "@/lib/supabase/client"
import { authenticatedFetch } from "@/lib/api"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useRealtime } from "@/hooks/use-realtime"
import { useTypingIndicator } from "@/hooks/use-typing-indicator"

// Helper: Attempt to repair truncated JSON from malformed AI tags
function repairJson(str: string): string {
    str = str.replace(/```json/g, '').replace(/```/g, '').trim()
    let braces = 0, brackets = 0, inString = false, escape = false
    for (const ch of str) {
        if (escape) { escape = false; continue }
        if (ch === '\\') { escape = true; continue }
        if (ch === '"') { inString = !inString; continue }
        if (inString) continue
        if (ch === '{') braces++
        if (ch === '}') braces--
        if (ch === '[') brackets++
        if (ch === ']') brackets--
    }
    if (inString) str += '"'
    while (brackets > 0) { str += ']'; brackets-- }
    while (braces > 0) { str += '}'; braces-- }
    return str
}

// Strip machine-readable tags from message content for clean display
function stripSystemTags(content: string, role: string = 'assistant'): string {
    let cleaned = content
        // XML system tags
        .replace(/<LOOT>[\s\S]*?<\/LOOT>/g, '')
        .replace(/<UPDATE>[\s\S]*?<\/UPDATE>/g, '')
        .replace(/<XP_GAIN>[\s\S]*?<\/XP_GAIN>/g, '')
        .replace(/<EVENT>[\s\S]*?<\/EVENT>/g, '')
        .replace(/<ACTION>[\s\S]*?<\/ACTION>/g, '')
        .replace(/<IMAGE>[\s\S]*?<\/IMAGE>/g, '')
        .replace(/<COMBAT>[\s\S]*?<\/COMBAT>/g, '')
        .replace(/<\/?LOOT>/g, '')
        .replace(/<\/?UPDATE>/g, '')
        .replace(/<\/?COMBAT>/g, '')
    // Only strip Gemini artifacts from SAM's responses, not player messages
    if (role === 'assistant') {
        cleaned = cleaned.replace(/Calculation:\s*-?\d+[\s]*[-+*/][\s]*-?\d+[\s]*=[\s]*-?\d+\.?/gi, '')
        cleaned = cleaned.replace(/No matching (monsters|spells|items) found\.?/gi, '')
        cleaned = cleaned.replace(/apply_damage\([^)]*\)/gi, '')
        cleaned = cleaned.replace(/apply_healing\([^)]*\)/gi, '')
        cleaned = cleaned.replace(/give_loot\([^)]*\)/gi, '')
        cleaned = cleaned.replace(/search_(spells|monsters|items)\([^)]*\)/gi, '')
        cleaned = cleaned.replace(/\[SYSTEM EVENT\][^\n]*/gi, '')
    }
    // Clean excess whitespace
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
    return cleaned.trim()
}

interface Message {
    id?: string
    role: "user" | "assistant" | "system"
    content: string
    imageUrl?: string
    debugInfo?: any
    timestamp: Date
    senderId?: string | null
    senderName?: string
}

export function ChatInterface({
    selectedCharacter,
    campaignId,
    campaignName,
    isGM,
    combatState,
    externalEvent,
    onEventHandled,
    onCharacterUpdate,
    onSamMessageReceived
}: {
    selectedCharacter: any,
    campaignId?: string,
    campaignName?: string,
    isGM?: boolean,
    combatState?: any,
    externalEvent?: string | null,
    onEventHandled?: () => void,
    onCharacterUpdate?: (updates: any) => void,
    onSamMessageReceived?: () => void
}) {
    const [messages, setMessages] = React.useState<Message[]>([])
    const [input, setInput] = React.useState("")
    const [isLoading, setIsLoading] = React.useState(false)
    const [currentUserId, setCurrentUserId] = React.useState<string | null>(null)
    const bottomRef = React.useRef<HTMLDivElement>(null)

    // Typing indicator (Supabase Broadcast)
    const { typingNames, sendTyping } = useTypingIndicator(campaignId || null, selectedCharacter?.name || null)

    // Combat turn logic
    const characterName = selectedCharacter?.name || null
    const isInCombat = combatState?.active === true
    const currentTurnEntry = combatState?.initiative_order?.find(
        (e: any) => e.name === combatState.current_turn
    )
    const isNpcTurn = currentTurnEntry?.is_npc === true
    const isMyTurn = !isInCombat || isNpcTurn || combatState?.current_turn === characterName
    const turnMessage = isInCombat && !isMyTurn ? `${combatState.current_turn}'s turn` : null

    // Tab notification state
    const unreadCountRef = React.useRef(0)
    const originalTitleRef = React.useRef('S.A.M. — AI Dungeon Master')
    const prevMessageCountRef = React.useRef(0)

    const playNotificationSound = React.useCallback(() => {
        try {
            const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
            const oscillator = audioCtx.createOscillator()
            const gainNode = audioCtx.createGain()
            oscillator.connect(gainNode)
            gainNode.connect(audioCtx.destination)
            oscillator.frequency.value = 587.33
            oscillator.type = 'sine'
            gainNode.gain.value = 0.1
            oscillator.start()
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3)
            oscillator.stop(audioCtx.currentTime + 0.3)
        } catch {}
    }, [])

    // Notify on new messages when tab is hidden
    React.useEffect(() => {
        if (messages.length <= prevMessageCountRef.current) {
            prevMessageCountRef.current = messages.length
            return
        }
        prevMessageCountRef.current = messages.length

        if (document.visibilityState === 'hidden') {
            const lastMessage = messages[messages.length - 1]
            if (lastMessage && (lastMessage.role === 'assistant' || (lastMessage.senderId && lastMessage.senderId !== currentUserId))) {
                unreadCountRef.current += 1
                document.title = `(${unreadCountRef.current}) ⚔️ S.A.M. — New activity!`
                playNotificationSound()
            }
        }
    }, [messages, currentUserId, playNotificationSound])

    // Combat turn notification
    React.useEffect(() => {
        if (combatState?.active && combatState?.current_turn === characterName && document.visibilityState === 'hidden') {
            document.title = '🎯 YOUR TURN! — S.A.M.'
            playNotificationSound()
            setTimeout(playNotificationSound, 300)
        }
    }, [combatState?.current_turn, characterName, combatState?.active, playNotificationSound])

    // Reset title when tab becomes visible
    React.useEffect(() => {
        const handleVisibility = () => {
            if (document.visibilityState === 'visible') {
                unreadCountRef.current = 0
                document.title = originalTitleRef.current
            }
        }
        document.addEventListener('visibilitychange', handleVisibility)
        return () => document.removeEventListener('visibilitychange', handleVisibility)
    }, [])

    // Debug Inspector State
    const [debugOpen, setDebugOpen] = React.useState(false)
    const [currentDebugInfo, setCurrentDebugInfo] = React.useState<any>(null)

    // Get current user ID on mount
    React.useEffect(() => {
        const supabase = createClient()
        supabase.auth.getUser().then(({ data: { user } }: { data: { user: any } }) => {
            if (user) setCurrentUserId(user.id)
        })
    }, [])

    // [PHASE 13] REALTIME SUBSCRIPTION — filtered by campaign
    useRealtime({
        table: 'messages',
        event: '*',
        filter: campaignId ? `campaign_id=eq.${campaignId}` : undefined,
        enabled: !!campaignId,
        onData: (newItem: any) => {

            // Handle DELETE (Reset)
            if (newItem.eventType === 'DELETE') {
                console.log("🗑️ Realtime Delete Event:", newItem)
                setMessages([]);
                return;
            }

            // Handle INSERT (Normal Chat)
            if (newItem.eventType === 'INSERT' && newItem.new) {
                const payload = newItem.new

                // SAM responses (role 'assistant') may have applied state_updates server-side
                // (spell_slots, inventory, hp, money). Tell the parent to re-fetch the character.
                if (payload.role === 'assistant' && onSamMessageReceived) {
                    console.log('🔄 SAM message received → triggering character re-fetch')
                    onSamMessageReceived()
                }

                const incomingMsg: Message = {
                    id: payload.id,
                    role: payload.role as "user" | "assistant" | "system",
                    content: payload.content,
                    imageUrl: payload.image_url,
                    timestamp: new Date(payload.created_at),
                    senderId: payload.sender_id || null,
                    senderName: payload.metadata?.character_name || "Player",
                }

                // ---------------------------------------------------------
                // [FIX] State Accumulation to prevent Race Conditions
                // ---------------------------------------------------------
                // We must perform all logic on a local copy of the status, then send 1 atomic update.
                const rawStatus = selectedCharacter?.status || {};

                // Deep Copy mutable fields
                // [FIX] Lazy Migration: wallet -> money
                // If backend sent 'wallet' (legacy), use it if 'money' is empty.
                const legacyWallet = rawStatus.wallet || { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
                const newMoney = rawStatus.money || { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };

                // If money is all zeros/empty, but legacyWallet has coins, perform migration
                const hasMoney = Object.values(newMoney).some(v => typeof v === 'number' && v > 0);
                const hasLegacy = Object.values(legacyWallet).some(v => typeof v === 'number' && v > 0);

                const finalMoney = (!hasMoney && hasLegacy) ? { ...legacyWallet } : { ...newMoney };

                let localStatus: any = {
                    ...rawStatus,
                    money: finalMoney,
                    inventory: Array.isArray(rawStatus.inventory) ? [...rawStatus.inventory] : [],
                    // Copy other fields as needed (hp_current, etc handled by update tag)
                };
                let hasStateChanges = false;

                let displayContent = incomingMsg.content;

                // 1. Check for <UPDATE> (Generic Stats like HP)
                const updateRegex = /<UPDATE>([\s\S]*?)<\/UPDATE>/;
                const updateMatch = displayContent.match(updateRegex);

                if (updateMatch && updateMatch[1]) {
                    try {
                        const updateData = JSON.parse(updateMatch[1]);
                        console.log("⚡ Auto-Applying State Update:", updateData);

                        // Merge status updates into localStatus
                        if (updateData.status) {
                            localStatus = { ...localStatus, ...updateData.status };
                            hasStateChanges = true;
                        } else {
                            // If updateData is NOT wrapped in status
                            localStatus = { ...localStatus, ...updateData };
                            hasStateChanges = true;
                        }

                        displayContent = displayContent.replace(updateMatch[0], "").trim();
                    } catch (e) {
                        console.error("Failed to parse Update Tag:", e);
                    }
                }

                // 2. Parse LOOT (Wallet & Inventory)
                displayContent = displayContent.replace(/<LOOT>([\s\S]*?)<\/LOOT>/g, (match, jsonStr) => {
                    try {
                        const lootData = JSON.parse(jsonStr);
                        console.log("💰 Processing Loot Data:", lootData);

                        const displayParts: string[] = [];

                        // [FIX] Support Complex Loot (Money + Items) & Legacy
                        // Case A: New Format { money: {...}, items: [...] }
                        if (lootData.money || lootData.items) {
                            // 1. Money
                            if (lootData.money) {
                                ['cp', 'sp', 'ep', 'gp', 'pp'].forEach(currency => {
                                    if (lootData.money[currency]) {
                                        localStatus.money[currency as keyof typeof localStatus.money] =
                                            (localStatus.money[currency as keyof typeof localStatus.money] || 0) + lootData.money[currency];
                                        displayParts.push(`${lootData.money[currency]} ${currency.toUpperCase()}`);
                                    }
                                });
                            }
                            // 2. Items
                            if (lootData.items && Array.isArray(lootData.items)) {
                                lootData.items.filter((itemObj: any) => itemObj.item).forEach((itemObj: any) => {
                                    localStatus.inventory.push({
                                        item: itemObj.item,
                                        qty: itemObj.qty || 1,
                                        weight: itemObj.weight || 0,
                                        notes: "Looted"
                                    });
                                    displayParts.push(`${itemObj.qty || 1}x ${itemObj.item}`);
                                });
                            }
                        }
                        // Case B: Legacy Format (Array of items or single item object)
                        else {
                            const lootItems = Array.isArray(lootData) ? lootData : [lootData];

                            lootItems.forEach((loot: any) => {
                                const qty = loot.qty || 1;
                                const itemDisplay = `${qty}x ${loot.item}`;
                                const lowerItem = (loot.item || "").toLowerCase();
                                let isCurrency = false;

                                // Legacy Currency Logic (Parsing Name)
                                if (lowerItem.includes("cobre") || lowerItem.includes("copper") || lowerItem === "cp") {
                                    localStatus.wallet.cp = (localStatus.wallet.cp || 0) + qty;
                                    isCurrency = true;
                                    displayParts.push(`${qty} CP`);
                                } else if (lowerItem.includes("plata") || lowerItem.includes("silver") || lowerItem === "sp") {
                                    localStatus.wallet.sp = (localStatus.wallet.sp || 0) + qty;
                                    isCurrency = true;
                                    displayParts.push(`${qty} SP`);
                                } else if (lowerItem.includes("oro") || lowerItem.includes("gold") || lowerItem === "gp") {
                                    localStatus.wallet.gp = (localStatus.wallet.gp || 0) + qty;
                                    isCurrency = true;
                                    displayParts.push(`${qty} GP`);
                                }

                                // Inventory Logic
                                if (!isCurrency) {
                                    localStatus.inventory.push({
                                        item: loot.item,
                                        qty: qty,
                                        weight: loot.weight || 0,
                                        notes: "Looted"
                                    });
                                    displayParts.push(itemDisplay);
                                }
                            });
                        }

                        hasStateChanges = true;

                        if (displayParts.length > 0) {
                            toast.success(`🎁 Loot Found: ${displayParts.join(", ")}`, {
                                duration: 4000,
                                className: "bg-green-600 text-white border-none"
                            });
                        }
                        return "";
                    } catch (e) {
                        console.error("Loot Parse Error:", e);
                        return "";
                    }
                });

                // 2b. Fallback: Recover orphaned </LOOT> (AI dropped opening tag)
                while (displayContent.includes('</LOOT>')) {
                    const closingIdx = displayContent.indexOf('</LOOT>')
                    const beforeClose = displayContent.substring(0, closingIdx)
                    const jsonStart = beforeClose.lastIndexOf('{')
                    if (jsonStart !== -1) {
                        let jsonStr = beforeClose.substring(jsonStart)
                        try {
                            jsonStr = repairJson(jsonStr)
                            const lootData = JSON.parse(jsonStr)
                            console.log("🔧 Recovered orphan LOOT:", lootData)
                            if (lootData.money || lootData.items) {
                                if (lootData.money) {
                                    (['cp', 'sp', 'ep', 'gp', 'pp'] as const).forEach(currency => {
                                        if (lootData.money[currency]) {
                                            localStatus.money[currency] =
                                                (localStatus.money[currency] || 0) + lootData.money[currency]
                                        }
                                    })
                                }
                                if (lootData.items && Array.isArray(lootData.items)) {
                                    lootData.items.filter((itemObj: any) => itemObj.item).forEach((itemObj: any) => {
                                        localStatus.inventory.push({
                                            item: itemObj.item,
                                            qty: itemObj.qty || 1,
                                            weight: itemObj.weight || 0,
                                            notes: "Looted"
                                        })
                                    })
                                }
                                hasStateChanges = true
                                toast.success("🎁 Loot Recovered!", { duration: 3000 })
                            }
                            displayContent = displayContent.substring(0, jsonStart) + displayContent.substring(closingIdx + 7)
                        } catch (e) {
                            console.warn("Orphan LOOT recovery failed:", e)
                            displayContent = displayContent.replace('</LOOT>', '')
                        }
                    } else {
                        displayContent = displayContent.replace('</LOOT>', '')
                    }
                }

                // 2c. Clean any remaining stray LOOT tags
                displayContent = displayContent.replace(/<\/?LOOT>/g, '')

                displayContent = displayContent.trim();

                // 3. Parse XP
                const xpRegex = /<XP_GAIN>(.*?)<\/XP_GAIN>/g;
                let xpMatch;
                while ((xpMatch = xpRegex.exec(displayContent)) !== null) {
                    const xpAmount = parseInt(xpMatch[1]);
                    if (!isNaN(xpAmount)) {
                        localStatus.xp = (localStatus.xp || 0) + xpAmount;
                        hasStateChanges = true;
                        toast.info(`✨ +${xpAmount} XP`);
                    }
                    displayContent = displayContent.replace(xpMatch[0], "").trim();
                }

                // 4. Handle Level Up
                if (displayContent.includes("<EVENT>LEVEL_UP</EVENT>")) {
                    toast.warning("🆙 LEVEL UP! YOU FEEL UNSTOPPABLE!", {
                        duration: 5000,
                        className: "bg-yellow-500 text-black font-bold text-lg"
                    });
                    displayContent = displayContent.replace("<EVENT>LEVEL_UP</EVENT>", "").trim();
                }

                if (!displayContent.trim() && (hasStateChanges || updateMatch)) {
                    // Fallback if AI only sent an update tag and no text (rare, but happens)
                    displayContent = "*(S.A.M. te mira fijamente mientras las leyes de la física se reajustan...)*";
                }

                // [FIX] Handling <ACTION>CLEAR_CHAT</ACTION> from Realtime
                if (displayContent.includes("<ACTION>CLEAR_CHAT</ACTION>")) {
                    console.log("🧹 Received Global Clear Command via Realtime");
                    setMessages([]);
                    return;
                }

                if (displayContent.includes("<ACTION>REFRESH_CHARACTERS</ACTION>")) {
                    displayContent = displayContent.replace("<ACTION>REFRESH_CHARACTERS</ACTION>", "").trim();
                    setTimeout(() => window.location.reload(), 2000);
                }

                incomingMsg.content = displayContent;

                // [FINAL COMMIT] Apply ALL Atomic Updates
                if (hasStateChanges && onCharacterUpdate && selectedCharacter) {
                    console.log("💾 Persisting Combined Updates (Atomic):", localStatus);
                    onCharacterUpdate({ status: localStatus });
                }

                setMessages((prev) => {
                    // [MULTIPLAYER FIX] ID-based deduplication — skip if already in array
                    if (incomingMsg.id && prev.some(m => m.id === incomingMsg.id)) {
                        return prev;
                    }
                    return [...prev, incomingMsg];
                })
            }
        }
    })

    // Reusable fetch history function
    const fetchHistory = React.useCallback(async () => {
        if (!campaignId) return
        const supabase = createClient()
        // Load the LAST 100 messages (newest first), then reverse for chronological display
        const { data, error } = await supabase
            .from('messages')
            .select('*')
            .eq('campaign_id', campaignId)
            .order('created_at', { ascending: false })
            .limit(100)

        if (error) {
            console.error("Error fetching chat history:", error)
            return
        }

        if (data) {
            console.log(`📜 fetchHistory: loaded ${data.length} messages for campaign ${campaignId}`)
            const ordered = [...data].reverse()
            const history: Message[] = ordered.map((msg: any) => ({
                id: msg.id,
                role: msg.role as "user" | "assistant" | "system",
                content: stripSystemTags(msg.content, msg.role),
                timestamp: new Date(msg.created_at),
                imageUrl: msg.image_url,
                debugInfo: msg.role === "assistant" ? msg.metadata : undefined,
                senderId: msg.sender_id || null,
                senderName: msg.metadata?.character_name || "Player",
            }))

            if (history.length === 0) {
                setMessages([{
                    role: "assistant",
                    content: "Te encuentras ante la entrada de la caverna. El olor a humedad y podredumbre emana de su interior. ¿Qué haces?",
                    timestamp: new Date()
                }])
            } else {
                setMessages(history)
            }
        }
    }, [campaignId])

    // Load History from Supabase — filtered by campaign, re-fetches on campaign change
    React.useEffect(() => {
        if (!campaignId) {
            setMessages([{
                role: "assistant",
                content: "Select a character to begin your adventure.",
                timestamp: new Date()
            }])
            return
        }
        setMessages([])
        fetchHistory()
    }, [campaignId, fetchHistory]);

    // Re-sync messages when returning from background (mobile sleep, tab switch)
    const lastSyncRef = React.useRef<number>(0)
    React.useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible' && campaignId) {
                const now = Date.now()
                if (now - lastSyncRef.current < 5000) return
                lastSyncRef.current = now
                console.log('🔄 Tab visible again, re-syncing messages (after token refresh delay)...')
                toast.info('Syncing messages...', { duration: 2000 })
                // Wait for potential token refresh before re-syncing
                setTimeout(() => {
                    fetchHistory()
                }, 1500)
            }
        }
        const handleOnline = () => {
            if (campaignId) {
                console.log('🔄 Back online, re-syncing messages (after token refresh delay)...')
                // Wait for potential token refresh before re-syncing
                setTimeout(() => {
                    fetchHistory()
                }, 1500)
            }
        }
        document.addEventListener('visibilitychange', handleVisibilityChange)
        window.addEventListener('online', handleOnline)
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange)
            window.removeEventListener('online', handleOnline)
        }
    }, [campaignId, fetchHistory]);

    // Scroll effect
    React.useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages])

    // Handle External Events (Dice Rolls)
    // Prevent Infinite Loops by tracking processed events
    const [processedEvent, setProcessedEvent] = React.useState<string | null>(null)

    React.useEffect(() => {
        // 1. Process New Event
        if (externalEvent && !isLoading && externalEvent !== processedEvent) {
            console.log("🎲 Handling External Event:", externalEvent);
            setProcessedEvent(externalEvent); // Mark as processed immediately

            handleSendMessage(null, externalEvent);

            // Clear in parent
            if (onEventHandled) onEventHandled();
        }

        // 2. Reset Logic (When parent clears event, we clear our tracker)
        if (!externalEvent && processedEvent) {
            setProcessedEvent(null);
        }
    }, [externalEvent, isLoading, processedEvent, onEventHandled])

    const handleSendMessage = async (e: React.FormEvent | null, overrideContent?: string) => {
        if (e) e.preventDefault()

        const contentToSend = overrideContent || input
        if (!contentToSend.trim() || isLoading) return

        // GM-only admin commands check
        const adminCommands = ["/reset", "/checkpoint", "/load", "/list"]
        const trimmed = contentToSend.trim().toLowerCase()
        if (adminCommands.some(cmd => trimmed.startsWith(cmd)) && !isGM) {
            toast.error("Only the GM can use admin commands.")
            return
        }

        // No optimistic update — message will arrive via Realtime
        if (!overrideContent) setInput("")
        setIsLoading(true)

        try {
            // Format Character Context
            let charContext = "No character selected."
            if (selectedCharacter) {
                const s = selectedCharacter.status || {};
                const hpVal = s.hp_current ?? s.hp;
                const hp = hpVal !== undefined ? `HP: ${hpVal}/${s.hp_max}` : 'HP: Unknown';
                const ac = s.ac ? `AC: ${s.ac}` : 'AC: Unknown';

                // Format Inventory
                let inventoryStr = "None";
                if (Array.isArray(s.inventory)) {
                    inventoryStr = s.inventory.map((i: any) => `${i.item || 'Item'} (x${i.qty || 1})`).join(', ');
                } else if (typeof s.inventory === 'string') {
                    inventoryStr = s.inventory;
                }

                // Format Money
                let moneyStr = "";
                if (s.money) {
                    moneyStr = `Money: ${s.money.gp || 0}gp, ${s.money.sp || 0}sp, ${s.money.cp || 0}cp`;
                }

                // Format Spells if available
                let spellStr = "";
                if (Array.isArray(s.spells)) {
                    spellStr = "Spells: " + s.spells.map((sp: any) => `${sp.name}`).join(', ');
                }

                charContext = `
                Name: ${selectedCharacter.name}
                Class: ${selectedCharacter.class} (Lvl ${selectedCharacter.level})
                Race: ${selectedCharacter.race}
                Stats: STR=${selectedCharacter.stats.str}, DEX=${selectedCharacter.stats.dex}, CON=${selectedCharacter.stats.con}, INT=${selectedCharacter.stats.int}, WIS=${selectedCharacter.stats.wis}, CHA=${selectedCharacter.stats.cha}
                Status: ${hp}, ${ac}, Speed=${s.speed || '30'}
                Inventory: ${inventoryStr}
                ${moneyStr}
                ${spellStr}
                Bio: ${selectedCharacter.bio || ''}
                `.trim();
            }

            // Call Backend API
            const res = await authenticatedFetch("/api/chat", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: contentToSend,
                    character_context: charContext,
                    history: messages.slice(-10).map(m => ({
                        role: m.role,
                        content: m.content,
                        sender_name: m.senderName || (m.senderId ? "Unknown Player" : "S.A.M.")
                    }))
                })
            })

            if (!res.ok) {
                throw new Error(`Backend returned ${res.status}`)
            }

            const data = await res.json()

            if (data.response) {
                if (data.updates && onCharacterUpdate) {
                    onCharacterUpdate(data.updates)
                }

                let finalContent = data.response;

                // [PHASE 11] ADMIN ACTIONS HANDLER
                if (finalContent.includes("<ACTION>CLEAR_CHAT</ACTION>")) {
                    setMessages([]);
                    localStorage.removeItem('sam_chat_history');
                    finalContent = finalContent.replace("<ACTION>CLEAR_CHAT</ACTION>", "").trim();
                }

                if (finalContent.includes("<ACTION>REFRESH_CHARACTERS</ACTION>")) {
                    finalContent = finalContent.replace("<ACTION>REFRESH_CHARACTERS</ACTION>", "").trim();
                    // Reload to reflect deep state changes
                    setTimeout(() => window.location.reload(), 2000);
                }

                if (finalContent || data.image_url) {
                    // [SYNC OR MANUAL?] 
                    // Admin Commands (starting with /) are ephemeral -> No DB -> Manual UI Update
                    const isAdmin = contentToSend.trim().startsWith("/");

                    if (isAdmin) {
                        const assistantMsg: Message = {
                            role: "assistant", // "system" maybe? No, assistant is fine.
                            content: finalContent,
                            imageUrl: data.image_url,
                            debugInfo: data.debug_info,
                            timestamp: new Date()
                        }
                        setMessages(prev => [...prev, assistantMsg]);
                    } else {
                        // Standard AI messages -> Wait for Realtime INSERT event
                        console.log("✅ Message sent, waiting for Realtime sync...");
                    }
                }
            }

        } catch (error) {
            console.error(error)
            const errorMsg: Message = { role: "system", content: "Error communicating with S.A.M. (Offline)", timestamp: new Date() }
            setMessages(prev => [...prev, errorMsg])

            toast.error("❌ Fallo de conexión con S.A.M.", {
                description: "El servidor no responde. Verifica tu conexión.",
                action: {
                    label: "Reintentar",
                    onClick: () => handleSendMessage(null, contentToSend)
                }
            })
        } finally {
            setIsLoading(false)
        }
    }

    // Determine message ownership for multiplayer alignment
    const isMyMessage = (msg: Message) => msg.senderId != null && msg.senderId === currentUserId
    const isOtherPlayer = (msg: Message) => msg.senderId != null && msg.senderId !== currentUserId
    // SAM messages: senderId is null

    // [PHASE 16] Visualizer for DM Rolls
    // 2+ DM_ROLLs in a message → HOIST mode: stack all chips at the top of the
    //                           bubble, remove tags from the narrative text below.
    // 0 or 1 DM_ROLL           → INLINE mode: single chip flows with the prose.
    const renderMessageContent = (content: string, role: string = 'assistant') => {
        // Safety net: strip any machine tags that survived processing
        content = stripSystemTags(content, role)

        type RollData = { result: string | number; roll: string; reason: string };
        const parseRoll = (raw: string): RollData | null => {
            try {
                return JSON.parse(raw);
            } catch {
                return null;
            }
        };

        const chipBase = "inline-flex items-center gap-1.5 bg-black/40 text-purple-300 border border-purple-500/30 px-2 py-1 rounded-md text-xs font-mono select-none";

        const renderChipBody = (data: RollData) => (
            <>
                <span className="text-lg">🎲</span>
                <span className="font-semibold text-purple-100">{data.result}</span>
                <span className="text-muted-foreground">({data.roll})</span>
                <span className="mx-1 text-purple-500/50">|</span>
                <span className="italic text-purple-200">{data.reason}</span>
            </>
        );

        const dmRollRegex = /<DM_ROLL>([\s\S]*?)<\/DM_ROLL>/g;
        const matches = [...content.matchAll(dmRollRegex)];

        // ─── HOIST MODE — 2+ rolls ───
        if (matches.length >= 2) {
            const rolls = matches.map(m => parseRoll(m[1]));

            // Remove all DM_ROLL tags from the narrative text
            let textOnly = content.replace(dmRollRegex, "");
            // Collapse horizontal whitespace left behind by removed tags
            textOnly = textOnly
                .replace(/[ \t]+/g, " ")
                .replace(/ *\n/g, "\n")
                .replace(/\n{3,}/g, "\n\n")
                .trim();

            return (
                <>
                    <div className="flex flex-col gap-1 my-2 items-start">
                        {rolls.map((r, i) => (
                            r
                                ? <span key={i} className={`${chipBase} w-fit`}>{renderChipBody(r)}</span>
                                : <span key={i} className="text-red-500 text-xs">[Invalid Roll Data]</span>
                        ))}
                    </div>
                    {textOnly && <div className="whitespace-pre-wrap">{textOnly}</div>}
                </>
            );
        }

        // ─── INLINE MODE — 0 or 1 roll ───
        const parts = content.split(/(<DM_ROLL>[\s\S]*?<\/DM_ROLL>)/g);
        return parts.map((part, idx) => {
            if (part.startsWith("<DM_ROLL>")) {
                const data = parseRoll(part.replace(/<\/?DM_ROLL>/g, ""));
                if (!data) {
                    return <span key={idx} className="text-red-500 text-xs">[Invalid Roll Data]</span>;
                }
                return (
                    <span key={idx} className={`${chipBase} mx-1 my-1`}>
                        {renderChipBody(data)}
                    </span>
                );
            }
            return <span key={idx}>{part}</span>;
        });
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <header className="flex h-9 sm:h-14 items-center gap-2 sm:gap-4 border-b bg-muted/40 px-3 sm:px-6 shrink-0">
                <h1 className="text-xs sm:text-lg font-semibold truncate">{campaignName ? `Campaign: ${campaignName}` : "S.A.M."}</h1>
                <div className="ml-auto flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-sm text-muted-foreground">
                    <span className={`flex h-2 w-2 rounded-full ${isLoading ? "bg-yellow-500 animate-pulse" : "bg-green-500"}`} />
                    <span className="hidden sm:inline">S.A.M. {isLoading ? "Thinking..." : "Active"}</span>
                    <span className="sm:hidden">{isLoading ? "..." : "OK"}</span>
                </div>
            </header>

            {/* Combat Initiative Banner */}
            {isInCombat && combatState.initiative_order && (
                <div className="px-4 py-2 bg-red-900/20 border-b border-red-800/30 text-sm shrink-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-red-400 font-semibold">⚔️ Combat — Round {combatState.round}</span>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {combatState.initiative_order.map((entry: any, i: number) => (
                            <span
                                key={i}
                                className={`px-2 py-0.5 rounded text-xs ${
                                    entry.name === combatState.current_turn
                                        ? 'bg-red-600 text-white font-bold'
                                        : entry.is_npc
                                            ? 'bg-gray-700 text-gray-400'
                                            : 'bg-gray-800 text-gray-300'
                                }`}
                            >
                                {entry.name} ({entry.initiative})
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
                <div className="flex flex-col gap-6 pb-4">
                    {messages.map((msg, index) => {
                        const mine = isMyMessage(msg)
                        const otherPlayer = isOtherPlayer(msg)

                        // Avatar and name logic
                        let avatarFallback = "AI"
                        let avatarSrc = "/avatars/sam_logo.png"
                        let displayName = "S.A.M."
                        let bubbleClass = "text-foreground" // SAM default

                        if (mine) {
                            avatarFallback = selectedCharacter?.name?.[0]?.toUpperCase() || "U"
                            avatarSrc = selectedCharacter?.image_url || ""
                            displayName = selectedCharacter?.name || "You"
                            bubbleClass = "bg-primary text-primary-foreground px-3 py-2 rounded-lg"
                        } else if (otherPlayer) {
                            avatarFallback = msg.senderName?.[0]?.toUpperCase() || "P"
                            avatarSrc = ""
                            displayName = msg.senderName || "Player"
                            bubbleClass = "bg-blue-500/20 text-foreground border border-blue-500/30 px-3 py-2 rounded-lg"
                        }

                        return (
                        <div
                            key={index}
                            className={`flex gap-4 ${mine ? "flex-row-reverse text-right" : ""}`}
                        >
                            <Avatar className={`h-10 w-10 border-2 ${mine ? "border-muted" : otherPlayer ? "border-blue-500/50" : "border-primary"}`}>
                                <AvatarFallback>{avatarFallback}</AvatarFallback>
                                <AvatarImage src={avatarSrc} />
                            </Avatar>

                            <div className={`grid gap-1 max-w-[80%] ${mine ? "justify-items-end" : ""}`}>
                                <div className={`font-semibold text-sm ${otherPlayer ? "text-blue-400" : "text-muted-foreground"}`}>
                                    {displayName}
                                </div>
                                <div className={`text-sm leading-relaxed whitespace-pre-wrap ${bubbleClass}`}>
                                    {renderMessageContent(msg.content, msg.role)}
                                </div>
                                {msg.imageUrl && (
                                    <div className="mt-2 rounded-lg overflow-hidden border">
                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img src={msg.imageUrl} alt="Generated scene" className="w-full h-auto max-w-md object-cover" />
                                    </div>
                                )}

                                {/* Debug Button */}
                                {msg.role === 'assistant' && msg.debugInfo && (
                                    <div className="mt-1 flex justify-start">
                                        <Button variant="ghost" size="sm" className="h-5 w-5 p-0 text-muted-foreground hover:text-purple-400"
                                            onClick={() => {
                                                setCurrentDebugInfo(msg.debugInfo)
                                                setDebugOpen(true)
                                            }}
                                            title="View Neural Process">
                                            <Brain className="h-3 w-3" />
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </div>
                        )
                    })}
                </div>
                {/* Invisible anchor for auto-scroll */}
                <div ref={bottomRef} className="h-px w-full" />
            </div>

            {/* Typing Indicator */}
            {typingNames.length > 0 && (
                <div className="px-6 py-1 text-sm text-muted-foreground italic animate-pulse">
                    {typingNames.length === 1
                        ? `${typingNames[0]} is typing...`
                        : `${typingNames.join(', ')} are typing...`
                    }
                </div>
            )}

            {/* Input Area */}
            <div className="py-3 sm:py-4 px-4 sm:px-6 border-t bg-background shrink-0 pb-safe">
                <form onSubmit={(e) => handleSendMessage(e)} className="flex gap-4">
                    <Input
                        value={input}
                        onChange={(e) => { setInput(e.target.value); sendTyping(); }}
                        placeholder={turnMessage || "Describe tu acción..."}
                        className="flex-1"
                        disabled={isLoading || (isInCombat && !isMyTurn)}
                    />
                    <Button type="submit" disabled={isLoading || (isInCombat && !isMyTurn)}>
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
            </div>

            {/* Debug Inspector Dialog */}
            <Dialog open={debugOpen} onOpenChange={setDebugOpen}>
                <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2"><Brain className="h-5 w-5 text-purple-500" /> S.A.M. Neural Inspector</DialogTitle>
                        <DialogDescription>Full analysis of AI reasoning and state updates.</DialogDescription>
                    </DialogHeader>
                    <ScrollArea className="flex-1 p-4 border rounded-md bg-muted/20">
                        {currentDebugInfo && (
                            <div className="space-y-6">
                                <div>
                                    <h4 className="font-bold text-sm text-blue-400 mb-2">🧠 RAG Context (Knowledge Retrieved)</h4>
                                    <pre className="text-xs whitespace-pre-wrap bg-primary/5 p-2 rounded border border-primary/10 font-mono text-muted-foreground">
                                        {currentDebugInfo.rag_context || "No specific context retrieved (General Knowledge used)."}
                                    </pre>
                                </div>

                                <div className="border-t pt-4">
                                    <h4 className="font-bold text-sm text-yellow-400 mb-2">⚡ State Updates (JSON)</h4>
                                    <pre className="text-xs whitespace-pre-wrap bg-yellow-500/10 p-2 rounded border border-yellow-500/20 font-mono text-muted-foreground overflow-x-auto">
                                        {currentDebugInfo.raw_response && currentDebugInfo.raw_response.includes("<UPDATE>")
                                            ? currentDebugInfo.raw_response.match(/<UPDATE>([\s\S]*?)<\/UPDATE>/)?.[1]
                                            : "No State Update triggered."
                                        }
                                    </pre>
                                </div>

                                <div className="border-t pt-4">
                                    <h4 className="font-bold text-sm text-green-400 mb-2">💬 Raw AI Response</h4>
                                    <pre className="text-xs whitespace-pre-wrap text-muted-foreground font-mono bg-black/20 p-2 rounded">
                                        {currentDebugInfo.raw_response}
                                    </pre>
                                </div>

                                <div className="border-t pt-4">
                                    <h4 className="font-bold text-sm text-purple-400 mb-2">🏗️ System Prompt Construction</h4>
                                    <pre className="text-xs whitespace-pre-wrap text-muted-foreground font-mono max-h-60 overflow-y-auto bg-black/20 p-2 rounded">
                                        {currentDebugInfo.system_prompt_preview}
                                    </pre>
                                </div>
                            </div>
                        )}
                    </ScrollArea>
                </DialogContent>
            </Dialog>
        </div>
    )
}
