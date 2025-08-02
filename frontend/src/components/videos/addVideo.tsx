import { useState, useRef, useEffect, type FormEvent } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import type { VideoItem } from "@/types"

interface AddVideoProps {
    onUploadSuccess: (videoId: string) => void
}

export function AddVideo({ onUploadSuccess }: AddVideoProps) {
    const [file, setFile] = useState<File | null>(null)
    const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle")
    const [errorMsg, setErrorMsg] = useState<string>("")
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (status === "success") {
            const timer = setTimeout(() => {
                setStatus("idle")
            }, 5000)
            return () => clearTimeout(timer)
        }
    }, [status])

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFile(e.target.files?.[0] ?? null)
        setStatus("idle")
        setErrorMsg("")
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        if (!file) {
            setErrorMsg("Please select an MP4 file first.")
            return
        }

        const formData = new FormData()
        formData.append("file", file)

        setStatus("uploading")
        setErrorMsg("")

        try {
            const res = await fetch("http://localhost:8000/videos", {
                method: "POST",
                body: formData,
            })
            const json = await res.json()

            if (res.status === 201) {
                const videoId = (json as VideoItem)._id
                setStatus("success")
                setFile(null)
                if (inputRef.current) inputRef.current.value = ""
                onUploadSuccess(videoId)
            } else {
                const detail =
                    typeof json === "object" && "detail" in json
                        ? (json as any).detail
                        : `Server responded ${res.status}`
                throw new Error(detail)
            }
        } catch (err: any) {
            setErrorMsg(err.message)
            setStatus("error")
        }
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="grid w-full max-w-md gap-4 border rounded-md p-6 mx-auto"
        >
            <div className="grid items-center gap-2">
                <Label htmlFor="videoFile">Upload MP4 Video</Label>
                <Input
                    id="videoFile"
                    type="file"
                    accept="video/mp4"
                    onChange={handleFileChange}
                    ref={inputRef}
                />
            </div>

            <Button type="submit" disabled={status === "uploading"}>
                {status === "uploading" ? "Uploading…" : "Upload Video"}
            </Button>

            {status === "success" && (
                <p className="text-green-600">Video uploaded successfully!</p>
            )}
            {status === "error" && (
                <p className="text-red-600">Upload failed: {errorMsg}</p>
            )}
        </form>
    )
}
