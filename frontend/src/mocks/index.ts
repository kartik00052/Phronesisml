/**
 * Demo mode configuration.
 *
 * The app runs in DEMO mode only when `VITE_DEMO_MODE=true` is set
 * explicitly.  By default (no env var, or `VITE_DEMO_MODE=false`) the app
 * talks to the real PhronesisML backend at `VITE_API_BASE_URL`.  Demo mode
 * uses the self-contained mock data layer in `src/mocks` and is clearly
 * signposted in the UI — mock data is never presented as real.
 */
export function isDemoMode(): boolean {
  const forced = import.meta.env.VITE_DEMO_MODE;
  if (forced === "true") return true;
  return false;
}

/** Small deterministic pseudo-random generator (mulberry32). */
export function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}