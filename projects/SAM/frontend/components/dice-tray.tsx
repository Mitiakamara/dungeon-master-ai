"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Dices, Minus, Plus, Loader2 } from "lucide-react"
import { authenticatedFetch } from "@/lib/api"

export function DiceTray({ onRoll, characterName }: { onRoll?: (msg: string) => void, characterName?: string }) {
    const [multiplier, setMultiplier] = React.useState(1)
    const [rolling, setRolling] = React.useState(false)

    const adjustMultiplier = (delta: number) => {
        setMultiplier(prev => Math.max(1, prev + delta))
    }

    const handleRoll = async (sides: number) => {
        setRolling(true)
        const rollerName = characterName || "Unknown Player";
        const expression = `${multiplier}d${sides}`;

        try {
            // Roll via backend (secrets.randbelow — cryptographically secure)
            const res = await authenticatedFetch("/api/roll", {
                method: "POST",
                body: JSON.stringify({ expression, visibility: "public" }),
            });

            if (res.ok) {
                const data = await res.json();
                const { rolls, total } = data.result;
                const msg = `[SYSTEM EVENT] ${rollerName} rolled ${expression}. Result: ${total} (Rolls: ${rolls.join(', ')}).`;
                if (onRoll) onRoll(msg);
            } else {
                throw new Error("Backend roll failed");
            }
        } catch {
            // Fallback to client-side if backend unreachable
            let total = 0;
            const rolls = [];
            for (let i = 0; i < multiplier; i++) {
                const val = Math.floor(Math.random() * sides) + 1;
                rolls.push(val);
                total += val;
            }
            const msg = `[SYSTEM EVENT] ${rollerName} rolled ${expression}. Result: ${total} (Rolls: ${rolls.join(', ')}).`;
            if (onRoll) onRoll(msg);
        } finally {
            setRolling(false)
        }
    }

    return (
        <div className="flex flex-col h-full">
            <h2 className="mb-4 text-lg font-semibold flex items-center">
                <Dices className="mr-2 h-5 w-5" /> Dice Tray
            </h2>

            {/* Multiplier Controls */}
            <div className="flex items-center space-x-2 mb-4 p-2 bg-secondary/20 rounded-lg">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => adjustMultiplier(-1)}
                    disabled={multiplier <= 1}
                    className="h-8 w-8"
                >
                    <Minus className="h-4 w-4" />
                </Button>
                <div className="flex-1 text-center font-mono font-bold text-lg">
                    {multiplier}x
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => adjustMultiplier(1)}
                    className="h-8 w-8"
                >
                    <Plus className="h-4 w-4" />
                </Button>
            </div>

            {/* Dice Grid */}
            <div className="grid grid-cols-2 gap-2">
                {[20, 12, 10, 8, 6, 4].map((sides) => (
                    <Button
                        key={sides}
                        variant="outline"
                        className="h-20 flex-col hover:border-primary hover:bg-primary/5 transition-all"
                        onClick={() => handleRoll(sides)}
                        disabled={rolling}
                    >
                        {rolling ? <Loader2 className="h-6 w-6 animate-spin" /> : <span className="text-2xl font-bold">d{sides}</span>}
                        <span className="text-xs text-muted-foreground mt-1">
                            {multiplier}d{sides}
                        </span>
                    </Button>
                ))}
            </div>
        </div>
    )
}
