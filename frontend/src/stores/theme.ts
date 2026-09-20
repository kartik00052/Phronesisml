import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useSyncExternalStore } from "react";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "phronesisml:theme";

function applyPreference(pref: ThemePreference): ResolvedTheme {
  const systemDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  const resolved: ResolvedTheme = pref === "system" ? (systemDark ? "dark" : "light") : pref;
  document.documentElement.classList.toggle("dark", resolved === "dark");
  return resolved;
}

function media() {
  return window.matchMedia?.("(prefers-color-scheme: dark)");
}

interface ThemeState {
  preference: ThemePreference;
  setPreference: (pref: ThemePreference) => void;
  toggle: () => void;
}

function initPreference(): ThemePreference {
  const stored = window.localStorage?.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      preference: initPreference(),
      setPreference: (pref) => {
        applyPreference(pref);
        set({ preference: pref });
      },
      toggle: () => {
        const next: ThemePreference = get().preference === "dark" ? "light" : "dark";
        get().setPreference(next);
      },
    }),
    { name: STORAGE_KEY, partialize: (s) => ({ preference: s.preference }) },
  ),
);

/** Reads the current resolved theme (best-effort, follows preference). */
export function resolvedTheme(): ResolvedTheme {
  const { preference } = useThemeStore.getState();
  return preference === "system"
    ? media()?.matches
      ? "dark"
      : "light"
    : preference;
}

let mediaListener: ((event: MediaQueryListEvent) => void) | null = null;

/** Keeps `document.documentElement.classList` in sync with the store. Idempotent. */
export function initTheme() {
  applyPreference(useThemeStore.getState().preference);
  const mq = media();
  if (mediaListener) {
    mq?.removeEventListener?.("change", mediaListener);
    mediaListener = null;
  }
  mediaListener = () => {
    if (useThemeStore.getState().preference === "system") {
      applyPreference("system");
    }
  };
  mq?.addEventListener?.("change", mediaListener);
}

function subscribeMedia(callback: () => void) {
  const mq = media();
  mq?.addEventListener?.("change", callback);
  return () => mq?.removeEventListener?.("change", callback);
}

/** Reactive resolved theme that re-renders on preference or system changes. */
export function useResolvedTheme(): ResolvedTheme {
  const preference = useThemeStore((s) => s.preference);
  const systemDark = useSyncExternalStore(
    subscribeMedia,
    () => media()?.matches ?? false,
    () => false,
  );
  return preference === "system" ? (systemDark ? "dark" : "light") : preference;
}