import { useEffect, useState, useRef, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'

interface TypingUser {
    characterName: string
    timestamp: number
}

export function useTypingIndicator(campaignId: string | null, myCharacterName: string | null) {
    const [typingUsers, setTypingUsers] = useState<Map<string, TypingUser>>(new Map())
    const channelRef = useRef<any>(null)
    const lastSentRef = useRef<number>(0)

    // Clean up stale typing indicators (older than 4 seconds)
    useEffect(() => {
        const interval = setInterval(() => {
            setTypingUsers(prev => {
                const now = Date.now()
                const next = new Map(prev)
                let changed = false
                for (const [key, value] of next) {
                    if (now - value.timestamp > 4000) {
                        next.delete(key)
                        changed = true
                    }
                }
                return changed ? next : prev
            })
        }, 1000)
        return () => clearInterval(interval)
    }, [])

    // Subscribe to broadcast channel
    useEffect(() => {
        if (!campaignId) return

        const supabase = createClient()
        const channel = supabase.channel(`typing:${campaignId}`, {
            config: { broadcast: { self: false } }
        })

        channel.on('broadcast', { event: 'typing' }, (payload: any) => {
            const { characterName } = payload.payload
            if (characterName && characterName !== myCharacterName) {
                setTypingUsers(prev => {
                    const next = new Map(prev)
                    next.set(characterName, { characterName, timestamp: Date.now() })
                    return next
                })
            }
        })

        channel.subscribe()
        channelRef.current = channel

        return () => {
            channel.unsubscribe()
            channelRef.current = null
        }
    }, [campaignId, myCharacterName])

    // Send typing event (throttled — max once per 2 seconds)
    const sendTyping = useCallback(() => {
        if (!channelRef.current || !myCharacterName) return
        const now = Date.now()
        if (now - lastSentRef.current < 2000) return
        lastSentRef.current = now

        channelRef.current.send({
            type: 'broadcast',
            event: 'typing',
            payload: { characterName: myCharacterName }
        })
    }, [myCharacterName])

    const typingNames = Array.from(typingUsers.values()).map(u => u.characterName)

    return { typingNames, sendTyping }
}
