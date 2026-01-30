"use client"

import * as React from "react"
import { ModeToggle } from "@/components/mode-toggle"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LogOut, Plus, Settings, User, Dices, ShieldCheck } from "lucide-react"
import { ProfileMenu } from "@/components/profile-menu"
import { DiceTray } from "@/components/dice-tray"
import { ChatInterface } from "@/components/chat-interface"
import { CharacterList } from "@/components/character-list"
import { CharacterCreateDialog } from "@/components/character-create-dialog"
import { Commlink } from "@/components/commlink/commlink-dialog"
import Link from "next/link"
import { useState } from "react"
import { createClient } from "@/lib/supabase/client"
import { useRealtime } from "@/hooks/use-realtime"

export default function GameLayout() {
    const [createOpen, setCreateOpen] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)

    const [selectedCharacter, setSelectedCharacter] = useState<any>(null)
    const [rollEvent, setRollEvent] = useState<string | null>(null)

    // [PHASE 13] Realtime Character Updates
    useRealtime({
        table: 'characters',
        event: 'UPDATE',
        onData: (payload: any) => {
            const newChar = payload.new
            console.log("⚡ Character Update Received:", newChar)

            // Only update if it matches our selected character
            if (selectedCharacter && newChar.id === selectedCharacter.id) {
                // Merge status updates safely
                setSelectedCharacter((prev: any) => ({
                    ...prev,
                    ...newChar,
                    status: {
                        ...prev.status,
                        ...(newChar.status || {})
                    }
                }))
            }
        }
    })

    // Persistence: Load on mount
    React.useEffect(() => {
        const saved = localStorage.getItem("selectedCharacter")
        if (saved) {
            try {
                setSelectedCharacter(JSON.parse(saved))
            } catch (e) {
                console.error("Failed to recover session character", e)
            }
        }
    }, [])

    const handleSelectCharacter = (char: any) => {
        if (char === 'NEW') {
            setCreateOpen(true)
        } else {
            setSelectedCharacter(char)
            localStorage.setItem("selectedCharacter", JSON.stringify(char))
        }
    }

    const handleCharacterUpdate = async (updates: any) => {
        if (!selectedCharacter) return

        console.log("Updating Character State:", updates)

        // 1. Optimistic UI Update (Deep merge for status)
        // If updates has 'status', merge it. If updates is just fields, merge them.
        // Backend returns "status": {"hp_current": X} structure as requested.

        const newStatus = { ...selectedCharacter.status, ...(updates.status || {}) }
        const updatedChar = {
            ...selectedCharacter,
            status: newStatus
        }

        setSelectedCharacter(updatedChar)
        localStorage.setItem("selectedCharacter", JSON.stringify(updatedChar))

        // 2. Persist to Backend
        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            await fetch(`/api/characters/${selectedCharacter.id}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.access_token}`
                },
                body: JSON.stringify(updates)
            })

        } catch (e) {
            console.error("Failed to persist HP update", e)
        }
    }

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background">
            {/* --- LEFT SIDEBAR: Characters & Nav --- */}
            <aside className="flex w-64 flex-col border-r bg-muted/20">
                <div className="flex h-14 items-center border-b px-4 gap-1">
                    <span className="font-bold text-sm mr-auto">S.A.M. Dashboard</span>

                    <Link href="/admin" title="Admin / God Mode">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-purple-400">
                            <ShieldCheck className="h-4 w-4" />
                        </Button>
                    </Link>

                    <div className="scale-90">
                        <Commlink />
                    </div>

                    <div className="scale-90">
                        <ModeToggle />
                    </div>
                </div>

                {/* Character List */}
                <CharacterList
                    key={refreshKey}
                    onSelectCharacter={handleSelectCharacter}
                    selectedId={selectedCharacter?.id}
                />

                {/* User Footer - MOVED TO RIGHT SIDEBAR */}
            </aside>

            {/* --- CENTER: Chat Area --- */}
            <main className="flex flex-1 flex-col overflow-hidden">
                <ChatInterface
                    selectedCharacter={selectedCharacter}
                    externalEvent={rollEvent}
                    onEventHandled={() => setRollEvent(null)}
                    onCharacterUpdate={handleCharacterUpdate}
                />
            </main>

            {/* --- RIGHT SIDEBAR: Tools & Dice --- */}
            <aside className="w-72 border-l bg-muted/20 p-4 hidden xl:flex flex-col">
                <div className="flex-1">
                    <DiceTray onRoll={(msg) => setRollEvent(msg)} />
                </div>

                <div className="mt-4 pt-4 border-t">
                    <div className="text-xs font-semibold text-muted-foreground mb-2 px-2">Player</div>
                    <ProfileMenu />
                </div>
            </aside>

            <CharacterCreateDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCharacterCreated={() => setRefreshKey(prev => prev + 1)}
            />
        </div>
    )
}
