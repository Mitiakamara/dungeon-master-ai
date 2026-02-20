"use client"

import { useState, useEffect } from "react"
import { authenticatedFetch } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Brain, Skull, Sparkles, Zap } from "lucide-react"
import { toast } from "sonner"

interface SamTunerProps {
    campaignId: string
    initialSettings?: any
}

export function SamTuner({ campaignId, initialSettings = {} }: SamTunerProps) {
    const [settings, setSettings] = useState({
        difficulty: initialSettings.difficulty || 50, // 0-100 (Easy -> Deadly)
        creativity: initialSettings.creativity || 50, // 0-100 (Strict Rules -> Rule of Cool)
        lethality: initialSettings.lethality || false, // Enable character death?
        tone: initialSettings.tone || "balanced" // "grim", "heroic", "comedic"
    })
    const [saving, setSaving] = useState(false)

    const handleSave = async () => {
        setSaving(true)
        try {
            const res = await authenticatedFetch(`/api/campaigns/${campaignId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ settings })
            })
            if (res.ok) {
                toast.success("S.A.M. Recalibrated")
            } else {
                toast.error("Failed to update settings")
            }
        } catch (e) {
            console.error(e)
            toast.error("Connection Error")
        } finally {
            setSaving(false)
        }
    }

    return (
        <Card className="border-purple-500/20 bg-black/40">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-purple-400" />
                    S.A.M. Neural Tuner
                </CardTitle>
                <CardDescription>Adjust the AI Dungeon Master's personality and difficulty.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">

                {/* Difficulty Slider */}
                <div className="space-y-3">
                    <div className="flex justify-between">
                        <Label className="flex items-center gap-2"><Skull className="h-4 w-4" /> Difficulty</Label>
                        <span className="text-xs text-muted-foreground">{settings.difficulty}%</span>
                    </div>
                    <Slider
                        value={[settings.difficulty]}
                        onValueChange={(val) => setSettings({ ...settings, difficulty: val[0] })}
                        max={100} step={1}
                        className="py-2"
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground uppercase">
                        <span>Story Mode</span>
                        <span>Old School</span>
                        <span>TPK Likely</span>
                    </div>
                </div>

                {/* Creativity (Rule Adherence) */}
                <div className="space-y-3">
                    <div className="flex justify-between">
                        <Label className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Rule Adherence</Label>
                        <span className="text-xs text-muted-foreground">{settings.creativity}% (Creative)</span>
                    </div>
                    <Slider
                        value={[settings.creativity]}
                        onValueChange={(val) => setSettings({ ...settings, creativity: val[0] })}
                        max={100} step={1}
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground uppercase">
                        <span>Rules Lawyer</span>
                        <span>Balanced</span>
                        <span>Rule of Cool</span>
                    </div>
                </div>

                {/* Lethality Toggle */}
                <div className="flex items-center justify-between p-3 border rounded-lg bg-red-950/10 border-red-900/20">
                    <div className="space-y-0.5">
                        <Label className="text-red-400">Lethal Mode</Label>
                        <div className="text-[10px] text-muted-foreground">Allows S.A.M. to kill characters without confirmation.</div>
                    </div>
                    <Switch
                        checked={settings.lethality}
                        onCheckedChange={(c) => setSettings({ ...settings, lethality: c })}
                    />
                </div>

                <Button onClick={handleSave} disabled={saving} className="w-full bg-purple-600 hover:bg-purple-700">
                    {saving ? "Calibrating..." : "Update Neural Weights"}
                </Button>
            </CardContent>
        </Card>
    )
}
