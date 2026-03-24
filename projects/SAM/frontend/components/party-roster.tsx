"use client"

import { useEffect, useState } from "react"
import { Users } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { authenticatedFetch } from "@/lib/api"

interface PartyMember {
    id: string
    name: string
    class: string
    level: number
    image_url?: string
    user_id: string
    status?: {
        hp_current?: number
        hp_max?: number
    }
}

function HpColor(current: number, max: number): string {
    if (max <= 0) return "text-muted-foreground"
    const ratio = current / max
    if (ratio > 0.5) return "text-green-500"
    if (ratio > 0.25) return "text-yellow-500"
    return "text-red-500"
}

export function PartyRoster({ campaignId, currentUserId }: { campaignId?: string; currentUserId?: string }) {
    const [party, setParty] = useState<PartyMember[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!campaignId || !currentUserId) { setParty([]); return }

        const fetchParty = async () => {
            setLoading(true)
            try {
                const res = await authenticatedFetch(`/api/characters/campaign/${campaignId}`)
                if (res.ok) {
                    const data: PartyMember[] = await res.json()
                    setParty(data.filter((c) => c.user_id !== currentUserId))
                }
            } catch (e) {
                console.error("Failed to fetch party:", e)
            } finally {
                setLoading(false)
            }
        }
        fetchParty()
    }, [campaignId, currentUserId])

    if (!campaignId) return null

    return (
        <div className="px-3 py-2">
            <div className="flex items-center gap-1.5 mb-2">
                <Users className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Party</span>
            </div>

            {loading ? (
                <p className="text-xs text-muted-foreground animate-pulse px-1">Loading...</p>
            ) : party.length === 0 ? (
                <p className="text-xs text-muted-foreground italic px-1">No other heroes in this campaign</p>
            ) : (
                <div className="space-y-1.5">
                    {party.map((member) => {
                        const hpCurrent = member.status?.hp_current ?? 0
                        const hpMax = member.status?.hp_max ?? 0

                        return (
                            <div key={member.id} className="flex items-center gap-2 px-1 py-1 rounded-md hover:bg-muted/50 transition-colors">
                                <Avatar className="h-7 w-7 border border-blue-500/30">
                                    <AvatarFallback className="text-[10px]">{member.name?.[0]?.toUpperCase() || "?"}</AvatarFallback>
                                    <AvatarImage src={member.image_url} />
                                </Avatar>
                                <div className="flex-1 min-w-0">
                                    <div className="text-xs font-medium truncate">{member.name}</div>
                                    <div className="text-[10px] text-muted-foreground truncate">
                                        {member.class} Lvl {member.level}
                                    </div>
                                </div>
                                {hpMax > 0 && (
                                    <span className={`text-[10px] font-mono font-medium ${HpColor(hpCurrent, hpMax)}`}>
                                        {hpCurrent}/{hpMax}
                                    </span>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
