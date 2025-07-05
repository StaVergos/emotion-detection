import { useState, useEffect } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuItem,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import type { VideoItem } from "../../types";

function ProcessingIndicator() {
    const [dots, setDots] = useState(0);
    useEffect(() => {
        const id = setInterval(() => {
            setDots((d) => (d === 3 ? 0 : d + 1));
        }, 500);
        return () => clearInterval(id);
    }, []);
    return <span>processing{".".repeat(dots)}</span>;
}

export function getVideoColumns(
    onDelete: (rawId: string) => void,
    onProcess: (rawId: string) => void,
    processingIds: Set<string>
): ColumnDef<VideoItem>[] {
    return [
        {
            accessorKey: "id",
            header: "ID",
        },
        {
            accessorKey: "video_filename",
            header: "Video File",
        },
        {
            id: "transcript_status",
            header: "Transcript Status",
            cell: ({ row }) => {
                const video = row.original;
                if (processingIds.has(video._id)) {
                    return <ProcessingIndicator />;
                }
                return <span>{video.transcript_process_status}</span>;
            },
        },
        {
            accessorKey: "created_at",
            header: "Created At",
        },
        {
            id: "actions",
            header: "Actions",
            cell: ({ row }) => {
                const video = row.original;
                const canProcess = video.transcript_process_status === "uploaded";

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
                                onClick={() => navigator.clipboard.writeText(video.id)}
                            >
                                Copy video ID
                            </DropdownMenuItem>

                            <DropdownMenuSeparator />

                            <DropdownMenuItem
                                onClick={() => onProcess(video._id)}
                                disabled={!canProcess}
                            >
                                Process transcript
                            </DropdownMenuItem>

                            <DropdownMenuSeparator />

                            <DropdownMenuItem onClick={() => onDelete(video._id)}>
                                Delete video
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                );
            },
        },
    ];
}
