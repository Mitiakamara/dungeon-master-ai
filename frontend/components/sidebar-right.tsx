"use client"

import * as React from "react"
import { DiceTray } from "@/components/dice-tray"
import { ProfileMenu } from "@/components/profile-menu"

interface SidebarRightProps {
    onRoll: (msg: string) => void
}

export function SidebarRight({ onRoll }: SidebarRightProps) {
    return (
        <div className="flex flex-col h-full bg-muted/20 border-l p-4">
            <div className="flex-1 overflow-y-auto">
                <DiceTray onRoll={onRoll} />
            </div>

            <div className="mt-4 pt-4 border-t flex-shrink-0">
                <div className="text-xs font-semibold text-muted-foreground mb-2 px-2">Player</div>
                <ProfileMenu />
            </div>
        </div>
    )
}
