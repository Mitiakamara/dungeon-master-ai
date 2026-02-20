"use client"

import { useState, useEffect } from "react"
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
import { authenticatedFetch } from "@/lib/api"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface CharacterSheetDialogProps {
    character: any | null
    open: boolean
    onOpenChange: (open: boolean) => void
    onUpdate: () => void
    onDelete: () => void
}

export function CharacterSheetDialog({ character, open, onOpenChange, onUpdate, onDelete }: CharacterSheetDialogProps) {
    const [loading, setLoading] = useState(false)
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
    const [formData, setFormData] = useState<any>({
        name: "",
        race: "",
        class: "",
        level: 1,
        stats: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
        // Expanded Status Schema for D&D 5e
        status: {
            hp_current: 0, hp_max: 0, temp_hp: 0,
            ac: 10, speed: 30, initiative: 0, proficiency_bonus: 2,
            hit_dice: "1d8",
            xp: 0,
            senses: "", languages: "", proficiencies: "",
            actions: "", bonus_actions: "", reactions: "",
            attacks: "", // Text for legacy, Array objects for new
            inventory: "", spells: "",
            money: { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 },
            features: "", // New structured features
            saving_throws: {} // { str: true, dex: false }
        },
        bio: ""
    })

    // Helper to calculate mod
    const getMod = (score: number) => Math.floor((score - 10) / 2)

    useEffect(() => {
        if (character && open) {
            setFormData({
                name: character.name || "",
                race: character.race || "",
                class: character.class || "",
                level: character.level || 1,
                stats: character.stats || { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
                status: {
                    hp_current: character.status?.hp_current || 0,
                    hp_max: character.status?.hp_max || 10,
                    temp_hp: character.status?.temp_hp || 0,
                    ac: character.status?.ac || 10,
                    speed: character.status?.speed || 30,
                    initiative: character.status?.initiative || 0,
                    proficiency_bonus: character.status?.proficiency_bonus || 2,
                    hit_dice: character.status?.hit_dice || "1d8",
                    xp: character.status?.xp || 0,
                    senses: character.status?.senses || "",
                    languages: character.status?.languages || "",
                    proficiencies: character.status?.proficiencies || "",
                    actions: character.status?.actions || "",
                    bonus_actions: character.status?.bonus_actions || "",
                    reactions: character.status?.reactions || "",
                    attacks: character.status?.attacks || "",
                    inventory: character.status?.inventory || "",
                    spells: character.status?.spells || "",
                    money: character.status?.money || { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 },
                    features: character.status?.features || "",
                    saving_throws: character.status?.saving_throws || {}
                },
                bio: character.bio || ""
            })
        }
    }, [character, open])

    const handleSave = async () => {
        if (!character) return
        setLoading(true)
        try {
            const payload = {
                name: formData.name,
                level: formData.level,
                stats: formData.stats,
                status: formData.status,
                bio: formData.bio
            }

            const res = await authenticatedFetch(`/api/characters/${character.id}`, {
                method: "PATCH",
                body: JSON.stringify(payload)
            })

            if (!res.ok) throw new Error("Failed to update")

            onUpdate()
            onOpenChange(false)
        } catch (error) {
            console.error("Update failed", error)
        } finally {
            setLoading(false)
        }
    }

    if (!character) return null

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <div className="flex items-center justify-between mr-8">
                        <div>
                            <DialogTitle className="text-2xl">{formData.name}</DialogTitle>
                            <DialogDescription className="text-md">
                                {formData.race} {formData.class} (Lvl {formData.level})
                            </DialogDescription>
                        </div>
                        <div className="text-right text-xs text-muted-foreground">
                            XP: {formData.status.xp}
                        </div>
                    </div>
                </DialogHeader>

                <Tabs defaultValue="main" className="w-full mt-2">
                    <TabsList className="grid w-full grid-cols-5">
                        <TabsTrigger value="main">Stats & Saves</TabsTrigger>
                        <TabsTrigger value="combat">Combat & Attacks</TabsTrigger>
                        <TabsTrigger value="spells">Spells</TabsTrigger>
                        <TabsTrigger value="features">Features & Traits</TabsTrigger>
                        <TabsTrigger value="bio">Bio & Gear</TabsTrigger>
                    </TabsList>

                    {/* --- TAB: MAIN (Ability Scores, Saves, Proficiencies) --- */}
                    <TabsContent value="main" className="space-y-6 py-4">
                        <div className="grid grid-cols-6 gap-4">
                            {/* Ability Scores */}
                            {['str', 'dex', 'con', 'int', 'wis', 'cha'].map((stat) => {
                                const score = formData.stats[stat]
                                const mod = getMod(score)
                                const modString = mod >= 0 ? `+${mod}` : `${mod}`

                                return (
                                    <div key={stat} className="flex flex-col items-center border border-accent p-2 rounded-lg bg-card col-span-1">
                                        <span className="uppercase text-[10px] font-black tracking-widest text-muted-foreground mb-1">{stat}</span>
                                        <div className="text-2xl font-black">{score}</div>
                                        <div className={`text-sm font-bold ${mod >= 0 ? "text-green-500" : "text-red-500"}`}>{modString}</div>
                                    </div>
                                )
                            })}
                        </div>

                        <Separator />

                        <div className="grid grid-cols-2 gap-8">
                            {/* Saving Throws */}
                            <div className="space-y-2">
                                <Label className="text-base font-semibold">Saving Throws</Label>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    {['str', 'dex', 'con', 'int', 'wis', 'cha'].map((stat) => {
                                        const mod = getMod(formData.stats[stat])
                                        const isProficient = formData.status.saving_throws?.[stat]
                                        const totalSave = mod + (isProficient ? (formData.status.proficiency_bonus || 2) : 0)

                                        return (
                                            <div key={stat} className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`save-${stat}`}
                                                    checked={isProficient}
                                                    onCheckedChange={(checked) => setFormData({
                                                        ...formData,
                                                        status: {
                                                            ...formData.status,
                                                            saving_throws: { ...formData.status.saving_throws, [stat]: !!checked }
                                                        }
                                                    })}
                                                />
                                                <Label htmlFor={`save-${stat}`} className="uppercase w-8">{stat}</Label>
                                                <span className="font-mono font-bold">{totalSave >= 0 ? `+${totalSave}` : totalSave}</span>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>

                            {/* Core Stats */}
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-2">
                                    <div className="space-y-1">
                                        <Label className="text-[10px] text-muted-foreground uppercase tracking-tighter">Prof. Bonus</Label>
                                        <div className="flex h-10 w-full rounded-md border border-input bg-muted px-2 py-1 text-sm text-center font-bold items-center justify-center">
                                            +{formData.status.proficiency_bonus}
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-[10px] text-muted-foreground uppercase tracking-tighter">P. Perception</Label>
                                        <div className="flex h-10 w-full rounded-md border border-input bg-muted px-2 py-1 text-sm text-center font-bold items-center justify-center">
                                            {10 + getMod(formData.stats.wis)}
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-[10px] text-muted-foreground uppercase tracking-tighter">P. Investigation</Label>
                                        <div className="flex h-10 w-full rounded-md border border-input bg-muted px-2 py-1 text-sm text-center font-bold items-center justify-center">
                                            {10 + getMod(formData.stats.int)}
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-[10px] text-muted-foreground uppercase tracking-tighter">P. Insight</Label>
                                        <div className="flex h-10 w-full rounded-md border border-input bg-muted px-2 py-1 text-sm text-center font-bold items-center justify-center">
                                            {10 + getMod(formData.stats.wis)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </TabsContent>

                    {/* --- TAB: COMBAT (Attributes, Attacks) --- */}
                    <TabsContent value="combat" className="space-y-6 py-4">
                        {/* Vitals Row */}
                        <div className="flex gap-4 items-end">
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Armor Class</Label>
                                <div className="flex h-16 w-full rounded-md border border-input bg-muted px-3 py-2 text-2xl text-center font-black items-center justify-center">
                                    {formData.status.ac}
                                </div>
                            </div>
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Initiative</Label>
                                <div className="flex h-16 w-full rounded-md border border-input bg-muted px-3 py-2 text-2xl text-center font-black items-center justify-center">
                                    {formData.status.initiative >= 0 ? `+${formData.status.initiative}` : formData.status.initiative}
                                </div>
                            </div>
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Speed</Label>
                                <Input
                                    value={formData.status.speed}
                                    onChange={(e) => setFormData({ ...formData, status: { ...formData.status, speed: e.target.value } })} // allow string for "30ft, fly 10ft"
                                    className="text-center text-xl font-bold h-16"
                                />
                            </div>
                            <div className="flex-1 space-y-1">
                                <Label className="text-xs font-bold text-muted-foreground uppercase">Hit Dice</Label>
                                <Input
                                    value={formData.status.hit_dice}
                                    onChange={(e) => setFormData({ ...formData, status: { ...formData.status, hit_dice: e.target.value } })}
                                    className="text-center text-xl font-bold h-16"
                                />
                            </div>
                        </div>

                        {/* HP Row */}
                        <div className="grid grid-cols-3 gap-4 p-4 border rounded-xl bg-muted/20">
                            <div className="space-y-1">
                                <Label className="text-xs uppercase font-bold">Max HP</Label>
                                <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm text-center font-bold items-center justify-center">
                                    {formData.status.hp_max}
                                </div>
                            </div>
                            <div className="space-y-1">
                                <Label className="text-xs uppercase font-bold">Current HP</Label>
                                <Input
                                    type="number"
                                    value={formData.status.hp_current}
                                    className="text-red-500 font-bold text-lg"
                                    onChange={(e) => setFormData({ ...formData, status: { ...formData.status, hp_current: parseInt(e.target.value) || 0 } })}
                                />
                            </div>
                            <div className="space-y-1">
                                <Label className="text-xs uppercase font-bold">Temp HP</Label>
                                <Input
                                    type="number"
                                    value={formData.status.temp_hp}
                                    onChange={(e) => setFormData({ ...formData, status: { ...formData.status, temp_hp: parseInt(e.target.value) || 0 } })}
                                    className="text-blue-500"
                                />
                            </div>
                        </div>

                        {/* Attacks */}
                        <div className="space-y-2">
                            <Label className="text-base font-semibold">Weapon Attacks</Label>
                            {Array.isArray(formData.status.attacks) ? (
                                <div className="border rounded-xl overflow-hidden">
                                    <div className="grid grid-cols-12 bg-muted p-2 text-xs font-bold uppercase text-muted-foreground">
                                        <div className="col-span-4">Name</div>
                                        <div className="col-span-2 text-center">Bonus</div>
                                        <div className="col-span-6">Damage / Type</div>
                                    </div>
                                    <div className="divide-y">
                                        {formData.status.attacks.map((atk: any, i: number) => (
                                            <div key={i} className="grid grid-cols-12 p-3 text-sm items-center hover:bg-muted/10">
                                                <div className="col-span-4 font-bold">{atk.name}</div>
                                                <div className="col-span-2 text-center font-mono font-bold text-green-500">{atk.bonus}</div>
                                                <div className="col-span-6 font-mono text-xs">{atk.damage} {atk.type}</div>
                                            </div>
                                        ))}
                                    </div>
                                    {/* Fallback to Add Manual Attack if array is empty? For now just display. */}
                                </div>
                            ) : (
                                <Textarea
                                    className="font-mono text-sm min-h-[120px]"
                                    value={formData.status.attacks}
                                    onChange={(e) => setFormData({ ...formData, status: { ...formData.status, attacks: e.target.value } })}
                                    placeholder={`Dagger: +5 to hit, 1d4+3 piercing\nLongbow: +7 to hit, 1d8+3 piercing (Range 150/600)`}
                                />
                            )}
                        </div>
                    </TabsContent>

                    {/* --- TAB: SPELLS (New independent tab) --- */}
                    <TabsContent value="spells" className="space-y-4 py-4">
                        <DialogDescription className="text-xs text-muted-foreground italic mb-2">
                            Full list of prepared spells and available slots.
                        </DialogDescription>
                        {Array.isArray(formData.status.spells) ? (
                            <div className="border rounded-xl overflow-hidden flex flex-col h-[400px]">
                                <div className="grid grid-cols-12 bg-muted p-3 text-xs font-bold uppercase text-muted-foreground border-b shrink-0 sticky top-0">
                                    <div className="col-span-1">Lvl</div>
                                    <div className="col-span-3">Name</div>
                                    <div className="col-span-2">Time</div>
                                    <div className="col-span-2">Range</div>
                                    <div className="col-span-2">Duration</div>
                                    <div className="col-span-2">Effect/School</div>
                                </div>
                                <div className="divide-y overflow-y-auto flex-1">
                                    {formData.status.spells.map((spell: any, i: number) => {
                                        // Formatting Helper
                                        let levelDisplay = "Lvl " + spell.level
                                        if (String(spell.level).toLowerCase().includes("cantrip") || spell.level === 0 || spell.level === '0') {
                                            levelDisplay = "Cantrip"
                                        } else if (String(spell.level).toLowerCase().startsWith("lvl")) {
                                            levelDisplay = spell.level // Already has prefix
                                        }

                                        return (
                                            <div key={i} className="grid grid-cols-12 p-3 text-sm items-center hover:bg-muted/10">
                                                <div className="col-span-1 font-mono font-bold text-purple-500 text-xs">
                                                    {levelDisplay}
                                                </div>
                                                <div className="col-span-3 font-bold truncate pr-2" title={spell.name}>{spell.name}</div>
                                                <div className="col-span-2 text-xs text-muted-foreground">{spell.time || "-"}</div>
                                                <div className="col-span-2 text-xs text-muted-foreground">{spell.range || "-"}</div>
                                                <div className="col-span-2 text-xs text-muted-foreground">{spell.duration || "-"}</div>
                                                <div className="col-span-2 text-xs text-muted-foreground truncate" title={spell.notes}>
                                                    {spell.notes || spell.school || ""}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        ) : (
                            <Textarea
                                value={formData.status.spells}
                                onChange={(e) => setFormData({ ...formData, status: { ...formData.status, spells: e.target.value } })}
                                className="h-[400px]"
                                placeholder="Cantrips: ...&#10;Lvl 1 (4 slots): ..."
                            />
                        )}
                    </TabsContent>

                    {/* --- TAB: FEATURES (Actions, Reactions, Languages) --- */}
                    <TabsContent value="features" className="space-y-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Languages</Label>
                                <Textarea value={formData.status.languages} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, languages: e.target.value } })} className="h-20" />
                            </div>
                            <div className="space-y-2">
                                <Label>Proficiencies (Armor/Weapons)</Label>
                                <Textarea value={formData.status.proficiencies} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, proficiencies: e.target.value } })} className="h-20" />
                            </div>
                        </div>

                        {/* Bonus Actions Table */}
                        <div className="space-y-2">
                            <Label className="font-bold text-green-600">Bonus Actions</Label>
                            {Array.isArray(formData.status.bonus_actions) ? (
                                <div className="border rounded-xl overflow-hidden">
                                    <div className="grid grid-cols-12 bg-muted p-2 text-xs font-bold uppercase text-muted-foreground">
                                        <div className="col-span-3">Name</div>
                                        <div className="col-span-9">Effect</div>
                                    </div>
                                    <div className="divide-y">
                                        {formData.status.bonus_actions.map((item: any, i: number) => (
                                            <div key={i} className="grid grid-cols-12 p-3 text-sm items-center hover:bg-muted/10">
                                                <div className="col-span-3 font-bold">{item.name}</div>
                                                <div className="col-span-9 text-xs text-muted-foreground">{item.description}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <Textarea value={formData.status.bonus_actions} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, bonus_actions: e.target.value } })} placeholder="Cunning Action, Flurry of Blows..." />
                            )}
                        </div>

                        {/* Reactions Table */}
                        <div className="space-y-2">
                            <Label className="font-bold text-orange-600">Reactions</Label>
                            {Array.isArray(formData.status.reactions) ? (
                                <div className="border rounded-xl overflow-hidden">
                                    <div className="grid grid-cols-12 bg-muted p-2 text-xs font-bold uppercase text-muted-foreground">
                                        <div className="col-span-3">Name</div>
                                        <div className="col-span-9">Effect</div>
                                    </div>
                                    <div className="divide-y">
                                        {formData.status.reactions.map((item: any, i: number) => (
                                            <div key={i} className="grid grid-cols-12 p-3 text-sm items-center hover:bg-muted/10">
                                                <div className="col-span-3 font-bold">{item.name}</div>
                                                <div className="col-span-9 text-xs text-muted-foreground">{item.description}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <Textarea value={formData.status.reactions} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, reactions: e.target.value } })} placeholder="Opportunity Attack, Deflect Missiles..." />
                            )}
                        </div>

                        {/* Features Table */}
                        <div className="space-y-2">
                            <Label>Features & Trait Descriptions</Label>
                            {Array.isArray(formData.status.features) ? (
                                <div className="border rounded-xl overflow-hidden">
                                    <div className="grid grid-cols-12 bg-muted p-2 text-xs font-bold uppercase text-muted-foreground">
                                        <div className="col-span-3">Name</div>
                                        <div className="col-span-3">Source</div>
                                        <div className="col-span-6">Description</div>
                                    </div>
                                    <div className="divide-y">
                                        {formData.status.features.map((item: any, i: number) => (
                                            <div key={i} className="grid grid-cols-12 p-3 text-sm items-start hover:bg-muted/10">
                                                <div className="col-span-3 font-bold">{item.name}</div>
                                                <div className="col-span-3 text-xs italic text-muted-foreground">{item.source || "General"}</div>
                                                <div className="col-span-6 text-xs">{item.description}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <Textarea value={formData.status.actions} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, actions: e.target.value } })} className="min-h-[150px]" placeholder="Detailed descriptions of your abilities..." />
                            )}
                        </div>
                    </TabsContent>

                    {/* --- TAB: BIO (Lore, Gear) --- */}
                    <TabsContent value="bio" className="space-y-4 py-4">
                        <DialogDescription className="text-xs text-muted-foreground italic">
                            *Money affects your personal balance. Party loot is distributed automatically in the future.*
                        </DialogDescription>

                        <div className="grid grid-cols-2 gap-4">
                            {/* Bio */}
                            <div className="space-y-2">
                                <Label htmlFor="bio">Bio & Backstory</Label>
                                <Textarea
                                    id="bio"
                                    value={formData.bio}
                                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                                    className="h-40 whitespace-pre-wrap" // styling for newlines
                                />
                            </div>

                            {/* Wallet Row Moved here to balance layout if needed or kept below */}
                            <div className="space-y-2">
                                <Label>Inventory (Gear & Equipment)</Label>
                                {Array.isArray(formData.status.inventory) ? (
                                    <div className="border rounded-xl overflow-hidden h-64 overflow-y-auto">
                                        <div className="grid grid-cols-12 bg-muted p-2 text-xs font-bold uppercase text-muted-foreground sticky top-0">
                                            <div className="col-span-7">Item</div>
                                            <div className="col-span-2 text-center">Qty</div>
                                            <div className="col-span-3 text-right">Weight</div>
                                        </div>
                                        <div className="divide-y">
                                            {formData.status.inventory.map((item: any, i: number) => (
                                                <div key={i} className="grid grid-cols-12 p-2 text-sm items-center hover:bg-muted/10">
                                                    <div className="col-span-7 font-medium">{item.item}</div>
                                                    <div className="col-span-2 text-center text-xs">{item.qty}</div>
                                                    <div className="col-span-3 text-right text-xs text-muted-foreground">{item.weight}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <Textarea value={formData.status.inventory} onChange={(e) => setFormData({ ...formData, status: { ...formData.status, inventory: e.target.value } })} className="max-h-40" />
                                )}
                            </div>
                        </div>

                        {/* Wallet Row */}
                        <div className="p-3 bg-muted/20 border rounded-lg flex items-center justify-between gap-4">
                            <Label className="font-bold uppercase text-xs w-16">Wallet</Label>
                            <div className="flex gap-2 flex-1">
                                {['cp', 'sp', 'ep', 'gp', 'pp'].map((coin) => (
                                    <div key={coin} className="flex items-center gap-1 bg-background border px-2 py-1 rounded-md flex-1">
                                        <span className="uppercase text-[10px] font-bold text-muted-foreground">{coin}</span>
                                        <Input
                                            type="number"
                                            className="h-6 text-right text-xs border-none p-0 focus-visible:ring-0"
                                            value={formData.status.money?.[coin] || 0}
                                            onChange={(e) => setFormData({
                                                ...formData,
                                                status: {
                                                    ...formData.status,
                                                    money: { ...formData.status.money, [coin]: parseInt(e.target.value) || 0 }
                                                }
                                            })}
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    </TabsContent>

                </Tabs>

                <DialogFooter className="flex items-center justify-between sm:justify-between mt-4">
                    <Button variant="destructive" size="sm" onClick={() => setDeleteConfirmOpen(true)}>Delete Character</Button>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                        <Button onClick={handleSave} disabled={loading}>
                            {loading ? "Saving..." : "Save Character"}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>

            <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Character?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete <b>{formData.name}</b>. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => {
                            onDelete()
                            setDeleteConfirmOpen(false)
                        }} className="bg-red-600 hover:bg-red-700">Delete</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Dialog >
    )
}
