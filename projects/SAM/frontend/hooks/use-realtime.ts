import { useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase/client'

type RealtimeEvent = 'INSERT' | 'UPDATE' | 'DELETE' | '*'

interface UseRealtimeOptions {
    table: string
    event?: RealtimeEvent
    filter?: string
    schema?: string
    onData: (payload: any) => void
    enabled?: boolean
}

export function useRealtime({
    table,
    event = '*',
    filter,
    schema = 'public',
    onData,
    enabled = true
}: UseRealtimeOptions) {
    // Stable client ref — prevents re-subscribe on every render
    const supabaseRef = useRef(createClient())

    // Latest callback ref — avoids stale closures without re-subscribing
    const onDataRef = useRef(onData)
    useEffect(() => {
        onDataRef.current = onData
    }, [onData])

    useEffect(() => {
        if (!enabled) return

        const supabase = supabaseRef.current
        // Include filter in channel name so different filters get different channels
        const channelName = `rt:${table}:${event}:${filter || 'all'}`

        console.log(`🔌 Subscribing to ${channelName}`)

        const channel = supabase
            .channel(channelName)
            .on(
                'postgres_changes',
                {
                    event: event,
                    schema: schema,
                    table: table,
                    filter: filter
                },
                (payload: any) => {
                    console.log(`⚡ Realtime Event [${table}]:`, payload)
                    if (onDataRef.current) {
                        onDataRef.current(payload)
                    }
                }
            )
            .subscribe((status: any) => {
                console.log(`🔌 Subscription status [${channelName}]: ${status}`)
            })

        return () => {
            console.log(`🔌 Unsubscribing from ${channelName}`)
            supabase.removeChannel(channel)
        }
    }, [table, event, filter, schema, enabled])
}
