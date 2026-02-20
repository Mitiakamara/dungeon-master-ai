'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'

function AuthCallbackContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [status, setStatus] = useState('Authenticating...')
    const [error, setError] = useState<string | null>(null)
    const supabase = createClient()

    useEffect(() => {
        const handleAuthCallback = async () => {
            const code = searchParams.get('code')
            const next = searchParams.get('next') ?? '/'

            if (code) {
                try {
                    console.log("Client-Side Auth: Exchanging code for session...")
                    const { error } = await supabase.auth.exchangeCodeForSession(code)

                    if (error) {
                        console.error("Client-Side Auth Error:", error)
                        setStatus('Authentication Failed')
                        setError(error.message)
                    } else {
                        console.log("Client-Side Auth: Success! Redirecting...")
                        setStatus('Success! Redirecting...')
                        setTimeout(() => {
                            router.push(next)
                            router.refresh()
                        }, 500)
                    }
                } catch (err: any) {
                    console.error("Client-Side Auth Exception:", err)
                    setStatus('Unexpected Error')
                    setError(err.message || 'Unknown error occurred')
                }
            } else {
                setStatus('No auth code found')
                setTimeout(() => router.push('/'), 2000)
            }
        }

        handleAuthCallback()
    }, [searchParams, router, supabase])

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground p-4">
            <div className="max-w-md w-full space-y-4 text-center">
                <h1 className="text-2xl font-bold">Authentication</h1>
                <p className="text-muted-foreground">{status}</p>

                {error && (
                    <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
                        {error}
                    </div>
                )}

                {error && (
                    <Button onClick={() => router.push('/')} variant="outline">
                        Return Home
                    </Button>
                )}
            </div>
        </div>
    )
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading Auth...</div>}>
            <AuthCallbackContent />
        </Suspense>
    )
}
