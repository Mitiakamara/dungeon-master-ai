import { createClient } from "@/lib/supabase/client"

const DEFAULT_TIMEOUT_MS = 30000 // 30s — mobile background can hang indefinitely

/**
 * Wrapper around fetch that adds the Authorization header with the current Supabase session token.
 * Auto-aborts after 30 seconds to prevent hung requests (especially on mobile background suspension).
 */
export async function authenticatedFetch(url: string, options: RequestInit = {}) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()

    const isFormData = options.body instanceof FormData

    const headers = {
        ...options.headers,
        // Only set Content-Type if NOT FormData (browser sets it automatically with boundary)
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    } as Record<string, string>

    if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
    }

    // Default to localhost for now if relative path, or handle base URL
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`

    // AbortController timeout — prevents hung fetches on mobile background
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

    try {
        const response = await fetch(fullUrl, {
            ...options,
            headers,
            signal: options.signal ?? controller.signal,
        })

        if (response.status === 401) {
            console.error("Unauthorized request to", url)
        }

        return response
    } finally {
        clearTimeout(timeoutId)
    }
}
