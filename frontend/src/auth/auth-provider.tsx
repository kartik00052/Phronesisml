/**
 * Supabase authentication provider.
 *
 * Three states, exposed via `useAuth()`:
 *
 * - `disabled`  — Supabase auth is not explicitly enabled
 *   (`VITE_AUTH_MODE` is not `supabase`, or the URL/publishable key is
 *   missing). The app renders normally; the backend runs
 *   `AUTH_MODE=disabled` and every request is accepted as the local-dev
 *   identity.
 * - `loading`   — Supabase is configured but the initial session restore has
 *   not finished yet. A full-screen splash is shown to avoid a flash of the
 *   login screen for already-authenticated users.
 * - `authed` / `anon` — Supabase is configured and the session state is known.
 *
 * The provider listens to `onAuthStateChange` so sign-in/sign-out from any
 * tab stays in sync.
 */
import * as React from "react";

import { getSupabase, supabaseConfigured } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "@/auth/auth-context";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<AuthStatus>(() =>
    supabaseConfigured() ? "loading" : "disabled",
  );
  const [session, setSession] = React.useState<Session | null>(null);

  const signOut = React.useCallback(async () => {
    const client = getSupabase();
    if (client) await client.auth.signOut();
    setStatus("anon");
    setSession(null);
  }, []);

  React.useEffect(() => {
    if (!supabaseConfigured()) return;
    const client = getSupabase()!;
    let active = true;

    client.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setStatus(data.session ? "authed" : "anon");
    });

    const { data: sub } = client.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setStatus(next ? "authed" : "anon");
    });

    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      status,
      session,
      userEmail: session?.user?.email ?? null,
      signOut,
    }),
    [status, session, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
