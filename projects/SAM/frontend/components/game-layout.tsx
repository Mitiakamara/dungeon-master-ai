"use client"

import * as React from "react"
import { ModeToggle } from "@/components/mode-toggle"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LogOut, Plus, Settings, User, Dices, ShieldCheck, Menu } from "lucide-react"
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

import { SidebarLeft } from "@/components/sidebar-left"
import { SidebarRight } from "@/components/sidebar-right"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"

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
                setSelectedCharacter((prev: any) => {
                    const updated = {
                        ...prev,
                        ...newChar,
                        status: {
                            ...prev.status,
                            ...(newChar.status || {})
                        }
                    };

                    // [FIX] Update Storage Immediately to prevent Desync
                    localStorage.setItem("selectedCharacter", JSON.stringify(updated));

                    return updated;
                })
            }
        }
    })

    // Persistence & Fresh Data: Load on mount
    React.useEffect(() => {
        const loadCharacter = async () => {
            const savedStr = localStorage.getItem("selectedCharacter")
            if (!savedStr) return

            let savedChar: any = null
            try {
                savedChar = JSON.parse(savedStr)
            } catch (e) {
                console.error("Failed to parse local character", e)
                return
            }

            if (!savedChar?.id) return

            // 1. Initial Load from Local (Instant UI)
            setSelectedCharacter(savedChar)

            // 2. Fetch Fresh Data from Backend (Source of Truth)
            // This fixes "Ghost HP" after server-side resets
            try {
                const supabase = createClient()
                const { data: { session } } = await supabase.auth.getSession()

                if (session?.access_token) {
                    const res = await fetch(`/api/characters/${savedChar.id}`, {
                        headers: {
                            Authorization: `Bearer ${session.access_token}`
                        }
                    })

                    if (res.ok) {
                        const freshChar = await res.json()
                        console.log("🔄 Synced Fresh Character Data:", freshChar)
                        setSelectedCharacter(freshChar)
                        localStorage.setItem("selectedCharacter", JSON.stringify(freshChar))
                    }
                }
            } catch (err) {
                console.warn("Using local cache only (Server unreachable)", err)
            }
        }

        loadCharacter()
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
        <div className="flex flex-col md:flex-row h-screen w-full overflow-hidden bg-background">

            {/* --- MOBILE HEADER (Visible only on small screens) --- */}
            <header className="flex md:hidden h-14 items-center justify-between border-b px-4 bg-muted/40 shrink-0">

                {/* 1. Left Menu Sheet */}
                <Sheet>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon">
                            <Menu className="h-5 w-5" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="p-0 w-[300px]">
                        <SidebarLeft
                            refreshKey={refreshKey}
                            onSelectCharacter={handleSelectCharacter}
                            selectedId={selectedCharacter?.id}
                        />
                    </SheetContent>
                </Sheet>

                <div className="font-bold text-sm">S.A.M. Mobile</div>

                {/* 2. Right Dice Sheet */}
                <Sheet>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon">
                            <Dices className="h-5 w-5" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" className="p-0 w-[300px]">
                        <SidebarRight onRoll={(msg) => setRollEvent(msg)} />
                    </SheetContent>
                </Sheet>
            </header>

            {/* --- DESKTOP LEFT SIDEBAR (Hidden on mobile) --- */}
            <aside className="hidden md:flex w-64 flex-col border-r bg-muted/20 shrink-0">
                <SidebarLeft
                    refreshKey={refreshKey}
                    onSelectCharacter={handleSelectCharacter}
                    selectedId={selectedCharacter?.id}
                />
            </aside>

            {/* --- CENTER: Chat Area --- */}
            <main className="flex flex-1 flex-col overflow-hidden relative">
                <ChatInterface
                    selectedCharacter={selectedCharacter}
                    externalEvent={rollEvent}
                    onEventHandled={() => setRollEvent(null)}
                    onCharacterUpdate={handleCharacterUpdate}
                />
            </main>

            {/* --- DESKTOP RIGHT SIDEBAR (Hidden on mobile) --- */}
            <aside className="hidden xl:flex w-72 flex-col border-l bg-muted/20 shrink-0">
                <SidebarRight onRoll={(msg) => setRollEvent(msg)} />
            </aside>

            <CharacterCreateDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCharacterCreated={() => setRefreshKey(prev => prev + 1)}
            />
        </div>
    )
}
