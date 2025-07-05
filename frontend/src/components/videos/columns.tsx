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

export function getVideoColumns(
    onDelete: (id: string) => void
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
            accessorKey: "transcript_process_status",
            header: "Transcript Status",
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

                            <DropdownMenuItem onClick={() => onDelete(video.id)}>
                                Delete video
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                );
            },
        },
    ];
}
