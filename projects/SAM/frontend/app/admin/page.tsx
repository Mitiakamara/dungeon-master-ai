"use client"

import { useEffect, useState } from "react"
import { authenticatedFetch } from "@/lib/api"
import { SamTuner } from "@/components/admin/sam-tuner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import Link from "next/link"
import { LogOut, Loader2, ShieldAlert, FileText, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

export default function AdminPage() {
    const [campaign, setCampaign] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Module Upload State
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)

    useEffect(() => {
        const fetchCampaign = async () => {
            try {
                // Determine active campaign. For prototype, we fetch list and pick first.
                const res = await authenticatedFetch('/api/campaigns/')
                if (res.ok) {
                    const data = await res.json()
                    if (data && data.length > 0) {
                        setCampaign(data[0]) // Pick first campaign
                    } else {
                        setError("No campaigns found. Create one first.")
                    }
                } else {
                    setError("Failed to fetch campaigns or unauthorized.")
                }
            } catch (e) {
                console.error(e)
                setError("Connection error.")
            } finally {
                setLoading(false)
            }
        }
        fetchCampaign()
    }, [])

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
        }
    }

    const handleUpload = async () => {
        if (!file || !campaign) return
        setUploading(true)

        const formData = new FormData()
        formData.append("file", file)

        try {
            // Safer: Use standard fetch + supabase session
            const { createClient } = require("@/lib/supabase/client")
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            const res = await fetch(`/api/campaigns/${campaign.id}/modules`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: formData
            })

            if (res.ok) {
                const data = await res.json()
                toast.success(`Module Ingested: ${data.chunks} chunks indexed.`)
                setFile(null)
            } else {
                const err = await res.text()
                toast.error(`Upload Failed: ${err}`)
            }

        } catch (e) {
            console.error(e)
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
        </div>
    )

    return (
        <div className="container mx-auto p-6 space-y-8 max-w-4xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
                        God Mode
                    </h1>
                    <p className="text-muted-foreground">Administering Campaign: {campaign.name}</p>
                </div>
                <Link href="/">
                    <Button variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/10 hover:text-red-300">
                        <LogOut className="mr-2 h-4 w-4" />
                        Exit God Mode
                    </Button>
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* S.A.M. Tuner */}
                <div className="md:col-span-1">
                    <SamTuner campaignId={campaign.id} initialSettings={campaign.settings || {}} />
                </div>

                {/* Other Modules Placeholders */}
                <div className="space-y-6">
                    <Card className="border-blue-500/20 bg-black/40">
                        <CardHeader>
                            <CardTitle className="text-blue-400 flex items-center gap-2">
                                <FileText className="h-5 w-5" />
                                Campaign Modules
                            </CardTitle>
                            <CardDescription>Upload PDF adventures to expand S.A.M.'s knowledge for this specific campaign.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid w-full max-w-sm items-center gap-1.5">
                                <Label htmlFor="module">Upload PDF / EPUB</Label>
                                <Input id="module" type="file" accept=".pdf,.epub" onChange={handleFileChange} disabled={uploading} className="cursor-pointer" />
                            </div>
                            <Button onClick={handleUpload} disabled={!file || uploading} className="w-full bg-blue-600 hover:bg-blue-700">
                                {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                                {uploading ? "Ingesting Knowledge..." : "Ingest Module"}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                * Files are indexed specifically for <b>{campaign.name}</b>.
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="border-green-500/20 bg-black/40 opacity-50 cursor-not-allowed">
                        <CardHeader>
                            <CardTitle className="text-green-400">User Management</CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm text-muted-foreground">
                            Manage players and bans.
                            <br /> (Coming Soon)
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
