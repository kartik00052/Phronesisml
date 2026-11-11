/**
 * Supabase client (browser, anon role) + auth-availability helpers.
 *
 * The Supabase feature is explicitly opt-in: it activates only when
 * `VITE_AUTH_MODE=supabase` AND both `VITE_SUPABASE_URL` and
 * `VITE_SUPABASE_PUBLISHABLE_KEY` are configured. Stale Supabase credentials
 * alone must never force the login gate on a no-auth prototype deployment.
 * Only the public **publishable** key is ever shipped to the browser - never
 * a service role/secret key. When configured, the backend must run with
 * `AUTH_MODE=supabase` using the same project, otherwise the UI and API will
 * disagree about identity.
 *
 * When not configured, the app runs in the single-tenant "local" mode and the
 * backend's `AUTH_MODE=disabled` accepts every request without a token.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const AUTH_MODE = (import.meta.env.VITE_AUTH_MODE as string | undefined)
  ?.trim()
  .toLowerCase();
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined)?.trim();
const SUPABASE_PUBLISHABLE_KEY = (
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined
)?.trim();

export function supabaseConfigured(): boolean {
  return (
    AUTH_MODE === "supabase" &&
    Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY)
  );
}

let _client: SupabaseClient | null = null;

/** Lazily-created singleton browser client; null when Supabase is off. */
export function getSupabase(): SupabaseClient | null {
  if (!supabaseConfigured()) return null;
  if (!_client) {
    _client = createClient(SUPABASE_URL!, SUPABASE_PUBLISHABLE_KEY!, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }
  return _client;
}

/**
 * Current access token, if a session exists. Used for the `Authorization`
 * header on every API request and the `access_token` query param on the run
 * events WebSocket.
 */
export async function getAccessToken(): Promise<string | null> {
  const client = getSupabase();
  if (!client) return null;
  const { data } = await client.auth.getSession();
  return data.session?.access_token ?? null;
}