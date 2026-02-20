"use client"

import { useEffect, useState } from "react"
import { createClient } from "@/lib/supabase/client"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { LogOut, User } from "lucide-react"

export function ProfileMenu() {
    const [user, setUser] = useState<any>(null)
    const supabase = createClient()

    const [debugCookie, setDebugCookie] = useState<string>('Checking...')
    const [authError, setAuthError] = useState<string | null>(null)

    useEffect(() => {
        // Fetch initial session
        const initSession = async () => {
            try {
                const { data: { session }, error } = await supabase.auth.getSession()
                if (error) {
                    console.error("Session Error:", error)
                    setAuthError(error.message)
                }
                if (session) {
                    console.log("Initial session found:", session.user.email)
                    setUser(session.user)
                } else {
                    console.log("No session from getSession(), trying getUser()...")
                    // Fallback to getUser() which validates against the server
                    const { data: { user: userFromGet }, error: userError } = await supabase.auth.getUser()
                    if (userError) {
                        console.error("User Error:", userError)
                        setAuthError(userError.message)
                    }
                    if (userFromGet) {
                        console.log("User found via getUser:", userFromGet.email)
                        setUser(userFromGet)
                    }
                }
            } catch (err: any) {
                setAuthError(err.toString())
            }
        }
        initSession()

        // Debug Cookie Check (Client-side only)
        if (typeof document !== 'undefined') {
            const cookies = document.cookie.split(';').map(c => c.trim())
            const sbCookies = cookies.filter(c => c.startsWith('sb-')).map(c => c.split('=')[0])

            const storeCookie = cookies.find(c => c.startsWith('manual-store-cookie=')) ? 'Store: Found' : 'Store: Missing'
            const respCookie = cookies.find(c => c.startsWith('manual-response-cookie=')) ? 'Response: Found' : 'Response: Missing'

            setDebugCookie((sbCookies.length > 0 ? sbCookies.join(', ') : 'Auth: Missing') + ' | ' + storeCookie + ' | ' + respCookie)
        }

        // Check URL params for debug info
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search)
            const errorParam = params.get('error')
            const debugParam = params.get('debug_auth')
            if (errorParam) setAuthError(`URL Error: ${errorParam}`)
            if (debugParam) console.log("URL Debug: Auth success reported by server")
        }

        const { data: { subscription } } = supabase.auth.onAuthStateChange((event: string, session: any) => {
            console.log("Auth state changed:", event, session?.user?.email)
            if (session) {
                setUser(session.user)
            } else {
                setUser(null)
            }
        })
        return () => subscription.unsubscribe()
    }, [supabase])

    const handleLogin = async () => {
        await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback`
            }
        })
    }

    const handleLogout = async () => {
        await supabase.auth.signOut()
    }

    if (!user) {
        return (
            <div className="p-4 border-t mt-auto">
                <Button onClick={handleLogin} className="w-full">
                    Login with Google
                </Button>
            </div>
        )
    }

    return (
        <div className="flex items-center gap-3">
            <Avatar>
                <AvatarImage src={user.user_metadata.avatar_url} />
                <AvatarFallback>{user.email?.charAt(0).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col overflow-hidden">
                <span className="text-sm font-medium truncate">{user.user_metadata.full_name || user.email}</span>
                <button onClick={handleLogout} className="text-xs text-muted-foreground text-left hover:text-primary flex items-center">
                    <LogOut className="mr-1 h-3 w-3" /> Logout
                </button>
            </div>
        </div>
    )
}
