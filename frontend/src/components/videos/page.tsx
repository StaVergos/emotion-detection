import { useMemo, useState, useCallback } from "react";
import { DataTable } from "./data-table";
import { getVideoColumns } from "./columns";
import type { VideoItem } from "../../types";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
    onDelete: (rawId: string) => void;
    onProcess: (rawId: string) => Promise<void>;
}

export default function VideoTablePage({
    loading,
    error,
    data,
    onDelete,
    onProcess,   // raw backend-calling callback
}: VideoTablePageProps) {
    // track which rows are currently being processed
    const [processingIds, setProcessingIds] = useState<Set<string>>(
        () => new Set()
    );

    const processVideo = useCallback(
        async (rawId: string) => {
            // start animation
            setProcessingIds((s) => new Set(s).add(rawId));
            try {
                await onProcess(rawId);
            } finally {
                // stop animation
                setProcessingIds((s) => {
                    const next = new Set(s);
                    next.delete(rawId);
                    return next;
                });
            }
        },
        [onProcess]
    );

    // rebuild columns whenever delete, process or processing set changes
    const columns = useMemo(
        () => getVideoColumns(onDelete, processVideo, processingIds),
        [onDelete, processVideo, processingIds]
    );

    return (
        <div className="container mx-auto py-10 w-full">
            {loading ? (
                <div className="text-center py-20">Loading…</div>
            ) : error ? (
                <div className="text-red-600 text-center py-20">{error}</div>
            ) : (
                <DataTable columns={columns} data={data} />
            )}
        </div>
    );
}
