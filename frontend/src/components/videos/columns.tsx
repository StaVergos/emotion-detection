import React, { useState, useEffect } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuItem,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import type { VideoItem } from "../../types"

const StageIndicator = React.memo(({ label }: { label: string }) => {
    const [dots, setDots] = useState(0)
    useEffect(() => {
        const id = setInterval(() => {
            setDots((d) => (d === 3 ? 0 : d + 1))
        }, 500)
        return () => clearInterval(id)
    }, [])
    return (
        <span>
            {label}
            {".".repeat(dots)}
        </span>
    )
})

export function getVideoColumns(
    onDelete: (rawId: string) => void,
    processingStatusRef: React.RefObject<Record<string, string>>
): ColumnDef<VideoItem>[] {
    return [
        { accessorKey: "id", header: "ID" },
        { accessorKey: "video_filename", header: "Video File" },
        {
            id: "status",
            header: "Status",
            cell: ({ row }) => {
                const vid = row.original
                const label = processingStatusRef.current?.[vid._id]
                if (label) return <StageIndicator label={label} />
                return <span>{vid.processing_status}</span>
            },
        },
        { accessorKey: "created_at", header: "Created At" },
        {
            id: "actions",
            header: "Actions",
            cell: ({ row }) => {
                const video = row.original
                return (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0">
                                <span className="sr-only">Open menu</span>
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem
                                onClick={() => navigator.clipboard.writeText(video._id)}
                            >
                                Copy video ID
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {/* no more “Process transcript” */}
                            <DropdownMenuItem onClick={() => onDelete(video._id)}>
                                Delete video
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                )
            },
        },
    ]
}
