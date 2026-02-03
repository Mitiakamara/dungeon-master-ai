"use client"

import { useEffect, useState } from "react"
import { authenticatedFetch } from "@/lib/api"
import { SamTuner } from "@/components/admin/sam-tuner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import Link from "next/link"
import { LogOut, Loader2, ShieldAlert, FileText, Upload } from "lucide-react"

// ... imports remain the same ...

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
