"use client";

import { columns } from "./columns";
import type { VideoItem } from "../../types";
import { DataTable } from "./data-table";

interface VideoTablePageProps {
    loading: boolean;
    error: string | null;
    data: VideoItem[];
}

export default function VideoTablePage({ loading, error, data }: VideoTablePageProps) {
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
