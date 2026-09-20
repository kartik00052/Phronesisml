import * as React from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/auth/auth-context";
import { AuthLayout } from "@/components/auth/auth-layout";
import { getSupabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const client = getSupabase();
    if (!client) return;
    setSubmitting(true);
    try {
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw error;
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Sign-in failed. Please try again.";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your account to continue."
      footer={
        <p className="text-sm text-muted-foreground">
          No account yet?{" "}
          <Link
            to="/signup"
            className="font-medium text-foreground underline underline-offset-4"
          >
            Create one
          </Link>
          <span className="mx-2 text-border">·</span>
          <button
            type="button"
            onClick={() => void signOut()}
            className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Return to local mode
          </button>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
}