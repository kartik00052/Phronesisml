/**
 * Route guards for the authentication flow.
 *
 * - `RequireAuth`: wraps the app shell. In Supabase mode it redirects
 *   anonymous users to `/login`. In disabled mode it is a no-op.
 * - `RedirectIfAuthed`: used on `/login`/`/signup`; sends already-authenticated
 *   users back to the dashboard. No-op in disabled mode.
 */
import * as React from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/auth/auth-context";
import { PageSkeleton } from "@/components/layout/page-skeleton";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <PageSkeleton />;
  if (status === "anon") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();

  if (status === "loading") return <PageSkeleton />;
  if (status === "authed") return <Navigate to="/" replace />;
  return <>{children}</>;
}