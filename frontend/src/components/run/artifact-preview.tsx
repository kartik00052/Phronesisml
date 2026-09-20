import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, FileText, Loader2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useArtifactContent } from "@/hooks/use-run-extras";
import { formatBytes } from "@/lib/format";
import type { Artifact } from "@/types/artifact";

function downloadText(name: string, contentType: string, content: string) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function ArtifactPreviewDialog({
  open,
  onOpenChange,
  runId,
  artifact,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runId: string;
  artifact: Artifact | null;
}) {
  const { data, isLoading, isError, error } = useArtifactContent(runId, artifact?.name ?? null);

  const download = () => {
    if (!data?.content) return;
    const type =
      data.format === "html"
        ? "text/html"
        : data.format === "md"
          ? "text/markdown"
          : data.format === "json"
            ? "application/json"
            : "text/plain";
    downloadText(data.name, type, data.content);
    toast.success(`Downloaded ${data.name}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex flex-wrap items-center gap-2 font-mono text-sm">
            {artifact?.name ?? "Artifact"}
            {data && (
              <span className="ml-auto font-sans text-xs font-normal text-muted-foreground">
                {data.format} · {formatBytes(data.sizeBytes)}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="scrollbar-thin max-h-[60vh] overflow-auto rounded-md border border-border">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : isError || !data ? (
            <p className="p-6 text-center text-sm text-danger">
              {error instanceof Error ? error.message : "Could not load artifact content."}
            </p>
          ) : data.note && !data.content ? (
            <div className="flex flex-col items-center gap-2 p-10 text-center">
              <FileText className="size-6 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{data.note}</p>
            </div>
          ) : data.format === "html" && data.content ? (
            <iframe
              title={`${data.name} preview`}
              srcDoc={data.content}
              sandbox=""
              className="h-[55vh] w-full bg-white"
            />
          ) : data.format === "md" && data.content ? (
            <article className="prose prose-sm prose-neutral max-w-none p-6 text-sm prose-headings:mt-4 prose-code:text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
            </article>
          ) : data.content ? (
            <>
              {data.truncated && (
                <div className="flex items-center gap-1.5 border-b border-border bg-warning/10 px-4 py-2 text-xs text-warning">
                  <TriangleAlert className="size-3.5 shrink-0" />
                  Preview truncated — showing the first portion of this {data.format.toUpperCase()}{" "}
                  artifact. Download the file for the full content.
                </div>
              )}
              <pre className="scrollbar-thin max-h-[60vh] overflow-auto p-4 font-mono text-xs leading-5 text-foreground">
                {data.content}
              </pre>
            </>
          ) : (
            <p className="p-6 text-center text-sm text-muted-foreground">
              No text preview available for this artifact.
            </p>
          )}
        </div>

        <DialogFooter className="items-center gap-2 sm:justify-between">
          <span className="text-xs text-muted-foreground">
            {isLoading ? "Fetching content…" : (data?.content?.length ?? 0).toLocaleString()} chars
          </span>
          <Button variant="outline" size="sm" onClick={download} disabled={!data?.content}>
            {isLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
            Download
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}