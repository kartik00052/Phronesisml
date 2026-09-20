import { useState } from "react";
import { RotateCcw, Trash2, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
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
import { useCancelRun, useDeleteRun, useRestoreRun } from "@/hooks/use-runs";
import { toApiError } from "@/api/client";

interface RunActionsProps {
  runId: string;
  status: string;
  onDeleted?: () => void;
}

/**
 * Operational run actions backed by the real backend endpoints. States:
 * Cancel (queued/running), Restore (cancelled/completed/failed), Delete
 * (terminal states only).
 */
export function RunActions({ runId, status, onDeleted }: RunActionsProps) {
  const cancel = useCancelRun();
  const restore = useRestoreRun();
  const remove = useDeleteRun();
  const [confirm, setConfirm] = useState<"cancel" | "delete" | null>(null);

  const busy = cancel.isPending || restore.isPending || remove.isPending;

  const handleCancel = () => {
    cancel.mutate(runId, {
      onSuccess: () => {
        setConfirm(null);
        toast.success("Run cancelled");
      },
      onError: (err) => toast.error(toApiError(err).message),
    });
  };

  const handleRestore = () => {
    restore.mutate(runId, {
      onSuccess: () => toast.success("Run restored"),
      onError: (err) => toast.error(toApiError(err).message),
    });
  };

  const handleDelete = () => {
    remove.mutate(runId, {
      onSuccess: (res) => {
        setConfirm(null);
        toast.success(res?.deleted ? "Run deleted" : "Run already gone");
        onDeleted?.();
      },
      onError: (err) => toast.error(toApiError(err).message),
    });
  };

  const terminal = status === "completed" || status === "failed" || status === "cancelled";

  return (
    <>
      <div className="flex items-center gap-2">
        {(status === "queued" || status === "running") && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-destructive hover:text-destructive"
            disabled={busy}
            onClick={() => setConfirm("cancel")}
          >
            <XCircle className="size-3.5" />
            Cancel
          </Button>
        )}
        {terminal && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={busy}
            onClick={handleRestore}
          >
            <RotateCcw className="size-3.5" />
            Restore
          </Button>
        )}
        {terminal && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-destructive hover:text-destructive"
            disabled={busy}
            onClick={() => setConfirm("delete")}
          >
            <Trash2 className="size-3.5" />
            Delete
          </Button>
        )}
      </div>

      <AlertDialog open={confirm === "cancel"}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel this run?</AlertDialogTitle>
            <AlertDialogDescription>
              The pipeline will stop at its current stage. You can restore this run later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirm(null)} disabled={busy}>
              Keep running
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleCancel}
              disabled={busy}
            >
              Cancel run
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirm === "delete"}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this run?</AlertDialogTitle>
            <AlertDialogDescription>
              Its artifacts, models, reports and event history are removed permanently.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirm(null)} disabled={busy}>
              Keep run
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
              disabled={busy}
            >
              Delete run
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
