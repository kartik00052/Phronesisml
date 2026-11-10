import * as React from "react";

import type { Session } from "@supabase/supabase-js";

export type AuthStatus = "disabled" | "loading" | "authed" | "anon";

export interface AuthContextValue {
  status: AuthStatus;
  session: Session | null;
  userEmail: string | null;
  signOut: () => Promise<void>;
}

export const AuthContext = React.createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth() must be used inside <AuthProvider>");
  return ctx;
}
