import * as React from "react";
import { useRef } from "react";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useUploadDataset } from "@/hooks/use-datasets";
import { toApiError } from "@/api/client";
import { isDemoMode } from "@/mocks";

const ACCEPT = ".csv,.tsv,.txt,.xlsx,.xls,.parquet,.json,.jsonl";

interface UploadDatasetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded?: (datasetId: string) => void;
}

/**
 * Upload a dataset straight to the backend (`POST /datasets`, streaming
 * multipart). Handles CSV / TSV / XLSX / XLS / Parquet / JSON / JSONL.
 */
export function UploadDatasetDialog({ open, onOpenChange, onUploaded }: UploadDatasetDialogProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [progress, setProgress] = React.useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const upload = useUploadDataset();
  const busy = upload.isPending;

  const reset = () => {
    setFile(null);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleOpenChange = (next: boolean) => {
    if (busy) return;
    if (!next) reset();
    onOpenChange(next);
  };

  const startUpload = () => {
    if (!file) return;
    setProgress(0);
    upload.mutate(
      { file, onProgress: setProgress },
      {
        onSuccess: (res) => {
          const id = res.dataset.summary.id;
          toast.success(`Uploaded ${res.dataset.summary.name}`);
          reset();
          onOpenChange(false);
          onUploaded?.(id);
        },
        onError: (err) => toast.error(toApiError(err).message),
      },
    );
  };

  const isDemo = isDemoMode();

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload dataset</DialogTitle>
          <DialogDescription>
            CSV, TSV, XLSX, XLS, Parquet, JSON or JSONL — file is streamed to the backend in chunks.
          </DialogDescription>
        </DialogHeader>

        <div
          role="button"
          tabIndex={0}
          aria-disabled={busy}
          onClick={() => !busy && inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              if (!busy) inputRef.current?.click();
            }
          }}
          className="grid cursor-pointer place-items-center gap-2 rounded-lg border border-dashed border-border p-8 text-center hover:bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <UploadCloud className="size-8 text-muted-foreground" />
          <p className="text-sm font-medium">{file ? file.name : "Click to choose a file"}</p>
          {file && <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>}
          {!file && <p className="text-xs text-muted-foreground">{ACCEPT.replaceAll(",", "  ")}</p>}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const selected = e.target.files?.[0] ?? null;
            setFile(selected);
            if (selected) setProgress(0);
          }}
        />

        {busy && (
          <div className="space-y-1.5">
            <Progress value={progress} />
            <p className="text-xs text-muted-foreground">Uploading… {progress}%</p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={startUpload} disabled={busy || !file} className="gap-1.5">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <FileUp className="size-4" />}
            {busy ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>

        {isDemo && (
          <p className="text-xs text-muted-foreground">
            Demo mode: uploads are simulated against mocked handlers.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
