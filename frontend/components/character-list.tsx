"use client"

import { useEffect, useState } from "react"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { User, Plus, Skull } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { authenticatedFetch } from "@/lib/api"

interface Character {
    id: string
    name: string
    class: string
    level: number
    image_url?: string
    status?: {
        xp?: number
        hp_current?: number
        hp_max?: number
        // ... other props
    }
}

// 5e XP Table helper
function getLevelProgress(xp: number = 0, level: number = 1) {
    // Current Level Flooring
    const levels = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000];
    const currentBase = levels[level - 1] || 0;
    const nextGoal = levels[level] || 355000;

    const needed = nextGoal - currentBase;
    const currentInLevel = xp - currentBase;

    let percent = (currentInLevel / needed) * 100;
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;

    return { percent, current: xp, next: nextGoal };
}

import { CharacterSheetDialog } from "@/components/character-sheet-dialog"
import { Settings, Trash2, Dices } from "lucide-react"
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

export function CharacterList({
    onSelectCharacter,
    selectedId
}: {
    onSelectCharacter: (char: any) => void,
    selectedId?: string
}) {
    const [characters, setCharacters] = useState<Character[]>([])
    const [loading, setLoading] = useState(true)
    const [userId, setUserId] = useState<string | null>(null)
    const [editingChar, setEditingChar] = useState<Character | null>(null)
    const supabase = createClient()

    useEffect(() => {
        const getUser = async () => {
            const { data: { user } } = await supabase.auth.getUser()
            if (user) {
                setUserId(user.id)
                fetchCharacters(user.id)
            } else {
                setLoading(false)
            }
        }
        getUser()

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event: string, session: any) => {
            if (session?.user) {
                setUserId(session.user.id)
                fetchCharacters(session.user.id)
            } else {
                setCharacters([])
                setUserId(null)
            }
        })
        return () => subscription.unsubscribe()
    }, [])

    const fetchCharacters = async (uid: string) => {
        setLoading(true)
        try {
            // Using backend endpoint
            const res = await authenticatedFetch(`/api/characters/user/me`)
            if (res.ok) {
                const data = await res.json()
                setCharacters(data)
            } else {
                console.error("Fetch characters failed:", res.status)
            }
        } catch (e) {
            console.error("Failed to fetch chars", e)
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/api/characters/${id}`, {
                method: 'DELETE'
            })
            if (res.ok) {
                if (userId) fetchCharacters(userId)
            }
        } catch (error) {
            console.error("Failed to delete", error)
        }
    }

    return (
        <div className="flex-1 flex flex-col min-h-0">
            <div className="px-4 py-2 flex items-center justify-between">
                <h2 className="text-lg font-semibold tracking-tight">Heroes</h2>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onSelectCharacter('NEW')}>
                    <Plus className="h-4 w-4" />
                </Button>
            </div>

            <ScrollArea className="flex-1">
                {loading ? (
                    <div className="p-4 text-sm text-muted-foreground">Loading roster...</div>
                ) : !userId ? (
                    <div className="p-4 text-sm text-muted-foreground">Log in to view heroes.</div>
                ) : (
                    <div className="px-4 space-y-1 pb-4">
                        {characters.length === 0 && (
                            <div className="text-sm text-muted-foreground text-center py-4">
                                No heroes found. <br /> Create one to begin.
                            </div>
                        )}

                        {characters.map((char: any) => {
                            const isSelected = char.id === selectedId
                            const hpCurrent = char.status?.hp_current ?? 0
                            const hpMax = char.status?.hp_max ?? 10
                            const ac = char.status?.ac ?? char.stats?.armor_class ?? 10

                            // Parse attacks safely
                            let attacks: any[] = []
                            if (char.status?.attacks && Array.isArray(char.status.attacks)) {
                                attacks = char.status.attacks
                            }

                            // Parse spells safely
                            let spells: any[] = []
                            if (char.status?.spells && Array.isArray(char.status.spells)) {
                                spells = char.status.spells
                            }

                            return (
                                <div key={char.id} className="flex flex-col gap-1 transition-all">
                                    <div className="flex gap-1 items-center group relative">
                                        <Button
                                            variant={isSelected ? "secondary" : "ghost"}
                                            className={`flex-1 justify-start h-auto py-2 px-3 pr-4 relative overflow-hidden ${isSelected ? 'bg-secondary' : ''}`}
                                            onClick={() => onSelectCharacter(char)}
                                        >
                                            <Avatar className="h-8 w-8 mr-2 z-10">
                                                <AvatarImage src={char.image_url} />
                                                <AvatarFallback><User className="h-4 w-4" /></AvatarFallback>
                                            </Avatar>
                                            <div className="flex flex-col items-start overflow-hidden z-10">
                                                <span className="text-sm font-medium truncate w-full text-left">{char.name}</span>
                                                <span className="text-xs text-muted-foreground truncate w-full text-left">
                                                    {char.class && typeof char.class === 'string' ? char.class.split('(')[0].trim() : 'Unknown'} Lvl {char.level}
                                                </span>
                                            </div>

                                            {/* Vertical XP Bar (Right Edge) */}
                                            <div className="absolute right-0 top-0 bottom-0 w-1.5 bg-background/20 mix-blend-overlay" title={`XP: ${char.status?.xp || 0}`}>
                                                <div
                                                    className="absolute bottom-0 left-0 right-0 bg-purple-500/80 transition-all duration-500"
                                                    style={{ height: `${getLevelProgress(char.status?.xp || 0, char.level).percent}%` }}
                                                />
                                            </div>
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-10 w-8 shrink-0 text-muted-foreground hover:text-foreground z-10"
                                            onClick={() => {
                                                setEditingChar(char)
                                                onSelectCharacter(char)
                                            }}
                                        >
                                            <Settings className="h-4 w-4" />
                                        </Button>
                                    </div>

                                    {/* MINI SHEET (Only if selected) */}
                                    {isSelected && (
                                        <div className="mx-1 mb-3 p-3 rounded-md bg-card border shadow-sm text-xs space-y-3 animate-in fade-in slide-in-from-top-1">
                                            {/* HP & AC Row */}
                                            <div className="flex items-center gap-2">
                                                <div className="flex flex-col flex-1 bg-secondary/30 rounded border border-border/50 p-1.5 justify-center items-center">
                                                    <span className="font-bold text-muted-foreground text-[10px] uppercase tracking-wider mb-0.5">Health</span>
                                                    <span className={`font-mono font-bold text-lg leading-none ${hpCurrent < hpMax / 2 ? "text-red-500" : "text-foreground"}`}>
                                                        {hpCurrent}/{hpMax}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col items-center justify-center w-[40px] bg-secondary/30 rounded border border-border/50 p-1.5">
                                                    <span className="text-[9px] text-muted-foreground uppercase font-bold">AC</span>
                                                    <span className="font-bold text-lg leading-none">{ac}</span>
                                                </div>
                                            </div>

                                            {/* Attacks Row */}
                                            {attacks.length > 0 && (
                                                <div className="pt-2 border-t border-border/50">
                                                    <div className="font-bold text-muted-foreground text-[10px] uppercase tracking-wider mb-2">Ready Attacks</div>
                                                    <div className="space-y-1">
                                                        {attacks.slice(0, 3).map((atk: any, i: number) => {
                                                            const name = typeof atk === 'string' ? atk : atk.name;
                                                            return (
                                                                <div key={i} className="flex items-center justify-between px-2 py-1.5 bg-muted/50 rounded hover:bg-muted transition-colors border border-transparent hover:border-border">
                                                                    <span className="font-medium truncate max-w-[120px]">{name}</span>
                                                                    <Dices className="h-3 w-3 text-muted-foreground opacity-50" />
                                                                </div>
                                                            )
                                                        })}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Spells Row */}
                                            {spells && spells.length > 0 && (
                                                <div className="pt-2 border-t border-border/50">
                                                    <div className="font-bold text-muted-foreground text-[10px] uppercase tracking-wider mb-2">Spells Prepared</div>
                                                    <div className="space-y-1">
                                                        {spells.slice(0, 4).map((spell: any, i: number) => {
                                                            const isCantrip = String(spell.level).toLowerCase().includes("cantrip") || spell.level === 0 || spell.level === '0'
                                                            return (
                                                                <div key={i} className="flex items-center justify-between px-2 py-1.5 bg-muted/50 rounded hover:bg-muted transition-colors border border-transparent hover:border-border">
                                                                    <span className="font-medium truncate max-w-[100px]">{spell.name}</span>
                                                                    <span className="text-[10px] text-muted-foreground uppercase">{isCantrip ? 'Cantrip' : String(spell.level).startsWith('Lvl') ? spell.level : `Lvl ${spell.level}`}</span>
                                                                </div>
                                                            )
                                                        })}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                )}
            </ScrollArea>

            <CharacterSheetDialog
                open={!!editingChar}
                character={editingChar}
                onOpenChange={(open) => !open && setEditingChar(null)}
                onUpdate={() => userId && fetchCharacters(userId)}
                onDelete={() => {
                    if (editingChar) handleDelete(editingChar.id)
                    setEditingChar(null) // Close dialog
                }}
            />
        </div>
    )
}
