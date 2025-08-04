import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from "@/components/ui/dialog";

interface TranscriptDialogProps {
    open: boolean;
    transcript: string;
    onClose: () => void;
}

export function TranscriptDialog({ open, transcript, onClose }: TranscriptDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Transcript</DialogTitle>
                    <DialogClose asChild>
                    </DialogClose>
                </DialogHeader>
                <div className="mt-4 whitespace-pre-wrap text-sm">{transcript}</div>
            </DialogContent>
        </Dialog>
    );
}
