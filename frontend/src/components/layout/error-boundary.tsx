import * as React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/** App-level render error boundary with a recoverable fallback. */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[phronesisml] render error boundary caught:", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 text-center shadow-sm">
          <div className="mx-auto flex size-11 items-center justify-center rounded-full border border-danger/30 bg-danger/10 text-danger">
            <AlertTriangle className="size-5" />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-foreground">Something went wrong</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            The application hit an unexpected error. Reload to continue, or check the console for
            details.
          </p>
          {this.state.error.message && (
            <pre className="scrollbar-thin mt-4 max-h-32 overflow-auto rounded-md bg-muted/40 p-3 text-left font-mono text-xs text-danger">
              {this.state.error.message}
            </pre>
          )}
          <Button className="mt-5 gap-2" onClick={() => window.location.reload()}>
            <RotateCcw className="size-4" />
            Reload app
          </Button>
        </div>
      </div>
    );
  }
}