import * as React from "react";
import {
  Archive,
  Boxes,
  Eye,
  File as FileIcon,
  FileJson,
  FileText,
  Image as ImageIcon,
  Package,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArtifactPreviewDialog } from "@/components/run/artifact-preview";
import { useArtifacts } from "@/hooks/use-run-extras";
import { formatBytes, formatNumber } from "@/lib/format";
import type { Artifact, ArtifactKind } from "@/types/artifact";

const KIND_ICON: Partial<Record<ArtifactKind, React.ReactNode>> = {
  model: <Package className="size-3.5" />,
  report: <FileText className="size-3.5" />,
  eda: <ImageIcon className="size-3.5" />,
  run_metadata: <FileJson className="size-3.5" />,
  logs: <FileIcon className="size-3.5" />,
};

export function RunArtifactsView({ runId }: { runId: string }) {
  const { data, isLoading, isError, error } = useArtifacts(runId);
  const [kind, setKind] = React.useState<"all" | ArtifactKind>("all");
  const [preview, setPreview] = React.useState<Artifact | null>(null);

  const columns = React.useMemo<ColumnDef<Artifact, unknown>[]>(
    () => [
      {
        id: "name",
        accessorKey: "name",
        header: "Artifact",
        cell: ({ row }) => (
          <span className="inline-flex items-center gap-2">
            <span className="text-muted-foreground">
              {KIND_ICON[row.original.kind] ?? <FileIcon className="size-3.5" />}
            </span>
            <span className="font-mono text-xs">{row.original.name}</span>
          </span>
        ),
      },
      {
        id: "kind",
        accessorKey: "kind",
        header: "Kind",
        cell: ({ row }) => (
          <span className="capitalize text-muted-foreground">
            {row.original.kind.replace(/_/g, " ")}
          </span>
        ),
      },
      {
        id: "description",
        accessorKey: "description",
        header: "Description",
        cell: ({ row }) => (
          <span className="text-muted-foreground">{row.original.description}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableGlobalFilter: false,
        accessorFn: (row) => row.status,
        cell: ({ row }) =>
          row.original.status === "available" ? (
            <Badge variant="success">{formatBytes(row.original.sizeBytes)}</Badge>
          ) : (
            <Badge variant="muted">{row.original.reason ?? "unavailable"}</Badge>
          ),
      },
      {
        id: "preview",
        header: "",
        enableGlobalFilter: false,
        cell: ({ row }) =>
          row.original.status === "available" ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground"
              onClick={(e) => {
                e.stopPropagation();
                setPreview(row.original);
              }}
            >
              <Eye className="size-3" />
              Preview
            </Button>
          ) : null,
      },
    ],
    [],
  );

  if (isLoading) return <DataTable columns={columns} data={[]} loading pageSize={8} />;
  if (isError) {
    return (
      <ErrorState
        title="Could not load artifacts"
        description={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }
  if (!data || data.artifactCount === 0) {
    return (
      <EmptyState
        icon={<Archive className="size-6" />}
        title="No artifacts yet"
        description="Model binaries, encodings, SHAP outputs, and reports appear here as the run writes them."
      />
    );
  }

  const kinds = Array.from(new Set(data.artifacts.map((a) => a.kind)));
  const filtered = kind === "all" ? data.artifacts : data.artifacts.filter((a) => a.kind === kind);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm">
        <span className="flex items-center gap-2 font-medium">
          <Boxes className="size-4 text-muted-foreground" />
          {formatNumber(data.artifactCount)} artifacts
        </span>
        <span className="text-muted-foreground">{formatBytes(data.totalBytes)} total</span>
        <span className="ml-auto font-mono text-xs text-muted-foreground">{data.runId}</span>
      </div>

      <Tabs value={kind} onValueChange={(v) => setKind(v as typeof kind)}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="all">All ({data.artifacts.length})</TabsTrigger>
          {kinds.map((k) => (
            <TabsTrigger key={k} value={k} className="capitalize">
              {k.replace(/_/g, " ")}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <DataTable
        columns={columns}
        data={filtered}
        searchPlaceholder="Search artifacts…"
        emptyMessage="No artifacts in this category"
        getRowId={(a) => a.name}
        pageSize={15}
        onRowClick={(row) => row.status === "available" && setPreview(row)}
      />

      <ArtifactPreviewDialog
        open={preview !== null}
        onOpenChange={(o) => !o && setPreview(null)}
        runId={runId}
        artifact={preview}
      />
    </div>
  );
}
