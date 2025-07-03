"use client";

import { useState, useEffect } from "react";
import { columns } from "./columns";
import type { VideoColumn, VideoItem } from "./types";
import { DataTable } from "./data-table";

export default function VideoTablePage() {
    const [videos, setVideos] = useState<VideoItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Map your full VideoItem[] down to the 4‐column shape
    const data: VideoColumn[] = videos.map((video) => ({
        id: video._id,
        video_filename: video.video_filename,
        transcript_process_status: video.transcript_process_status,
        created_at: new Date(video.created_at).toLocaleDateString(),
    }));

    useEffect(() => {
        fetch("http://localhost:8000/videos")
            .then((res) => {
                if (res.status === 404) {
                    throw new Error("No videos found");
                }
                if (!res.ok) {
                    throw new Error(`Server error (${res.status})`);
                }
                return res.json();
            })
            .then((json) => {
                setVideos(json.videos);
            })
            .catch((err: Error) => {
                setError(err.message);
            })
            .finally(() => {
                setLoading(false);
            });
    }, []);

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
