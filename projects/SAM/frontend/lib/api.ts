import { createClient } from "@/lib/supabase/client"

/**
 * Wrapper around fetch that adds the Authorization header with the current Supabase session token.
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
    // Ideally use env var NEXT_PUBLIC_API_URL
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`

    const response = await fetch(fullUrl, {
        ...options,
        headers,
    })

    if (response.status === 401) {
        // Handle unauthorized (e.g. redirect to login or refresh token)
        console.error("Unauthorized request to", url)
    }

    return response
}
