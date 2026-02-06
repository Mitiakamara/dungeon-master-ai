"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { createClient } from "@/lib/supabase/client"
import { authenticatedFetch } from "@/lib/api"

interface CharacterCreateDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    onCharacterCreated: () => void
}

export function CharacterCreateDialog({ open, onOpenChange, onCharacterCreated }: CharacterCreateDialogProps) {
    const [loading, setLoading] = useState(false)
    const [formData, setFormData] = useState({
        name: "",
        race: "",
        class: "",
        bio: "",
        level: 1,
        stats: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
        status: {},
        image_url: ""
    })

    const supabase = createClient()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)

        try {
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) throw new Error("No user")

            // Minimal payload expecting backend to handle 'stats' defaults if empty
            // Backend expects: name, race, class (mapped to class_), user_id, campaign_id
            const payload = {
                ...formData,
                user_id: user.id,
                campaign_id: "d71c97be-d54f-40e6-89ad-2b6bd32371d6", // Default "Solo Adventure" Campaign
            }

            const res = await authenticatedFetch("/api/characters/", {
                method: "POST",
                body: JSON.stringify(payload)
            })

            if (!res.ok) throw new Error("Failed to create")

            onCharacterCreated()
            onOpenChange(false)
            setFormData({
                name: "",
                race: "",
                class: "",
                bio: "",
                level: 1,
                stats: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
                status: {},
                image_url: ""
            }) // Reset
        } catch (error: any) {
            console.error(error)
            alert(`Error creating character: ${error.message || "Unknown error"}`)
        } finally {
            setLoading(false)
        }
    }

    const [activeTab, setActiveTab] = useState("manual")

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setLoading(true)
        try {
            const formData = new FormData()
            formData.append("file", file)

            const res = await authenticatedFetch("/api/characters/import", {
                method: "POST",
                body: formData
            })

            if (!res.ok) throw new Error("Import failed")

            const data = await res.json()
            // Pre-fill form with imported data
            setFormData(prev => ({
                ...prev,
                name: data.name || "",
                race: data.race || "",
                class: data.class || "",
                bio: data.bio || "",
                level: data.level || 1,
                stats: data.stats || prev.stats,
                status: data.status || {},
                image_url: data.image_url || "" // Capture generated avatar
            }))

            // Switch to manual tab for review
            setActiveTab("manual")
        } catch (error) {
            console.error("PDF Import Error:", error)
            alert("Failed to parse PDF. Please try again or fill manually.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Create New Hero</DialogTitle>
                    <DialogDescription>
                        Import a D&D Beyond PDF or create manually.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex gap-4 border-b mb-4">
                    <Button variant={activeTab === "manual" ? "default" : "ghost"} onClick={() => setActiveTab("manual")} className="rounded-b-none">
                        Manual Entry
                    </Button>
                    <Button variant={activeTab === "pdf" ? "default" : "ghost"} onClick={() => setActiveTab("pdf")} className="rounded-b-none">
                        Import PDF
                    </Button>
                </div>

                {activeTab === "pdf" ? (
                    <div className="py-8 flex flex-col items-center justify-center border-2 border-dashed rounded-xl bg-muted/20">
                        <Label htmlFor="pdf-upload" className="cursor-pointer flex flex-col items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
                            <span className="text-4xl">📄</span>
                            <span className="font-medium">Click to Upload D&D Beyond PDF</span>
                        </Label>
                        <Input
                            id="pdf-upload"
                            type="file"
                            accept=".pdf"
                            className="hidden"
                            onChange={handleFileChange}
                            disabled={loading}
                        />
                        {loading && <p className="mt-4 text-sm animate-pulse text-yellow-500">S.A.M. is reading your sheet...</p>}
                    </div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div className="grid gap-4 py-4">
                            {/* Existing Form Fields */}
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label className="text-right">Avatar</Label>
                                <div className="col-span-3 flex items-center gap-4">
                                    {formData.image_url ? (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img src={formData.image_url} alt="Avatar" className="h-12 w-12 rounded-full border bg-muted" />
                                    ) : (
                                        <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-xs text-muted-foreground">?</div>
                                    )}
                                    <span className="text-xs text-muted-foreground">{formData.image_url ? "Auto-generated from Race/Class" : "No avatar"}</span>
                                </div>
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="name" className="text-right">Name</Label>
                                <Input id="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="col-span-3" required />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="race" className="text-right">Race</Label>
                                <Input id="race" value={formData.race} onChange={(e) => setFormData({ ...formData, race: e.target.value })} className="col-span-3" placeholder="Human, Elf..." />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="class" className="text-right">Class</Label>
                                <Input id="class" value={formData.class} onChange={(e) => setFormData({ ...formData, class: e.target.value })} className="col-span-3" placeholder="Fighter Lvl 1..." />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="bio" className="text-right">Bio</Label>
                                <Textarea id="bio" value={formData.bio} onChange={(e) => setFormData({ ...formData, bio: e.target.value })} className="col-span-3 h-32" placeholder="Backstory and key items..." />
                            </div>
                        </div>
                        <DialogFooter className="flex-col sm:justify-between sm:flex-row gap-2">
                            {Object.keys((formData as any).status || {}).length > 0 && (
                                <div className="text-xs text-green-500 flex items-center gap-1">
                                    <span>✅ PDF Data Loaded (Inventory, Spells, Traits)</span>
                                </div>
                            )}
                            <Button type="submit" disabled={loading}>
                                {loading ? "Creating..." : "Create Character"}
                            </Button>
                        </DialogFooter>
                    </form>
                )}
            </DialogContent>
        </Dialog>
    )
}
