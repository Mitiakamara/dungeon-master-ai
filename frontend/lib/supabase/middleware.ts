import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => request.cookies.set(name, value))
                    response = NextResponse.next({
                        request: {
                            headers: request.headers,
                        },
                    })
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, options)
                    )
                },
            },
        }
    )

    // IMPORTANT: DO NOT REMOVE auth.getUser()
    const { data: { user }, error } = await supabase.auth.getUser()

    if (request.nextUrl.pathname.startsWith('/auth') || request.nextUrl.pathname === '/') {
        return response
    }

    // Example protection (optional, commenting out to avoid redirect loops for now)
    /*
    if (!user && !request.nextUrl.pathname.startsWith('/auth')) {
      // no user, potentially redirect to login page
      // const url = request.nextUrl.clone()
      // url.pathname = '/login'
      // return NextResponse.redirect(url)
    }
    */

    return response
}
