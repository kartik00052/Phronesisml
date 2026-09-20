import { useQuery } from "@tanstack/react-query";

import { getCapabilities, getHealth } from "@/api/health";

export const queryKeys = {
  health: () => ["health"] as const,
  capabilities: () => ["capabilities"] as const,
};

export function useHealth() {
  return useQuery({ queryKey: queryKeys.health(), queryFn: getHealth });
}

export function useCapabilities() {
  return useQuery({ queryKey: queryKeys.capabilities(), queryFn: getCapabilities });
}