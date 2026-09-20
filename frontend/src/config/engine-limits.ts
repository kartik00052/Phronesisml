/**
 * Canonical demo engine-routing limits.
 *
 * 1:1 with the SDK's single source of truth in
 * `phronesisml.configs.settings`: `PANDAS_MAX_BYTES` (2 MiB) and
 * `DEFAULT_MAX_MEMORY_BYTES` (500 MiB), which drive
 * `phronesisml.engines.recommend.recommend_engine` and the run worker.
 * Demo mode (wizard recommendation, upload routing, seeded dataset reasons
 * and synthetic run summaries) must never re-implement these numbers — it
 * derives everything from these constants.
 */

/** Files strictly below this size route to pandas. */
export const PANDAS_MAX_BYTES = 2 * 1024 * 1024;

/** Files up to this size route to polars; anything larger routes to spark. */
export const POLARS_MAX_BYTES = 500 * 1024 * 1024;

export type DemoEngine = "pandas" | "polars" | "spark";

/** Byte-size routing helper mirroring `recommend_engine`'s thresholds. */
export function engineFromBytes(bytes: number): DemoEngine {
  if (bytes < PANDAS_MAX_BYTES) return "pandas";
  if (bytes <= POLARS_MAX_BYTES) return "polars";
  return "spark";
}

function formatTrimmed(num: string): string {
  return num.replace(/\.0+$/, "").replace(/\.$/, "");
}

/** Compact human byte label (e.g. "2 MB", "500 MB", "4.2 KB", "1.2 GB"). */
export function formatByteSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${formatTrimmed((bytes / 1024).toFixed(1))} KB`;
  if (bytes < 1024 ** 3) return `${formatTrimmed((bytes / (1024 * 1024)).toFixed(1))} MB`;
  return `${formatTrimmed((bytes / 1024 ** 3).toFixed(2))} GB`;
}

/**
 * The canonical engine-reason sentence (shared by the wizard handler, the
 * upload router and the seeded dataset/run summaries so demo copy can never
 * drift from the real thresholds).
 */
export function engineReason(bytes: number): string {
  const engine = engineFromBytes(bytes);
  const size = formatByteSize(bytes);
  if (engine === "pandas") return `file ${size} < ${formatByteSize(PANDAS_MAX_BYTES)} → pandas`;
  if (engine === "polars") {
    return (
      `file ${size} within polars range ` +
      `(${formatByteSize(PANDAS_MAX_BYTES)} – ${formatByteSize(POLARS_MAX_BYTES)}) → polars`
    );
  }
  return `file ${size} > ${formatByteSize(POLARS_MAX_BYTES)} → spark`;
}