"use client"

import { useEffect, useState, useRef } from "react"
import { authenticatedFetch } from "@/lib/api"
import { createClient } from "@/lib/supabase/client"
import { SamTuner } from "@/components/admin/sam-tuner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import Link from "next/link"
import {
    LogOut, Loader2, ShieldAlert, FileText, Upload, Ticket, Users,
    Copy, X, RotateCcw, Save, List, Swords, Shield, Plus, Map, Paperclip
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"

interface Campaign {
    id: string
    name: string
    description?: string
    status: string
    gm_id: string
    settings: any
    created_at: string
}

interface Invitation {
    id: string
    code: string
    max_uses: number
    current_uses: number
    is_active: boolean
    expires_at: string | null
    created_at: string
}

interface Profile {
    id: string
    email: string
    username: string
    role: string
    status: string
    created_at: string
}

export default function AdminPage() {
    const [campaigns, setCampaigns] = useState<Campaign[]>([])
    const [campaign, setCampaign] = useState<Campaign | null>(null)
    const [playerCounts, setPlayerCounts] = useState<Record<string, number>>({})
    const [campaignModules, setCampaignModules] = useState<Record<string, string[]>>({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [currentUserId, setCurrentUserId] = useState<string>("")

    // New Campaign Form
    const [showNewCampaign, setShowNewCampaign] = useState(false)
    const [newCampName, setNewCampName] = useState("")
    const [newCampDesc, setNewCampDesc] = useState("")
    const [newCampFile, setNewCampFile] = useState<File | null>(null)
    const [creatingCampaign, setCreatingCampaign] = useState(false)

    // Per-campaign upload
    const [uploadingFor, setUploadingFor] = useState<string | null>(null)
    const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

    // Invitations
    const [invitations, setInvitations] = useState<Invitation[]>([])
    const [newCodeMaxUses, setNewCodeMaxUses] = useState(5)
    const [generating, setGenerating] = useState(false)
    const [lastGeneratedCode, setLastGeneratedCode] = useState<string | null>(null)

    // Users
    const [profiles, setProfiles] = useState<Profile[]>([])

    // Campaign Controls
    const [commandLoading, setCommandLoading] = useState<string | null>(null)
    const [confirmReset, setConfirmReset] = useState(false)
    const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

    const supabaseRef = useRef(createClient())

    useEffect(() => {
        const init = async () => {
            try {
                const supabase = supabaseRef.current
                const { data: { user } } = await supabase.auth.getUser()
                if (!user) { setError("Not authenticated"); setLoading(false); return }
                setCurrentUserId(user.id)

                const { data: profile } = await supabase
                    .from("profiles").select("role").eq("id", user.id).single()
                if (profile?.role !== "admin") {
                    setError("Access denied. Admin role required.")
                    setLoading(false)
                    return
                }

                await fetchCampaigns()
                await fetchInvitations()
                await fetchProfiles()
                await fetchPlayerCounts()
            } catch (e) {
                console.error(e)
                setError("Connection error.")
            } finally {
                setLoading(false)
            }
        }
        init()
    }, [])

    const fetchCampaigns = async () => {
        const res = await authenticatedFetch("/api/campaigns/")
        if (res.ok) {
            const data: Campaign[] = await res.json()
            setCampaigns(data)
            const active = data.find(c => c.status === "active") || data[0] || null
            setCampaign(active)
            // Fetch modules for all campaigns
            await fetchAllModules(data)
        }
    }

    const fetchAllModules = async (camps: Campaign[]) => {
        const modules: Record<string, string[]> = {}
        for (const c of camps) {
            const { data } = await supabaseRef.current
                .from("documents")
                .select("metadata")
                .like("metadata", `%"campaign_id":"${c.id}"%`)
            const sources = new Set<string>()
            data?.forEach((doc: any) => {
                try {
                    const meta = typeof doc.metadata === "string" ? JSON.parse(doc.metadata) : doc.metadata
                    if (meta.source) sources.add(meta.source)
                } catch { /* skip */ }
            })
            modules[c.id] = Array.from(sources)
        }
        setCampaignModules(modules)
    }

    const fetchPlayerCounts = async () => {
        const { data } = await supabaseRef.current.from("characters").select("campaign_id")
        const counts: Record<string, number> = {}
        data?.forEach((c: any) => { counts[c.campaign_id] = (counts[c.campaign_id] || 0) + 1 })
        setPlayerCounts(counts)
    }

    const fetchInvitations = async () => {
        try {
            const res = await authenticatedFetch("/api/invitations/")
            if (res.ok) setInvitations(await res.json())
        } catch (e) { console.error("Failed to fetch invitations:", e) }
    }

    const fetchProfiles = async () => {
        const { data } = await supabaseRef.current
            .from("profiles").select("*").order("created_at", { ascending: false })
        setProfiles(data || [])
    }

    // --- Upload Module helper ---
    const uploadModule = async (campaignId: string, file: File): Promise<number> => {
        const { data: { session } } = await supabaseRef.current.auth.getSession()
        const fd = new FormData(); fd.append("file", file)
        const res = await fetch(`/api/campaigns/${campaignId}/modules`, {
            method: "POST",
            headers: { Authorization: `Bearer ${session?.access_token}` },
            body: fd,
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        return data.chunks || 0
    }

    // --- Campaigns ---
    const handleCreateCampaign = async () => {
        if (!newCampName.trim()) return
        setCreatingCampaign(true)
        try {
            const res = await authenticatedFetch("/api/campaigns/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: newCampName.trim(), description: newCampDesc.trim() }),
            })
            if (res.ok) {
                const newCamp = await res.json()
                let msg = `Campaign "${newCamp.name}" created`

                // Upload module if file selected
                if (newCampFile) {
                    try {
                        const chunks = await uploadModule(newCamp.id, newCampFile)
                        msg += ` + ${chunks} chunks indexed from ${newCampFile.name}`
                    } catch (e) {
                        toast.error(`Campaign created but module upload failed: ${e}`)
                    }
                }

                toast.success(msg)
                setNewCampName("")
                setNewCampDesc("")
                setNewCampFile(null)
                setShowNewCampaign(false)
                await fetchCampaigns()
                await fetchPlayerCounts()
            } else toast.error("Failed to create campaign")
        } catch { toast.error("Error creating campaign") }
        finally { setCreatingCampaign(false) }
    }

    const handleInlineUpload = async (campaignId: string, file: File) => {
        setUploadingFor(campaignId)
        try {
            const chunks = await uploadModule(campaignId, file)
            toast.success(`Module uploaded: ${chunks} chunks from ${file.name}`)
            await fetchAllModules(campaigns)
        } catch (e) {
            toast.error(`Upload failed: ${e}`)
        } finally {
            setUploadingFor(null)
        }
    }

    const activateCampaign = async (id: string) => {
        for (const c of campaigns) {
            if (c.id !== id && c.status === "active") {
                await authenticatedFetch(`/api/campaigns/${c.id}`, {
                    method: "PATCH", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: "inactive" }),
                })
            }
        }
        await authenticatedFetch(`/api/campaigns/${id}`, {
            method: "PATCH", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "active" }),
        })
        toast.success("Campaign activated")
        await fetchCampaigns()
    }

    const deactivateCampaign = async (id: string) => {
        await authenticatedFetch(`/api/campaigns/${id}`, {
            method: "PATCH", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "inactive" }),
        })
        toast.success("Campaign deactivated")
        await fetchCampaigns()
    }

    const deleteCampaign = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/api/campaigns/${id}`, { method: "DELETE" })
            if (res.ok) { toast.success("Campaign deleted"); setConfirmDelete(null); await fetchCampaigns(); await fetchPlayerCounts() }
            else toast.error("Failed to delete campaign")
        } catch { toast.error("Error deleting campaign") }
    }

    // --- Invitations ---
    const handleGenerateCode = async () => {
        setGenerating(true); setLastGeneratedCode(null)
        try {
            const res = await authenticatedFetch("/api/invitations/", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ max_uses: newCodeMaxUses, expires_hours: 168 }),
            })
            if (res.ok) { const d = await res.json(); setLastGeneratedCode(d.code); toast.success(`Code: ${d.code}`); await fetchInvitations() }
            else toast.error("Failed to generate code")
        } catch { toast.error("Error") }
        finally { setGenerating(false) }
    }

    const handleDeactivateInvite = async (id: string) => {
        const res = await authenticatedFetch(`/api/invitations/${id}`, { method: "DELETE" })
        if (res.ok) { toast.success("Deactivated"); await fetchInvitations() }
    }

    const copyCode = (code: string) => { navigator.clipboard.writeText(code); toast.success(`Copied: ${code}`) }

    // --- Players ---
    const toggleRole = async (pid: string, cur: string) => {
        await supabaseRef.current.from("profiles").update({ role: cur === "admin" ? "player" : "admin" }).eq("id", pid)
        toast.success("Role changed"); await fetchProfiles()
    }
    const toggleStatus = async (pid: string, cur: string) => {
        await supabaseRef.current.from("profiles").update({ status: cur === "approved" ? "rejected" : "approved" }).eq("id", pid)
        toast.success("Status changed"); await fetchProfiles()
    }

    // --- Campaign Controls ---
    const sendCommand = async (cmd: string) => {
        setCommandLoading(cmd)
        try {
            const res = await authenticatedFetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: cmd }) })
            if (res.ok) { const d = await res.json(); toast.success(d.response?.substring(0, 100) || "Done") }
            else toast.error("Failed")
        } catch { toast.error("Error") }
        finally { setCommandLoading(null); setConfirmReset(false) }
    }

    const clearCombatState = async () => {
        if (!campaign) return
        await supabaseRef.current.from("campaigns").update({ settings: {} }).eq("id", campaign.id)
        toast.success("Combat state cleared")
    }

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin text-purple-500" /></div>
    if (error) return (
        <div className="flex h-screen flex-col items-center justify-center gap-4 text-red-400">
            <ShieldAlert className="h-12 w-12" /><div>{error}</div>
            <Link href="/"><Button variant="outline">Back to Game</Button></Link>
        </div>
    )

    return (
        <div className="container mx-auto p-4 sm:p-6 space-y-6 max-w-5xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">God Mode</h1>
                    <p className="text-muted-foreground text-sm">Active: {campaign?.name || "None"}</p>
                </div>
                <Link href="/"><Button variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/10"><LogOut className="mr-2 h-4 w-4" /> Exit</Button></Link>
            </div>

            {/* Row 1: Campaigns (full width) */}
            <Card className="border-cyan-500/20 bg-black/40">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-cyan-400 flex items-center gap-2"><Map className="h-5 w-5" /> Campaigns</CardTitle>
                        <Button size="sm" variant="secondary" onClick={() => setShowNewCampaign(!showNewCampaign)}>
                            <Plus className="mr-1 h-3 w-3" /> New Campaign
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* New Campaign Form */}
                    {showNewCampaign && (
                        <div className="p-3 border border-cyan-500/20 rounded-lg space-y-3">
                            <div>
                                <Label className="text-xs">Name</Label>
                                <Input value={newCampName} onChange={(e) => setNewCampName(e.target.value)} placeholder="The Lost Mines of Phandelver" />
                            </div>
                            <div>
                                <Label className="text-xs">Description</Label>
                                <Textarea value={newCampDesc} onChange={(e) => setNewCampDesc(e.target.value)} placeholder="A classic D&D adventure..." className="min-h-[60px]" />
                            </div>
                            <div>
                                <Label className="text-xs">PDF Module (optional)</Label>
                                <Input type="file" accept=".pdf,.epub" onChange={(e) => setNewCampFile(e.target.files?.[0] || null)} className="cursor-pointer" />
                            </div>
                            <div className="flex gap-2">
                                <Button size="sm" onClick={handleCreateCampaign} disabled={!newCampName.trim() || creatingCampaign}>
                                    {creatingCampaign ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                                    {creatingCampaign ? "Creating..." : "Create"}
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => { setShowNewCampaign(false); setNewCampFile(null) }}>Cancel</Button>
                            </div>
                        </div>
                    )}

                    {/* Campaign List */}
                    <div className="space-y-2">
                        {campaigns.length === 0 && <p className="text-xs text-muted-foreground">No campaigns yet.</p>}
                        {campaigns.map((c) => {
                            const isActive = c.status === "active"
                            const count = playerCounts[c.id] || 0
                            const modules = campaignModules[c.id] || []
                            const isConfirmingDelete = confirmDelete === c.id
                            const isUploading = uploadingFor === c.id

                            return (
                                <div key={c.id} className={`p-3 rounded-lg ${isActive ? "bg-green-500/5 border border-green-500/20" : "bg-muted/20"}`}>
                                    <div className="flex items-center gap-3">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className={`font-medium truncate ${isActive ? "text-green-400" : ""}`}>{c.name}</span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${isActive ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-500"}`}>{c.status}</span>
                                            </div>
                                            <div className="text-xs text-muted-foreground truncate">
                                                {count} player{count !== 1 ? "s" : ""}{c.description ? ` — ${c.description}` : ""}
                                            </div>
                                        </div>
                                        <div className="flex gap-1 flex-shrink-0">
                                            {/* Upload Module */}
                                            <input
                                                type="file"
                                                accept=".pdf,.epub"
                                                className="hidden"
                                                ref={(el) => { fileInputRefs.current[c.id] = el }}
                                                onChange={(e) => { if (e.target.files?.[0]) handleInlineUpload(c.id, e.target.files[0]); e.target.value = "" }}
                                            />
                                            <Button size="sm" variant="ghost" className="h-7 text-xs" disabled={isUploading}
                                                onClick={() => fileInputRefs.current[c.id]?.click()}>
                                                {isUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Paperclip className="h-3 w-3" />}
                                            </Button>
                                            {isActive ? (
                                                <Button size="sm" variant="ghost" className="h-7 text-xs text-gray-400" onClick={() => deactivateCampaign(c.id)}>Deactivate</Button>
                                            ) : (
                                                <Button size="sm" variant="ghost" className="h-7 text-xs text-green-400" onClick={() => activateCampaign(c.id)}>Activate</Button>
                                            )}
                                            {!isActive && count === 0 && !isConfirmingDelete && (
                                                <Button size="sm" variant="ghost" className="h-7 text-xs text-red-400" onClick={() => setConfirmDelete(c.id)}>Delete</Button>
                                            )}
                                            {isConfirmingDelete && (
                                                <>
                                                    <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => deleteCampaign(c.id)}>Confirm</Button>
                                                    <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setConfirmDelete(null)}>Cancel</Button>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                    {/* Modules list */}
                                    {modules.length > 0 && (
                                        <div className="mt-2 flex gap-1 flex-wrap">
                                            {modules.map((m, i) => (
                                                <span key={i} className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded">
                                                    <FileText className="h-2.5 w-2.5" /> {m}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Row 2: SAM Tuner + Campaign Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {campaign && <SamTuner campaignId={campaign.id} initialSettings={campaign.settings || {}} />}

                <Card className="border-orange-500/20 bg-black/40">
                    <CardHeader>
                        <CardTitle className="text-orange-400 flex items-center gap-2"><Shield className="h-5 w-5" /> Campaign Controls</CardTitle>
                        <CardDescription>Commands for {campaign?.name || "—"}.</CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-2 gap-2">
                        {!confirmReset ? (
                            <Button variant="destructive" size="sm" onClick={() => setConfirmReset(true)} disabled={!!commandLoading}>
                                <RotateCcw className="mr-1 h-3 w-3" /> Reset
                            </Button>
                        ) : (
                            <div className="col-span-2 flex gap-2 items-center p-2 bg-red-500/10 border border-red-500/30 rounded">
                                <span className="text-xs text-red-400 flex-1">Delete all messages and restore HP?</span>
                                <Button variant="destructive" size="sm" onClick={() => sendCommand("/reset")} disabled={commandLoading === "/reset"}>
                                    {commandLoading === "/reset" ? <Loader2 className="h-3 w-3 animate-spin" /> : "Confirm"}
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => setConfirmReset(false)}>Cancel</Button>
                            </div>
                        )}
                        <Button variant="secondary" size="sm" onClick={() => sendCommand("/checkpoint")} disabled={!!commandLoading}>
                            {commandLoading === "/checkpoint" ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Save className="mr-1 h-3 w-3" />} Checkpoint
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => sendCommand("/list")} disabled={!!commandLoading}>
                            {commandLoading === "/list" ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <List className="mr-1 h-3 w-3" />} List
                        </Button>
                        <Button variant="outline" size="sm" className="border-orange-500/30 text-orange-400" onClick={clearCombatState}>
                            <Swords className="mr-1 h-3 w-3" /> Clear Combat
                        </Button>
                    </CardContent>
                </Card>
            </div>

            {/* Row 3: Invitations + Players */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-yellow-500/20 bg-black/40">
                    <CardHeader><CardTitle className="text-yellow-400 flex items-center gap-2"><Ticket className="h-5 w-5" /> Invitations</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-end gap-2">
                            <div className="flex-1">
                                <Label className="text-xs">Max uses</Label>
                                <Input type="number" value={newCodeMaxUses} onChange={(e) => setNewCodeMaxUses(parseInt(e.target.value) || 1)} min={1} max={100} className="h-8" />
                            </div>
                            <Button onClick={handleGenerateCode} disabled={generating} size="sm" className="bg-yellow-600 hover:bg-yellow-700">
                                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate"}
                            </Button>
                        </div>
                        {lastGeneratedCode && (
                            <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                                <span className="font-mono text-xl font-bold tracking-widest flex-1">{lastGeneratedCode}</span>
                                <Button size="sm" variant="ghost" onClick={() => copyCode(lastGeneratedCode)}><Copy className="h-4 w-4" /></Button>
                            </div>
                        )}
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {invitations.length === 0 && <p className="text-xs text-muted-foreground">No invitations yet.</p>}
                            {invitations.map((inv) => {
                                const dead = !inv.is_active || (inv.expires_at && new Date(inv.expires_at) < new Date()) || inv.current_uses >= inv.max_uses
                                return (
                                    <div key={inv.id} className="flex items-center gap-2 text-sm p-2 rounded bg-muted/20">
                                        <button onClick={() => copyCode(inv.code)} className="font-mono font-bold tracking-wider hover:text-yellow-400">{inv.code}</button>
                                        <span className={`text-xs ${dead ? "text-gray-500" : "text-green-400"}`}>{inv.current_uses}/{inv.max_uses}</span>
                                        <span className="text-xs text-muted-foreground flex-1">{dead ? (inv.is_active ? (inv.current_uses >= inv.max_uses ? "used" : "expired") : "inactive") : "active"}</span>
                                        {!dead && <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-400" onClick={() => handleDeactivateInvite(inv.id)}><X className="h-3 w-3" /></Button>}
                                    </div>
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-green-500/20 bg-black/40">
                    <CardHeader><CardTitle className="text-green-400 flex items-center gap-2"><Users className="h-5 w-5" /> Players</CardTitle></CardHeader>
                    <CardContent>
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {profiles.map((p) => {
                                const isSelf = p.id === currentUserId
                                return (
                                    <div key={p.id} className="flex items-center gap-2 text-sm p-2 rounded bg-muted/20">
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium truncate">{p.username || "—"}{isSelf && " (you)"}</div>
                                            <div className="text-xs text-muted-foreground truncate">{p.email}</div>
                                        </div>
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${p.role === "admin" ? "bg-purple-500/20 text-purple-400" : "bg-gray-500/20 text-gray-400"}`}>{p.role}</span>
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${p.status === "approved" ? "bg-green-500/20 text-green-400" : p.status === "pending" ? "bg-yellow-500/20 text-yellow-400" : "bg-red-500/20 text-red-400"}`}>{p.status}</span>
                                        {!isSelf && (
                                            <div className="flex gap-1">
                                                <Button size="sm" variant="ghost" className="h-6 text-[10px] px-1.5" onClick={() => toggleRole(p.id, p.role)}>{p.role === "admin" ? "→Player" : "→Admin"}</Button>
                                                <Button size="sm" variant="ghost" className={`h-6 text-[10px] px-1.5 ${p.status === "approved" ? "text-red-400" : "text-green-400"}`}
                                                    onClick={() => toggleStatus(p.id, p.status)}>{p.status === "approved" ? "Deactivate" : "Activate"}</Button>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
