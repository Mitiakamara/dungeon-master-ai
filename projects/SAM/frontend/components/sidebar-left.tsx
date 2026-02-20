"use client"

import * as React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ShieldCheck } from "lucide-react"
import { ModeToggle } from "@/components/mode-toggle"
import { Commlink } from "@/components/commlink/commlink-dialog"
import { CharacterList } from "@/components/character-list"

interface SidebarLeftProps {
    refreshKey: number
    onSelectCharacter: (char: any) => void
    selectedId?: string
}

export function SidebarLeft({ refreshKey, onSelectCharacter, selectedId }: SidebarLeftProps) {
    return (
        <div className="flex flex-col h-full bg-muted/20 border-r">
            {/* Header Area */}
            <div className="flex h-14 items-center border-b px-4 gap-1 flex-shrink-0">
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

            {/* Character List (Scrollable) */}
            <div className="flex-1 overflow-hidden flex flex-col">
                <CharacterList
                    key={refreshKey}
                    onSelectCharacter={onSelectCharacter}
                    selectedId={selectedId}
                />
            </div>
        </div>
    )
}
