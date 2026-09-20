/**
 * System health & capabilities types.
 * 1:1 with backend `health()` and `capabilities()`.
 */

export interface DependencyInfo {
  installed: boolean;
  version?: string;
  optional?: boolean;
}

/** Live backend probe state: database reachability / storage writability. */
export interface HealthProbeState {
  reachable?: boolean;
  writable?: boolean;
  paths?: string[];
  error?: string | null;
}

export interface HealthReport {
  status: "ok" | "degraded";
  version: string;
  python: string;
  dependencies: Record<string, DependencyInfo>;
  missing_core: string[];
  database?: HealthProbeState;
  storage?: HealthProbeState;
}

export interface EngineCapabilityMatrix {
  engine: string;
  capabilities: Record<string, boolean>;
}

export interface OptionalModelInfo {
  name: string;
  installed: boolean;
  version?: string;
  optional?: boolean;
  reason?: string | null;
}

export interface CapabilitiesReport {
  name: string;
  version: string;
  offline: boolean;
  deterministic: boolean;
  task_types: string[];
  engines: string[];
  explainers: string[];
  pipeline_stages: string[];
  sdk_methods: string[];
  cli_commands: string[];
  extras: string[];
  /** Dynamically probed optional model backends (never hard-coded). */
  optional_models?: OptionalModelInfo[];
}
