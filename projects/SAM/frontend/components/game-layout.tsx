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
import { authenticatedFetch } from "@/lib/api"
import { useRealtime } from "@/hooks/use-realtime"

import { SidebarLeft } from "@/components/sidebar-left"
import { usePresence } from "@/hooks/use-presence"
import { SidebarRight } from "@/components/sidebar-right"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"

export default function GameLayout() {
    const [createOpen, setCreateOpen] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)

    const [selectedCharacter, setSelectedCharacter] = useState<any>(null)
    const [rollEvent, setRollEvent] = useState<string | null>(null)
    const [isGM, setIsGM] = useState(false)
    const [campaignName, setCampaignName] = useState<string>("")
    const [currentUserId, setCurrentUserId] = useState<string>("")
    const [combatState, setCombatState] = useState<any>(null)
    const [diceSheetOpen, setDiceSheetOpen] = useState(false)

    // Derived campaign ID from selected character
    const campaignId = selectedCharacter?.campaign_id || ""

    // Presence tracking
    const { isOnline } = usePresence(campaignId || null, selectedCharacter?.name ?? null)

    // Get current user ID on mount
    React.useEffect(() => {
        const supabase = createClient()
        supabase.auth.getUser().then(({ data: { user } }: { data: { user: any } }) => {
            if (user) setCurrentUserId(user.id)
        })
    }, [])

    // Reusable: fetch campaign info (name + GM check + combat state)
    const fetchCampaignInfo = React.useCallback(async () => {
        if (!campaignId) {
            setIsGM(false)
            setCampaignName("")
            return
        }
        try {
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) return

            const res = await authenticatedFetch(`/api/campaigns/${campaignId}`)
            if (res.ok) {
                const campaign = await res.json()
                setIsGM(campaign.gm_id === user.id)
                setCampaignName(campaign.name || "")
                setCombatState(campaign.settings?.combat || null)
            } else {
                setIsGM(false)
                setCampaignName("")
            }
        } catch (err) {
            console.error("🔑 GM Check failed:", err)
            setIsGM(false)
            setCampaignName("")
        }
    }, [campaignId])

    // Reusable: fetch fresh character data from backend
    const fetchCharacterData = React.useCallback(async (charId: string) => {
        try {
            const res = await authenticatedFetch(`/api/characters/${charId}`)
            if (res.ok) {
                const freshChar = await res.json()
                console.log("🔄 Synced Fresh Character Data:", freshChar)
                setSelectedCharacter(freshChar)
                localStorage.setItem("selectedCharacter", JSON.stringify(freshChar))
            }
        } catch (err) {
            console.warn("Character resync failed:", err)
        }
    }, [])

    // Fetch campaign info when campaign changes
    React.useEffect(() => {
        fetchCampaignInfo()
    }, [fetchCampaignInfo])

    // Re-sync character + campaign when returning from background
    const lastGameSyncRef = React.useRef<number>(0)
    React.useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                const now = Date.now()
                if (now - lastGameSyncRef.current < 5000) return
                lastGameSyncRef.current = now
                console.log('🔄 Tab visible, re-syncing character and campaign data...')
                if (selectedCharacter?.id) fetchCharacterData(selectedCharacter.id)
                if (campaignId) fetchCampaignInfo()
            }
        }
        document.addEventListener('visibilitychange', handleVisibilityChange)
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
    }, [selectedCharacter?.id, campaignId, fetchCharacterData, fetchCampaignInfo])

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

    // Realtime Combat State Updates (campaigns table)
    useRealtime({
        table: 'campaigns',
        event: 'UPDATE',
        enabled: !!campaignId,
        onData: (payload: any) => {
            if (payload.new?.id === campaignId) {
                const combat = payload.new.settings?.combat || null
                console.log("⚔️ Combat state update:", combat)
                setCombatState(combat)
            }
        }
    })

    // Re-sync character data when a SAM message is processed in the chat-interface
    // listener. We piggyback on the existing useRealtime for `messages` instead of
    // creating a second subscription on the same table (which can collide channels).
    const handleSamMessageReceived = React.useCallback(() => {
        if (!selectedCharacter?.id) return
        const charId = selectedCharacter.id
        // Delay so the backend finishes applying state_updates before we re-fetch
        setTimeout(() => fetchCharacterData(charId), 1500)
    }, [selectedCharacter?.id, fetchCharacterData])

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
        <div className="flex flex-col md:flex-row h-[100dvh] w-full overflow-hidden bg-background">

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
                            campaignId={selectedCharacter?.campaign_id}
                            isGM={isGM}
                            currentUserId={currentUserId}
                            isOnline={isOnline}
                        />
                    </SheetContent>
                </Sheet>

                <div className="font-bold text-sm">S.A.M. Mobile</div>

                {/* 2. Right Dice Sheet */}
                <Sheet open={diceSheetOpen} onOpenChange={setDiceSheetOpen}>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon">
                            <Dices className="h-5 w-5" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="right" className="p-0 w-[300px]">
                        <SidebarRight
                            onRoll={(msg) => {
                                setRollEvent(msg)
                                // Auto-close on mobile after rolling
                                setTimeout(() => setDiceSheetOpen(false), 500)
                            }}
                            characterName={selectedCharacter?.name}
                        />
                    </SheetContent>
                </Sheet>
            </header>

            {/* --- DESKTOP LEFT SIDEBAR (Hidden on mobile) --- */}
            <aside className="hidden md:flex w-64 flex-col border-r bg-muted/20 shrink-0">
                <SidebarLeft
                    refreshKey={refreshKey}
                    onSelectCharacter={handleSelectCharacter}
                    selectedId={selectedCharacter?.id}
                    campaignId={selectedCharacter?.campaign_id}
                    isGM={isGM}
                    currentUserId={currentUserId}
                    isOnline={isOnline}
                />
            </aside>

            {/* --- CENTER: Chat Area --- */}
            <main className="flex flex-1 flex-col overflow-hidden relative">
                <ChatInterface
                    selectedCharacter={selectedCharacter}
                    campaignId={campaignId}
                    campaignName={campaignName}
                    isGM={isGM}
                    combatState={combatState}
                    externalEvent={rollEvent}
                    onEventHandled={() => setRollEvent(null)}
                    onCharacterUpdate={handleCharacterUpdate}
                    onSamMessageReceived={handleSamMessageReceived}
                />
            </main>

            {/* --- DESKTOP RIGHT SIDEBAR (Hidden on mobile) --- */}
            <aside className="hidden xl:flex w-72 flex-col border-l bg-muted/20 shrink-0">
                <SidebarRight onRoll={(msg) => setRollEvent(msg)} characterName={selectedCharacter?.name} />
            </aside>

            <CharacterCreateDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCharacterCreated={() => setRefreshKey(prev => prev + 1)}
                campaignId={campaignId}
            />
        </div>
    )
}
