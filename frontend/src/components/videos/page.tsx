"use client";

import { useMemo, useRef, useEffect } from "react";
import { DataTable } from "./dataTable";
import { getVideoColumns } from "./columns";
import type { VideoItem } from "../../types";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
    processingStatus: Record<string, string>;
    onDelete: (rawId: string) => void;
}

export default function VideoTablePage({
    loading,
    error,
    data,
    processingStatus,
    onDelete,
}: VideoTablePageProps) {
    const statusRef = useRef(processingStatus);
    useEffect(() => {
        statusRef.current = processingStatus;
    }, [processingStatus]);

    const processingKeyString = useMemo(
        () => Object.keys(processingStatus).sort().join(","),
        [processingStatus]
    );

    const columns = useMemo(
        () => getVideoColumns(onDelete, statusRef),
        [onDelete, processingKeyString]
    );

    if (loading)
        return <div className="text-center py-20">Loading…</div>;
    if (error)
        return <div className="text-red-600 text-center py-20">{error}</div>;

    return (
        <div className="container mx-auto py-10 w-full">
            <DataTable columns={columns} data={data} />
        </div>
    );
}
