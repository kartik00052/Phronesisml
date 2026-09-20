import * as React from "react";
import {
  BadgeCheck,
  CheckCircle2,
  Database,
  FileWarning,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { UploadDatasetDialog } from "@/components/datasets/upload-dataset-dialog";
import { useDatasets, useDataset, useDeleteDataset } from "@/hooks/use-datasets";
import { toApiError } from "@/api/client";
import { formatBytes, formatNumber, formatDateTime } from "@/lib/format";
import type { ColumnInfo, DatasetSummary } from "@/types/dataset";

export default function DatasetsPage() {
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [toDelete, setToDelete] = React.useState<DatasetSummary | null>(null);
  const deleteMut = useDeleteDataset();

  const { data, isLoading } = useDatasets({ pageSize: 100 });
  const { data: detail } = useDataset(selected ?? undefined);

  const filtered = (data?.items ?? []).filter(
    (d) =>
      !search ||
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.path.toLowerCase().includes(search.toLowerCase()),
  );

  const samples = filtered.filter((d) => d.sample);
  const uploaded = filtered.filter((d) => !d.sample);
  const sorted = [...samples, ...uploaded];

  const confirmDelete = () => {
    if (!toDelete) return;
    deleteMut.mutate(toDelete.id, {
      onSuccess: (res) => {
        toast.success(res.deleted ? `Deleted ${toDelete.name}` : "Dataset already gone");
        setToDelete(null);
        if (selected === toDelete.id) setSelected(null);
      },
      onError: (err) => toast.error(toApiError(err).message),
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Datasets"
        description="Browse the workspace dataset registry and inspect schemas, validation, and sampling metadata."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search datasets…"
            className="h-9 pl-8"
          />
        </div>
        <Button onClick={() => setUploadOpen(true)} className="gap-1.5">
          <Upload className="size-4" />
          Upload dataset
        </Button>
      </div>

      {filtered.length === 0 && !isLoading && (
        <div className="rounded-lg border border-border bg-card py-14 text-center shadow-sm">
          <Database className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-3 text-sm font-medium">No datasets yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload a CSV (or other tabular file) to run your first experiment.
          </p>
        </div>
      )}

      <div className="rounded-lg border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Format</TableHead>
              <TableHead>Shape</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Missing / dup</TableHead>
              <TableHead>Validation</TableHead>
              <TableHead>Registered</TableHead>
              <TableHead className="sr-only">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={8}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : sorted.length > 0 ? (
              sorted.map((d) => (
                <TableRow key={d.id} className="cursor-pointer" onClick={() => setSelected(d.id)}>
                  <TableCell className="max-w-64">
                    <div className="flex items-center gap-2">
                      <Database className="size-4 shrink-0 text-muted-foreground" />
                      <span className="truncate font-medium text-foreground">{d.name}</span>
                      {d.sample && (
                        <Badge variant="secondary" className="gap-1">
                          <Sparkles className="size-3" />
                          Sample
                        </Badge>
                      )}
                    </div>
                    <span className="block truncate font-mono text-xs text-muted-foreground">
                      {d.path}
                    </span>
                  </TableCell>
                  <TableCell className="uppercase text-muted-foreground">{d.format}</TableCell>
                  <TableCell className="tabular-nums">
                    {formatNumber(d.rows)} × {formatNumber(d.columns)}
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {formatBytes(d.sizeBytes)}
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {formatNumber(d.missingCells)} / {formatNumber(d.duplicateRows)}
                  </TableCell>
                  <TableCell>
                    {d.validationPassed ? (
                      <Badge variant="success">
                        <CheckCircle2 className="size-3" /> Passed
                      </Badge>
                    ) : (
                      <Badge variant="warning">
                        <FileWarning className="size-3" /> Check
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(d.registeredAt)}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-1.5 text-destructive hover:text-destructive"
                      onClick={() => setToDelete(d)}
                      disabled={deleteMut.isPending}
                    >
                      <Trash2 className="size-3.5" />
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-sm text-muted-foreground">
                  No datasets found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Sheet open={!!detail} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {detail ? (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {detail.summary.name}
                  {detail.summary.validationPassed && (
                    <BadgeCheck className="size-4 text-success" />
                  )}
                </SheetTitle>
              </SheetHeader>

              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-md border border-border bg-surface p-3">
                  <p className="text-xs text-muted-foreground">Rows</p>
                  <p className="text-lg font-semibold">{formatNumber(detail.summary.rows)}</p>
                </div>
                <div className="rounded-md border border-border bg-surface p-3">
                  <p className="text-xs text-muted-foreground">Columns</p>
                  <p className="text-lg font-semibold">{formatNumber(detail.summary.columns)}</p>
                </div>
                <div className="rounded-md border border-border bg-surface p-3">
                  <p className="text-xs text-muted-foreground">Missing cells</p>
                  <p className="text-lg font-semibold">
                    {formatNumber(detail.summary.missingCells)}
                  </p>
                </div>
              </div>

              <div className="mt-6">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Schema
                </p>
                <div className="overflow-hidden rounded-md border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Column</TableHead>
                        <TableHead>Dtype</TableHead>
                        <TableHead>Null %</TableHead>
                        <TableHead>Range</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.columns.map((c) => (
                        <ColumnRow key={c.name} column={c} />
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <div className="mt-6 rounded-md border border-border bg-surface p-3 text-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Engine
                </p>
                <p className="mt-1 font-medium">{detail.summary.engine}</p>
                <p className="text-xs text-muted-foreground">{detail.summary.engineReason}</p>
              </div>
            </>
          ) : (
            <Skeleton className="h-full w-full" />
          )}
        </SheetContent>
      </Sheet>

      <UploadDatasetDialog open={uploadOpen} onOpenChange={setUploadOpen} />

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{toDelete?.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              The dataset files, profile, validation and preview are removed from the workspace
              registry.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMut.isPending}>Keep dataset</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMut.isPending}
              onClick={confirmDelete}
            >
              Delete dataset
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ColumnRow({ column }: { column: ColumnInfo }) {
  let range = "";
  if (column.stats) {
    const { min, max } = column.stats;
    range = `${min} – ${max}`;
  } else if (column.topValues) {
    const top = Object.keys(column.topValues).slice(0, 2).join(", ");
    range = top;
  } else {
    range = column.cardinality != null ? `${formatNumber(column.cardinality)} categories` : "";
  }

  return (
    <TableRow>
      <TableCell className="font-medium">{column.name}</TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">{column.dtype}</TableCell>
      <TableCell className="tabular-nums">{column.nullPercent.toFixed(1)}%</TableCell>
      <TableCell className="max-w-48 truncate text-muted-foreground" title={range}>
        {range || "—"}
      </TableCell>
    </TableRow>
  );
}
