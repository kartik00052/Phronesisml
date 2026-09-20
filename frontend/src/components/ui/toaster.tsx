import { Toaster as SonnerToaster } from "sonner";

import { useResolvedTheme } from "@/stores/theme";

/**
 * App-wide toast host. Styled against the semantic tokens so notices inherit
 * the active theme. Critical information is never toast-only — toasts confirm
 * transient actions (copied, launched, saved).
 */
export function Toaster() {
  const theme = useResolvedTheme();

  return (
    <SonnerToaster
      theme={theme}
      position="bottom-right"
      closeButton
      richColors
      toastOptions={{
        classNames: {
          toast:
            "group rounded-lg border border-border bg-popover text-popover-foreground shadow-raised",
          description: "text-muted-foreground",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-muted text-muted-foreground",
        },
      }}
    />
  );
}
