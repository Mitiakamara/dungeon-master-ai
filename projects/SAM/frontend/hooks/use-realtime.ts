import { useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

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
    const supabase = createClient()
    const router = useRouter()

    // [FIX] Use Ref to avoid stale closures without re-subscribing
    const onDataRef = useRef(onData)

    useEffect(() => {
        onDataRef.current = onData
    }, [onData])

    useEffect(() => {
        if (!enabled) return

        console.log(`🔌 Subscribing to ${table} (${event})`)

        const channel = supabase
            .channel(`public:${table}:${event}`)
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
                    // Call the latest callback
                    if (onDataRef.current) {
                        onDataRef.current(payload)
                    }
                }
            )
            .subscribe((status: any) => {
                console.log(`🔌 Subscription status [${table}]: ${status}`)
            })

        return () => {
            console.log(`🔌 Unsubscribing from ${table}`)
            supabase.removeChannel(channel)
        }
    }, [table, event, filter, schema, enabled, supabase])
}
