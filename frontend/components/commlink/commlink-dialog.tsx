"use client"

import { useState, useEffect } from "react"
import { authenticatedFetch } from "@/lib/api"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Mail, Send, User } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export function Commlink() {
    const [open, setOpen] = useState(false)
    const [messages, setMessages] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [view, setView] = useState<'inbox' | 'compose'>('inbox')

    // Compose State
    const [subject, setSubject] = useState("")
    const [content, setContent] = useState("")
    const [recipientId, setRecipientId] = useState("") // Ideally a select dropdown

    useEffect(() => {
        if (open) fetchMessages()
    }, [open])

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

    const handleSend = async () => {
        if (!content) return

        // For prototype, we might need to know WHO to send to. 
        // We'll hardcode to "GM" (User ID?) or S.A.M. (null)?
        // Or fetch list of users.
        // For this iteration, let's allow sending to "Campaign Chat" (Broadcast?) No, this is PRIVATE.
        // We need a user list. 
        // Let's assume sending to S.A.M. (AI) for now if we don't have user list.
        // Or implement user list fetching.

        // Let's just create the UI for now and allow typing an ID (debug) or just "S.A.M.".

        try {
            const res = await authenticatedFetch('/api/messages/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    campaign_id: "FIXME_CAMPAIGN_ID", // We need context!
                    receiver_id: recipientId,
                    content,
                    subject
                })
            })
            if (res.ok) {
                toast.success("Message Encrypted & Sent")
                setView('inbox')
                fetchMessages()
                setContent("")
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
                                                <span className="font-bold text-sm text-purple-300">{msg.sender_id ? 'Unknown User' : 'S.A.M. (System)'}</span>
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
                                <Button className="w-full" onClick={handleSend}>
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
