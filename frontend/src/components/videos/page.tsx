import { useMemo, useRef, useEffect } from "react";
import { DataTable } from "./dataTable";
import { getVideoColumns } from "./columns";
import type { VideoItem } from "../../types";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
    // processingStatus: boolean;
    onDelete: (rawId: string) => void;
    onViewTranscript: (rawId: string) => void;
    onViewOpenAIAnalysis: (rawId: string) => void;
}

export default function VideoTablePage({
    loading,
    error,
    data,
    onDelete,
    onViewTranscript,
    onViewOpenAIAnalysis
}: VideoTablePageProps) {


    const columns = useMemo(
        () => getVideoColumns(onDelete, onViewTranscript, onViewOpenAIAnalysis),
        [onDelete, onViewTranscript, onViewOpenAIAnalysis]
    );

    if (loading) return <div className="text-center py-20">Loading…</div>;
    if (error) return <div className="text-red-600 text-center py-20">{error}</div>;

    return (
        <div className="container mx-auto py-10 w-full">
            <DataTable columns={columns} data={data} />
        </div>
    );
}
