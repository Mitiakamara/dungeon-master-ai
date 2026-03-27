"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useRouter } from "next/navigation"

export default function SignupPage() {
    const [code, setCode] = useState("")
    const [codeValid, setCodeValid] = useState<boolean | null>(null)
    const [codeError, setCodeError] = useState("")
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [username, setUsername] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")
    const router = useRouter()

    const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || ""

    const validateCode = async () => {
        setCodeError("")
        try {
            const res = await fetch(`${BACKEND_URL}/api/invitations/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code.toUpperCase().trim() }),
            })
            const data = await res.json()
            if (data.valid) {
                setCodeValid(true)
            } else {
                setCodeValid(false)
                setCodeError(
                    data.reason === "expired"
                        ? "This code has expired"
                        : data.reason === "used"
                            ? "This code has already been used"
                            : "Invalid code"
                )
            }
        } catch {
            setCodeError("Error validating code")
        }
    }

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setError("")
        try {
            const res = await fetch(`${BACKEND_URL}/api/invitations/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email,
                    password,
                    username,
                    invitation_code: code.toUpperCase().trim(),
                }),
            })
            const data = await res.json()
            if (res.ok) {
                router.push("/?registered=true")
            } else {
                setError(data.detail || "Error creating account")
            }
        } catch {
            setError("Error connecting to server")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
                        S.A.M.
                    </CardTitle>
                    <CardDescription>Storytelling AI Master — Join the Adventure</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {/* Step 1: Invitation Code */}
                        <div>
                            <label className="text-sm font-medium">Invitation Code</label>
                            <div className="flex gap-2 mt-1">
                                <Input
                                    value={code}
                                    onChange={(e) => {
                                        setCode(e.target.value)
                                        setCodeValid(null)
                                    }}
                                    placeholder="ABC123"
                                    maxLength={8}
                                    className="uppercase tracking-widest text-center font-mono text-lg"
                                />
                                <Button
                                    onClick={validateCode}
                                    variant="secondary"
                                    disabled={code.trim().length < 6}
                                >
                                    Validate
                                </Button>
                            </div>
                            {codeValid === true && (
                                <p className="text-sm text-green-500 mt-1">Valid code</p>
                            )}
                            {codeError && (
                                <p className="text-sm text-red-500 mt-1">{codeError}</p>
                            )}
                        </div>

                        {/* Step 2: Registration form (only if code is valid) */}
                        {codeValid && (
                            <form onSubmit={handleRegister} className="space-y-3 pt-4 border-t">
                                <div>
                                    <label className="text-sm font-medium">Username</label>
                                    <Input
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium">Email</label>
                                    <Input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium">Password</label>
                                    <Input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        minLength={6}
                                    />
                                </div>
                                {error && <p className="text-sm text-red-500">{error}</p>}
                                <Button type="submit" className="w-full" disabled={loading}>
                                    {loading ? "Creating account..." : "Create Account"}
                                </Button>
                            </form>
                        )}

                        <div className="text-center pt-4">
                            <a
                                href="/"
                                className="text-sm text-muted-foreground hover:underline"
                            >
                                Already have an account? Sign in
                            </a>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
