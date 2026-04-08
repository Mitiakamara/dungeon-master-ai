"use client"

import { useState, useEffect } from "react"
import { authenticatedFetch } from "@/lib/api"
import { createClient } from "@/lib/supabase/client"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Mail, Send, User } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface Recipient {
    character_id: string | null
    character_name: string
    user_id: string | null
    class?: string | null
    level?: number | null
}

const SAM_VALUE = "__sam__"

export function Commlink({ campaignId }: { campaignId?: string }) {
    const [open, setOpen] = useState(false)
    const [messages, setMessages] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [view, setView] = useState<'inbox' | 'compose'>('inbox')

    // Compose State
    const [subject, setSubject] = useState("")
    const [content, setContent] = useState("")
    const [recipientValue, setRecipientValue] = useState("") // user_id, or SAM_VALUE for S.A.M.

    // Recipients + current user
    const [recipients, setRecipients] = useState<Recipient[]>([])
    const [currentUserId, setCurrentUserId] = useState<string | null>(null)
    const [myCharacterName, setMyCharacterName] = useState<string>("You")

    // Get current user id once
    useEffect(() => {
        const supabase = createClient()
        supabase.auth.getUser().then(({ data: { user } }: { data: { user: any } }) => {
            if (user) setCurrentUserId(user.id)
        })
    }, [])

    useEffect(() => {
        if (open) {
            fetchMessages()
            fetchRecipients()
        }
    }, [open, campaignId])

    const fetchMessages = async () => {
        setLoading(true)
        try {
            const res = await authenticatedFetch('/api/messages/')
            if (res.ok) {
                const data = await res.json()
                setMessages(data)
            }
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    const fetchRecipients = async () => {
        if (!campaignId) { setRecipients([]); return }
        try {
            const res = await authenticatedFetch(`/api/messages/recipients?campaign_id=${campaignId}`)
            if (res.ok) {
                const data: Recipient[] = await res.json()
                setRecipients(data)
                // Try to derive my own character name from full party fetch
                try {
                    const partyRes = await authenticatedFetch(`/api/characters/campaign/${campaignId}`)
                    if (partyRes.ok && currentUserId) {
                        const allChars = await partyRes.json()
                        const mine = allChars.find((c: any) => c.user_id === currentUserId)
                        if (mine?.name) setMyCharacterName(mine.name)
                    }
                } catch { /* ignore */ }
            }
        } catch (e) {
            console.error("Failed to fetch recipients:", e)
        }
    }

    const senderLabel = (msg: any): string => {
        if (msg.sender_id == null) return "S.A.M."
        if (currentUserId && msg.sender_id === currentUserId) return myCharacterName || "You"
        const found = recipients.find((r) => r.user_id === msg.sender_id)
        return found?.character_name || "Unknown"
    }

    const handleSend = async () => {
        if (!content) return
        if (!recipientValue) {
            toast.error("Select a recipient first")
            return
        }

        const isSam = recipientValue === SAM_VALUE
        const target = isSam ? null : recipients.find((r) => r.user_id === recipientValue)

        try {
            const res = await authenticatedFetch('/api/messages/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    campaign_id: campaignId || "",
                    receiver_id: isSam ? null : (target?.user_id ?? null),
                    receiver_character_id: isSam ? null : (target?.character_id ?? null),
                    content,
                    subject,
                })
            })
            if (res.ok) {
                toast.success("Message Encrypted & Sent")
                setView('inbox')
                fetchMessages()
                setContent("")
                setSubject("")
                setRecipientValue("")
            } else {
                toast.error("Transmission Failed")
            }
        } catch (e) {
            toast.error("Transmission Failed")
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="relative">
                    <Mail className="h-5 w-5" />
                    {messages.some(m => !m.is_read) && (
                        <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                    )}
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] h-[600px] flex flex-col p-0 gap-0">
                <DialogHeader className="p-4 border-b bg-muted/20">
                    <DialogTitle className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-purple-400" />
                        Commlink v2.0
                    </DialogTitle>
                    <DialogDescription>Encrypted channel.</DialogDescription>
                </DialogHeader>

                <div className="flex-1 flex overflow-hidden">
                    {/* Sidebar / List (Simplified inbox view for now, usually split pane) */}
                    {view === 'inbox' ? (
                        <div className="flex-1 flex flex-col">
                            <div className="p-2 border-b flex justify-between items-center">
                                <span className="text-xs font-bold text-muted-foreground ml-2">INBOX ({messages.length})</span>
                                <Button size="sm" variant="secondary" onClick={() => setView('compose')}>
                                    Compose
                                </Button>
                            </div>
                            <ScrollArea className="flex-1 p-2">
                                <div className="space-y-2">
                                    {messages.length === 0 && (
                                        <div className="text-center text-muted-foreground py-10 text-sm">No messages.</div>
                                    )}
                                    {messages.map((msg) => (
                                        <div key={msg.id} className={`p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors ${msg.is_read ? 'bg-background opacity-70' : 'bg-muted/20 border-purple-500/30'}`}>
                                            <div className="flex justify-between mb-1">
                                                <span className="font-bold text-sm text-purple-300">{senderLabel(msg)}</span>
                                                <span className="text-[10px] text-muted-foreground">{formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}</span>
                                            </div>
                                            <div className="font-medium text-sm mb-1">{msg.subject || "(No Subject)"}</div>
                                            <div className="text-xs text-muted-foreground line-clamp-2">{msg.content}</div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col p-4 gap-4">
                            <div className="flex items-center gap-2">
                                <Button variant="ghost" size="sm" onClick={() => setView('inbox')}>&larr; Inbox</Button>
                                <h3 className="font-bold">New Message</h3>
                            </div>
                            <div className="space-y-2">
                                <div>
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">To</label>
                                    <select
                                        value={recipientValue}
                                        onChange={(e) => setRecipientValue(e.target.value)}
                                        className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                    >
                                        <option value="">-- Select recipient --</option>
                                        {recipients.map((r) => {
                                            const isSam = r.user_id == null
                                            const value = isSam ? SAM_VALUE : (r.user_id || "")
                                            const meta = !isSam && (r.class || r.level)
                                                ? ` (${r.class || ""}${r.level ? ` Lvl ${r.level}` : ""})`
                                                : ""
                                            return (
                                                <option key={value} value={value}>
                                                    {r.character_name}{meta}
                                                </option>
                                            )
                                        })}
                                    </select>
                                </div>
                                <Input placeholder="Subject" value={subject} onChange={e => setSubject(e.target.value)} />
                                <Textarea
                                    className="resize-none flex-1 h-[200px]"
                                    placeholder="Type your message..."
                                    value={content}
                                    onChange={e => setContent(e.target.value)}
                                />
                                <div className="text-xs text-muted-foreground">
                                    * Messages are fully encrypted (RLS). Only the recipient can decrypt.
                                </div>
                                <Button className="w-full" onClick={handleSend} disabled={!recipientValue || !content}>
                                    <Send className="w-4 h-4 mr-2" /> Send via Subspace
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}
