"use client";

import { useMemo } from "react";
import { DataTable } from "./data-table";
import { getVideoColumns } from "./columns";
import type { VideoItem } from "../../types";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
    onDelete: (id: string) => void;
}

export default function VideoTablePage({
    loading,
    error,
    data,
    onDelete,
}: VideoTablePageProps) {
    const columns = useMemo(() => getVideoColumns(onDelete), [onDelete]);

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
