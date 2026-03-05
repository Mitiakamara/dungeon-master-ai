"use client"

import * as React from "react"
import { Upload, FileText, Loader2, CheckCircle, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { authenticatedFetch } from "@/lib/api"
import { toast } from "sonner"

interface UploadState {
    status: "idle" | "uploading" | "success" | "error"
    message?: string
    chunks?: number
}

export function CampaignModuleUpload({
    campaignId,
    open,
    onOpenChange
}: {
    campaignId: string
    open: boolean
    onOpenChange: (open: boolean) => void
}) {
    const [uploadState, setUploadState] = React.useState<UploadState>({ status: "idle" })
    const fileInputRef = React.useRef<HTMLInputElement>(null)

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        const ext = file.name.split('.').pop()?.toLowerCase()
        if (!["pdf", "epub"].includes(ext || "")) {
            toast.error("Solo se aceptan archivos .pdf o .epub")
            return
        }

        if (file.size > 50 * 1024 * 1024) {
            toast.error("El archivo no puede superar 50MB")
            return
        }

        setUploadState({ status: "uploading" })

        try {
            const formData = new FormData()
            formData.append("file", file)

            const res = await authenticatedFetch(`/api/campaigns/${campaignId}/modules`, {
                method: "POST",
                body: formData
            })

            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.detail || "Error desconocido")
            }

            const data = await res.json()
            setUploadState({
                status: "success",
                chunks: data.chunks,
                message: data.file
            })
            toast.success(`Modulo cargado: ${data.chunks} fragmentos indexados`)

        } catch (err: any) {
            setUploadState({ status: "error", message: err.message })
            toast.error(`Error al cargar: ${err.message}`)
        }

        if (fileInputRef.current) fileInputRef.current.value = ""
    }

    const handleClose = () => {
        setUploadState({ status: "idle" })
        onOpenChange(false)
    }

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-primary" />
                        Cargar Modulo de Campana
                    </DialogTitle>
                    <DialogDescription>
                        Sube un PDF o EPUB de tu aventura. SAM lo indexara y lo usara como contexto narrativo.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div
                        className="border-2 border-dashed border-muted-foreground/30 rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-colors"
                        onClick={() => uploadState.status !== "uploading" && fileInputRef.current?.click()}
                    >
                        {uploadState.status === "idle" && (
                            <>
                                <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm font-medium">Haz clic para seleccionar un archivo</p>
                                <p className="text-xs text-muted-foreground mt-1">PDF o EPUB - Max 50MB</p>
                            </>
                        )}

                        {uploadState.status === "uploading" && (
                            <>
                                <Loader2 className="h-8 w-8 mx-auto mb-2 text-primary animate-spin" />
                                <p className="text-sm font-medium">Procesando modulo...</p>
                                <p className="text-xs text-muted-foreground mt-1">SAM esta leyendo y vectorizando el archivo. Puede tardar un minuto.</p>
                            </>
                        )}

                        {uploadState.status === "success" && (
                            <>
                                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                                <p className="text-sm font-medium text-green-500">Modulo listo!</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {uploadState.message} - {uploadState.chunks} fragmentos indexados
                                </p>
                            </>
                        )}

                        {uploadState.status === "error" && (
                            <>
                                <XCircle className="h-8 w-8 mx-auto mb-2 text-destructive" />
                                <p className="text-sm font-medium text-destructive">Error al procesar</p>
                                <p className="text-xs text-muted-foreground mt-1">{uploadState.message}</p>
                            </>
                        )}
                    </div>

                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.epub"
                        className="hidden"
                        onChange={handleFileSelect}
                    />

                    <div className="flex justify-end gap-2">
                        {uploadState.status === "success" && (
                            <Button variant="outline" onClick={() => setUploadState({ status: "idle" })}>
                                Subir otro
                            </Button>
                        )}
                        <Button variant="ghost" onClick={handleClose}>
                            {uploadState.status === "success" ? "Cerrar" : "Cancelar"}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}
