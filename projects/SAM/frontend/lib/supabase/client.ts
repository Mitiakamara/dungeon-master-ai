import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!url || !key) {
        // Log warning but don't crash during build if merely static generation
        console.warn("Missing Supabase Env Vars")
        // Return a mocked client to satisfy build-time renders
        return {
            auth: {
                getSession: async () => ({ data: { session: null }, error: null }),
                getUser: async () => ({ data: { user: null }, error: null }),
                onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
                signInWithOAuth: async () => { },
                signOut: async () => { },
            }
        } as any
    }

    return createBrowserClient(url, key)
}
