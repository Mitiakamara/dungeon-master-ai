import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
    const cookieStore = await cookies()

    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return cookieStore.getAll()
                },
                setAll(cookiesToSet) {
                    console.log("Supabase Adapter: setAll called with", cookiesToSet.length, "cookies")
                    cookiesToSet.forEach(({ name, value, options }) => {
                        console.log(`Supabase Adapter: Setting cookie [${name}]`, options)
                        // Force options for localhost compatibility
                        cookieStore.set(name, value, {
                            ...options,
                            sameSite: 'lax',
                            secure: process.env.NODE_ENV === 'production',
                            httpOnly: false,
                            path: '/',
                        })
                    })
                },
            },
        }
    )
}
