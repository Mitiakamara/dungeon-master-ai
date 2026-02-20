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

interface Message {
    role: "user" | "assistant" | "system"
    content: string
    imageUrl?: string
    debugInfo?: any
    timestamp: Date
}

export function ChatInterface({
    selectedCharacter,
    externalEvent,
    onEventHandled,
    onCharacterUpdate
}: {
    selectedCharacter: any,
    externalEvent?: string | null,
    onEventHandled?: () => void,
    onCharacterUpdate?: (updates: any) => void
}) {
    const [messages, setMessages] = React.useState<Message[]>([])
    const [input, setInput] = React.useState("")
    const [isLoading, setIsLoading] = React.useState(false)
    const bottomRef = React.useRef<HTMLDivElement>(null)

    // Debug Inspector State
    const [debugOpen, setDebugOpen] = React.useState(false)
    const [currentDebugInfo, setCurrentDebugInfo] = React.useState<any>(null)

    // [PHASE 13] REALTIME SUBSCRIPTION
    useRealtime({
        table: 'messages',
        event: '*',
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

                const incomingMsg: Message = {
                    role: payload.role as "user" | "assistant" | "system",
                    content: payload.content,
                    imageUrl: payload.image_url,
                    timestamp: new Date(payload.created_at)
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
                                lootData.items.forEach((itemObj: any) => {
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
                    const lastMsg = prev[prev.length - 1];

                    // [SYNC FIX] Deduplication Logic
                    const isDuplicate = lastMsg
                        && lastMsg.content === incomingMsg.content
                        && lastMsg.role === incomingMsg.role;

                    if (isDuplicate) {
                        return prev;
                    }

                    return [...prev, incomingMsg];
                })
            }
        }
    })

    // Load History from Supabase
    React.useEffect(() => {
        const fetchHistory = async () => {
            const supabase = createClient()
            const { data, error } = await supabase
                .from('messages')
                .select('*')
                .order('created_at', { ascending: true })
                .limit(100)

            if (error) {
                console.error("Error fetching chat history:", error)
                return
            }

            if (data) {
                const history: Message[] = data.map((msg: any) => ({
                    role: msg.role as "user" | "assistant" | "system",
                    content: msg.content,
                    timestamp: new Date(msg.created_at),
                    imageUrl: msg.image_url,
                    debugInfo: msg.metadata // Assuming metadata stores extra info if any
                }))

                // If history is empty, show welcome message
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
        }

        fetchHistory()
    }, []);

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

        const userMsg: Message = { role: "user", content: contentToSend, timestamp: new Date() }

        setMessages(prev => [...prev, userMsg])
        if (!overrideContent) setInput("")
        setIsLoading(true)

        try {
            // Format Character Context
            let charContext = "No character selected."
            if (selectedCharacter) {
                const s = selectedCharacter.status || {};
                const hp = s.hp_current !== undefined ? `HP: ${s.hp_current}/${s.hp_max}` : 'HP: Unknown';
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
                    history: messages.slice(-5).map(m => ({ role: m.role, content: m.content }))
                })
            })

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

    // [PHASE 16] Visualizer for DM Rolls
    const renderMessageContent = (content: string) => {
        // Split by the tag, keeping the delimiter
        const parts = content.split(/(<DM_ROLL>[\s\S]*?<\/DM_ROLL>)/g);

        return parts.map((part, index) => {
            if (part.startsWith("<DM_ROLL>")) {
                try {
                    // Extract JSON
                    const jsonStr = part.replace(/<\/?DM_ROLL>/g, "");
                    const data = JSON.parse(jsonStr);

                    return (
                        <span key={index} className="inline-flex items-center gap-1.5 bg-black/40 text-purple-300 border border-purple-500/30 px-2 py-1 rounded-md text-xs font-mono mx-1 my-1 select-none">
                            <span className="text-lg">🎲</span>
                            <span className="font-semibold text-purple-100">{data.result}</span>
                            <span className="text-muted-foreground">({data.roll})</span>
                            <span className="mx-1 text-purple-500/50">|</span>
                            <span className="italic text-purple-200">{data.reason}</span>
                        </span>
                    );
                } catch (e) {
                    return <span key={index} className="text-red-500 text-xs">[Invlaid Roll Data]</span>;
                }
            }
            return <span key={index}>{part}</span>;
        });
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-6 shrink-0">
                <h1 className="text-lg font-semibold">Campaña: La Mina Perdida</h1>
                <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground">
                    <span className={`flex h-2 w-2 rounded-full ${isLoading ? "bg-yellow-500 animate-pulse" : "bg-green-500"}`} />
                    S.A.M. {isLoading ? "Thinking..." : "Active"}
                </div>
            </header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
                <div className="flex flex-col gap-6 pb-4">
                    {messages.map((msg, index) => (
                        <div
                            key={index}
                            className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse text-right" : ""}`}
                        >
                            <Avatar className={`h-10 w-10 border-2 ${msg.role === "assistant" ? "border-primary" : "border-muted"}`}>
                                <AvatarFallback>{msg.role === "user" ? (selectedCharacter?.name?.[0]?.toUpperCase() || "U") : "AI"}</AvatarFallback>
                                <AvatarImage src={msg.role === "assistant" ? "/avatars/sam_logo.png" : selectedCharacter?.image_url} />
                            </Avatar>

                            <div className={`grid gap-1 max-w-[80%] ${msg.role === "user" ? "justify-items-end" : ""}`}>
                                <div className="font-semibold text-sm text-muted-foreground">
                                    {msg.role === "user" ? (selectedCharacter?.name || "You") : "S.A.M."}
                                </div>
                                <div className={`text-sm leading-relaxed whitespace-pre-wrap ${msg.role === "assistant" ? "text-foreground" : "bg-primary text-primary-foreground px-3 py-2 rounded-lg"}`}>
                                    {renderMessageContent(msg.content)}
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
                    ))}
                </div>
                {/* Invisible anchor for auto-scroll */}
                <div ref={bottomRef} className="h-px w-full" />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t bg-background shrink-0">
                <form onSubmit={(e) => handleSendMessage(e)} className="flex gap-4">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Describe tu acción..."
                        className="flex-1"
                        disabled={isLoading}
                    />
                    <Button type="submit" disabled={isLoading}>
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
