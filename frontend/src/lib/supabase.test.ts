import { afterEach, describe, expect, it, vi } from "vitest";

async function loadSupabaseModule() {
  vi.resetModules();
  return import("@/lib/supabase");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("supabase auth opt-in", () => {
  it("stays disabled when stale credentials exist without VITE_AUTH_MODE", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test");
    vi.stubEnv("VITE_AUTH_MODE", "");

    const { getSupabase, supabaseConfigured } = await loadSupabaseModule();

    expect(supabaseConfigured()).toBe(false);
    expect(getSupabase()).toBeNull();
  });

  it("stays disabled when VITE_AUTH_MODE=supabase but credentials are missing", async () => {
    vi.stubEnv("VITE_AUTH_MODE", "supabase");
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "");

    const { supabaseConfigured } = await loadSupabaseModule();

    expect(supabaseConfigured()).toBe(false);
  });

  it("enables only when the flag and both credentials are present", async () => {
    vi.stubEnv("VITE_AUTH_MODE", "supabase");
    vi.stubEnv("VITE_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test");

    const { supabaseConfigured } = await loadSupabaseModule();

    expect(supabaseConfigured()).toBe(true);
  });
});
