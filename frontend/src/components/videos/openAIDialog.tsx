import {
    Dialog,
    DialogContent,
    DialogTitle,
} from "@/components/ui/dialog";
import type { PromptItem } from "@/types";

interface OpenAIDialogProps {
    open: boolean;
    prompt: PromptItem[];
    analysis: string;
    onClose: () => void;
}

export function OpenAIDialog({
    open,
    prompt,
    analysis,
    onClose,
}: OpenAIDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
                <DialogTitle className="mt-6">Prompt</DialogTitle>
                <div className="mt-4 whitespace-pre-wrap text-sm">{prompt.map((p) => `${p.role}: ${p.content}`).join("\n")}</div>
                <DialogTitle className="mt-6">Analysis</DialogTitle>
                <div className="mt-4 whitespace-pre-wrap text-sm">{analysis}</div>
            </DialogContent>
        </Dialog>
    );
}
