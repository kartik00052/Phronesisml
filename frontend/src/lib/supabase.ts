/**
 * Supabase client (browser, anon role) + auth-availability helpers.
 *
 * The Supabase feature is opt-in: it activates only when BOTH
 * `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are configured. Only the
 * public **anon** key is ever shipped to the browser — never the service-role
 * key. When configured, the backend must run with `AUTH_MODE=supabase` using
 * the same project, otherwise the UI and API will disagree about identity.
 *
 * When not configured, the app runs in the single-tenant "local" mode and the
 * backend's `AUTH_MODE=disabled` accepts every request without a token.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export function supabaseConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

let _client: SupabaseClient | null = null;

/** Lazily-created singleton browser client; null when Supabase is off. */
export function getSupabase(): SupabaseClient | null {
  if (!supabaseConfigured()) return null;
  if (!_client) {
    _client = createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
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