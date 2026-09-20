import type { StageDetail } from "@/types/pipeline";
import type { Run } from "@/types/run";

/** Context provided by the run workspace layout to its tab routes. */
export interface RunOutletContext {
  run: Run;
  stages: StageDetail[];
  logs: string[];
  live: boolean;
  refresh: () => void;
}
