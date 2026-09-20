import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy, Download, FileText, FileCode2, FileJson2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useReport } from "@/hooks/use-run-extras";
import { formatDateTime, formatNumber } from "@/lib/format";

type ReportTab = "preview" | "html" | "json";

const TAB_LABELS: Record<ReportTab, { label: string; icon: React.ReactNode }> = {
  preview: { label: "Markdown", icon: <FileText className="size-3.5" /> },
  html: { label: "HTML", icon: <FileCode2 className="size-3.5" /> },
  json: { label: "Raw JSON", icon: <FileJson2 className="size-3.5" /> },
};

export function RunReportView({ runId }: { runId: string }) {
  const { data, isLoading, isError, error } = useReport(runId);
  const [tab, setTab] = React.useState<ReportTab>("preview");
  const [copied, setCopied] = React.useState(false);

  if (isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (isError) {
    return (
      <ErrorState
        title="Could not load report"
        description={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }
  if (!data) {
    return (
      <EmptyState
        icon={<FileText className="size-6" />}
        title="Report not available yet"
        description="Markdown reports are generated once a run completes and artifacts are written."
      />
    );
  }

  const activeContent =
    tab === "json" ? data.json : tab === "html" ? data.html : data.markdown;
  const activeMissing = !activeContent;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(activeContent ?? "");
      setCopied(true);
      toast.success(`${TAB_LABELS[tab].label} copied`);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy report");
    }
  };

  const download = () => {
    if (!activeContent) return;
    const ext = tab === "html" ? "html" : tab === "json" ? "json" : "md";
    const type =
      tab === "html" ? "text/html" : tab === "json" ? "application/json" : "text/markdown";
    const blob = new Blob([activeContent], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.runId}-report.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground">{data.title}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {data.sections.length} sections · {formatNumber(data.reportLines)} lines · generated{" "}
            {formatDateTime(data.created)}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {data.sections.map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant="outline">{data.format}</Badge>
          <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={copy} disabled={activeMissing}>
            {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
            Copy
          </Button>
          <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={download} disabled={activeMissing}>
            <Download className="size-3.5" />
            Download
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as ReportTab)}>
        <TabsList>
          {(Object.keys(TAB_LABELS) as ReportTab[]).map((t) => (
            <TabsTrigger key={t} value={t} className="gap-1.5">
              {TAB_LABELS[t].icon}
              {TAB_LABELS[t].label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {tab === "html" && data.html ? (
        <iframe
          title={`${data.runId} HTML report`}
          srcDoc={data.html}
          sandbox=""
          className="h-[70vh] w-full rounded-lg border border-border bg-white"
        />
      ) : tab === "html" ? (
        <EmptyState title="HTML render unavailable" description="The HTML representation was not produced for this report." />
      ) : tab === "json" && data.json ? (
        <pre className="scrollbar-thin max-h-[70vh] overflow-auto rounded-lg border border-border bg-card p-4 font-mono text-xs leading-5">
          {data.json}
        </pre>
      ) : tab === "json" ? (
        <EmptyState title="JSON payload unavailable" description="The structured report was not produced for this run." />
      ) : data.markdown ? (
        <article className="prose prose-sm prose-neutral max-w-none rounded-lg border border-border bg-card p-6 text-sm prose-headings:mt-5 prose-headings:mb-2 prose-h1:text-lg prose-h2:text-base prose-p:leading-relaxed prose-pre:bg-background prose-code:text-primary prose-table:text-xs">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.markdown}</ReactMarkdown>
        </article>
      ) : (
        <EmptyState title="Report body is empty" description="The report file contained no markdown." />
      )}

      <p className="text-xs text-muted-foreground">
        Shown as {TAB_LABELS[tab].label.toLowerCase()} — download saves the active representation.
      </p>
    </div>
  );
}