"use client";

import { useState, useMemo } from "react";
import { DataTable } from "./data-table";
import { getVideoColumns } from "./columns";
import { Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription, DialogClose } from "@/components/ui/dialog";
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
    const [isOpen, setIsOpen] = useState(false);
    const [currentTranscript, setCurrentTranscript] = useState<string>("");

    const handleViewTranscript = (text: string) => {
        setCurrentTranscript(text);
        setIsOpen(true);
    };

    const columns = useMemo(
        () =>
            getVideoColumns(
                onDelete,
                onProcess,
                processingIds,
                handleViewTranscript
            ),
        [onDelete, onProcess, processingIds]
    );

    return (
        <>
            <Dialog open={isOpen} onOpenChange={setIsOpen}>
                <DialogContent>
                    <DialogTitle>Transcript</DialogTitle>
                    <DialogDescription asChild>
                        <pre className="whitespace-pre-wrap text-sm">
                            {currentTranscript}
                        </pre>
                    </DialogDescription>
                    <DialogClose className="mt-4">Close</DialogClose>
                </DialogContent>
            </Dialog>

            <div className="container mx-auto py-10 w-full">
                {loading ? (
                    <div className="text-center py-20">Loading…</div>
                ) : error ? (
                    <div className="text-red-600 text-center py-20">{error}</div>
                ) : (
                    <DataTable columns={columns} data={data} />
                )}
            </div>
        </>
    );
}
