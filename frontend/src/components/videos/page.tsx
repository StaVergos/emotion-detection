"use client";

import { useMemo } from "react";
import { DataTable } from "./data-table";
import { getVideoColumns } from "./columns";
import type { VideoItem } from "../../types";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
    processingIds: Set<string>;
    onDelete: (rawId: string) => void;
    onProcess: (rawId: string) => void;
}

export default function VideoTablePage({
    loading,
    error,
    data,
    processingIds,
    onDelete,
    onProcess,
}: VideoTablePageProps) {
    const columns = useMemo(
        () => getVideoColumns(onDelete, onProcess, processingIds),
        [onDelete, onProcess, processingIds]
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
