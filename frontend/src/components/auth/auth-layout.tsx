import { Logo } from "@/components/layout/logo";

/** Centered, minimal layout for the login / sign-up screens. */
export function AuthLayout({
  title,
  description,
  footer,
  children,
}: {
  title: string;
  description: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-4 py-8">
      <div className="mb-6 flex flex-col items-center">
        <Logo className="mb-1" />
      </div>
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-5 space-y-1">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {children}
      </div>
      {footer && <div className="mt-4 max-w-sm text-center">{footer}</div>}
    </div>
  );
}