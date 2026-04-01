import { useEffect, useState, useRef, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'

export function usePresence(campaignId: string | null, characterName: string | null) {
    const [onlineUsers, setOnlineUsers] = useState<Set<string>>(new Set())
    const channelRef = useRef<any>(null)

    useEffect(() => {
        if (!campaignId || !characterName) return

        const supabase = createClient()
        const channel = supabase.channel(`presence:${campaignId}`, {
            config: { presence: { key: characterName } }
        })

        channel.on('presence', { event: 'sync' }, () => {
            const state = channel.presenceState()
            const users = new Set<string>()
            Object.keys(state).forEach(key => users.add(key))
            setOnlineUsers(users)
        })

        channel.subscribe(async (status: string) => {
            if (status === 'SUBSCRIBED') {
                await channel.track({
                    character_name: characterName,
                    online_at: new Date().toISOString()
                })
            }
        })

        channelRef.current = channel

        return () => {
            channel.untrack()
            channel.unsubscribe()
            channelRef.current = null
        }
    }, [campaignId, characterName])

    const isOnline = useCallback((name: string) => onlineUsers.has(name), [onlineUsers])

    return { onlineUsers, isOnline }
}
