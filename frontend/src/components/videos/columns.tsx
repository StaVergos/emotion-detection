import type { ColumnDef } from "@tanstack/react-table"
import type { VideoColumn } from "../../types"

export const columns: ColumnDef<VideoColumn>[] = [
    {
        accessorKey: "id",
        header: "id",
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
]