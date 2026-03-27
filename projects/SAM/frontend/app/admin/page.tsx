"use client"

import { useEffect, useState } from "react"
import { authenticatedFetch } from "@/lib/api"
import { createClient } from "@/lib/supabase/client"
import { SamTuner } from "@/components/admin/sam-tuner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import Link from "next/link"
import { LogOut, Loader2, ShieldAlert, FileText, Upload, Ticket, Users, Copy, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

interface Invitation {
    id: string
    code: string
    max_uses: number
    current_uses: number
    is_active: boolean
    expires_at: string | null
    created_at: string
    campaign_id: string | null
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
    const [campaign, setCampaign] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isAdmin, setIsAdmin] = useState(false)

    // Module Upload State
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)

    // Invitations State
    const [invitations, setInvitations] = useState<Invitation[]>([])
    const [newCodeMaxUses, setNewCodeMaxUses] = useState(5)
    const [generating, setGenerating] = useState(false)
    const [lastGeneratedCode, setLastGeneratedCode] = useState<string | null>(null)

    // Users State
    const [profiles, setProfiles] = useState<Profile[]>([])

    useEffect(() => {
        const init = async () => {
            try {
                const supabase = createClient()
                const { data: { user } } = await supabase.auth.getUser()
                if (!user) { setError("Not authenticated"); setLoading(false); return }

                // Check admin role
                const { data: profile } = await supabase
                    .from("profiles")
                    .select("role")
                    .eq("id", user.id)
                    .single()

                if (profile?.role !== "admin") {
                    setError("Access denied. Admin role required.")
                    setLoading(false)
                    return
                }
                setIsAdmin(true)

                // Fetch campaign
                const res = await authenticatedFetch("/api/campaigns/")
                if (res.ok) {
                    const data = await res.json()
                    if (data?.length > 0) setCampaign(data[0])
                    else setError("No campaigns found.")
                }

                // Fetch invitations
                await fetchInvitations()

                // Fetch profiles
                const { data: allProfiles } = await supabase
                    .from("profiles")
                    .select("*")
                    .order("created_at", { ascending: false })
                setProfiles(allProfiles || [])
            } catch (e) {
                console.error(e)
                setError("Connection error.")
            } finally {
                setLoading(false)
            }
        }
        init()
    }, [])

    const fetchInvitations = async () => {
        try {
            const res = await authenticatedFetch("/api/invitations/")
            if (res.ok) setInvitations(await res.json())
        } catch (e) {
            console.error("Failed to fetch invitations:", e)
        }
    }

    const handleGenerateCode = async () => {
        setGenerating(true)
        setLastGeneratedCode(null)
        try {
            const res = await authenticatedFetch("/api/invitations/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ max_uses: newCodeMaxUses, expires_hours: 168 }),
            })
            if (res.ok) {
                const data = await res.json()
                setLastGeneratedCode(data.code)
                toast.success(`Code generated: ${data.code}`)
                await fetchInvitations()
            } else {
                toast.error("Failed to generate code")
            }
        } catch {
            toast.error("Error generating code")
        } finally {
            setGenerating(false)
        }
    }

    const handleDeactivate = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/api/invitations/${id}`, { method: "DELETE" })
            if (res.ok) {
                toast.success("Invitation deactivated")
                await fetchInvitations()
            }
        } catch {
            toast.error("Error deactivating")
        }
    }

    const copyCode = (code: string) => {
        navigator.clipboard.writeText(code)
        toast.success(`Copied: ${code}`)
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) setFile(e.target.files[0])
    }

    const handleUpload = async () => {
        if (!file || !campaign) return
        setUploading(true)
        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()
            const res = await fetch(`/api/campaigns/${campaign.id}/modules`, {
                method: "POST",
                headers: { Authorization: `Bearer ${session?.access_token}` },
                body: (() => { const fd = new FormData(); fd.append("file", file); return fd })(),
            })
            if (res.ok) {
                const data = await res.json()
                toast.success(`Module Ingested: ${data.chunks} chunks indexed.`)
                setFile(null)
            } else {
                toast.error(`Upload Failed: ${await res.text()}`)
            }
        } catch {
            toast.error("Upload Error")
        } finally {
            setUploading(false)
        }
    }

    if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin text-purple-500" /></div>

    if (error) return (
        <div className="flex h-screen flex-col items-center justify-center gap-4 text-red-400">
            <ShieldAlert className="h-12 w-12" />
            <div>{error}</div>
            <Link href="/"><Button variant="outline">Back to Game</Button></Link>
        </div>
    )

    return (
        <div className="container mx-auto p-4 sm:p-6 space-y-6 max-w-5xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
                        God Mode
                    </h1>
                    <p className="text-muted-foreground text-sm">Campaign: {campaign?.name}</p>
                </div>
                <Link href="/">
                    <Button variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/10">
                        <LogOut className="mr-2 h-4 w-4" /> Exit
                    </Button>
                </Link>
            </div>

            {/* Row 1: SAM Tuner + Campaign Modules */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {campaign && (
                    <SamTuner campaignId={campaign.id} initialSettings={campaign.settings || {}} />
                )}

                <Card className="border-blue-500/20 bg-black/40">
                    <CardHeader>
                        <CardTitle className="text-blue-400 flex items-center gap-2">
                            <FileText className="h-5 w-5" /> Campaign Modules
                        </CardTitle>
                        <CardDescription>Upload PDF adventures for RAG.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid w-full items-center gap-1.5">
                            <Label htmlFor="module">Upload PDF / EPUB</Label>
                            <Input id="module" type="file" accept=".pdf,.epub" onChange={handleFileChange} disabled={uploading} className="cursor-pointer" />
                        </div>
                        <Button onClick={handleUpload} disabled={!file || uploading} className="w-full bg-blue-600 hover:bg-blue-700">
                            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                            {uploading ? "Ingesting..." : "Ingest Module"}
                        </Button>
                    </CardContent>
                </Card>
            </div>

            {/* Row 2: Invitations + Users */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Invitations */}
                <Card className="border-yellow-500/20 bg-black/40">
                    <CardHeader>
                        <CardTitle className="text-yellow-400 flex items-center gap-2">
                            <Ticket className="h-5 w-5" /> Invitations
                        </CardTitle>
                        <CardDescription>Generate invite codes for new players.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Generate */}
                        <div className="flex items-end gap-2">
                            <div className="flex-1">
                                <Label className="text-xs">Max uses</Label>
                                <Input
                                    type="number"
                                    value={newCodeMaxUses}
                                    onChange={(e) => setNewCodeMaxUses(parseInt(e.target.value) || 1)}
                                    min={1}
                                    max={100}
                                    className="h-8"
                                />
                            </div>
                            <Button onClick={handleGenerateCode} disabled={generating} size="sm" className="bg-yellow-600 hover:bg-yellow-700">
                                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate"}
                            </Button>
                        </div>

                        {/* Last generated code */}
                        {lastGeneratedCode && (
                            <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                                <span className="font-mono text-xl font-bold tracking-widest flex-1">{lastGeneratedCode}</span>
                                <Button size="sm" variant="ghost" onClick={() => copyCode(lastGeneratedCode)}>
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        )}

                        {/* List */}
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {invitations.length === 0 && <p className="text-xs text-muted-foreground">No invitations yet.</p>}
                            {invitations.map((inv) => {
                                const isExpired = inv.expires_at && new Date(inv.expires_at) < new Date()
                                const isUsedUp = inv.current_uses >= inv.max_uses
                                const statusColor = !inv.is_active || isExpired || isUsedUp
                                    ? "text-gray-500"
                                    : "text-green-400"

                                return (
                                    <div key={inv.id} className="flex items-center gap-2 text-sm p-2 rounded bg-muted/20">
                                        <button onClick={() => copyCode(inv.code)} className="font-mono font-bold tracking-wider hover:text-yellow-400" title="Copy">
                                            {inv.code}
                                        </button>
                                        <span className={`text-xs ${statusColor}`}>
                                            {inv.current_uses}/{inv.max_uses}
                                        </span>
                                        <span className="text-xs text-muted-foreground flex-1">
                                            {!inv.is_active ? "inactive" : isExpired ? "expired" : isUsedUp ? "used" : "active"}
                                        </span>
                                        {inv.is_active && !isExpired && !isUsedUp && (
                                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-400 hover:text-red-300" onClick={() => handleDeactivate(inv.id)}>
                                                <X className="h-3 w-3" />
                                            </Button>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>

                {/* Users */}
                <Card className="border-green-500/20 bg-black/40">
                    <CardHeader>
                        <CardTitle className="text-green-400 flex items-center gap-2">
                            <Users className="h-5 w-5" /> Players
                        </CardTitle>
                        <CardDescription>Registered users.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 max-h-80 overflow-y-auto">
                            {profiles.length === 0 && <p className="text-xs text-muted-foreground">No users found.</p>}
                            {profiles.map((p) => (
                                <div key={p.id} className="flex items-center gap-3 text-sm p-2 rounded bg-muted/20">
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium truncate">{p.username || "—"}</div>
                                        <div className="text-xs text-muted-foreground truncate">{p.email}</div>
                                    </div>
                                    <span className={`text-xs px-2 py-0.5 rounded ${
                                        p.role === "admin" ? "bg-purple-500/20 text-purple-400" : "bg-gray-500/20 text-gray-400"
                                    }`}>
                                        {p.role}
                                    </span>
                                    <span className={`text-xs px-2 py-0.5 rounded ${
                                        p.status === "approved" ? "bg-green-500/20 text-green-400"
                                            : p.status === "pending" ? "bg-yellow-500/20 text-yellow-400"
                                                : "bg-red-500/20 text-red-400"
                                    }`}>
                                        {p.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
