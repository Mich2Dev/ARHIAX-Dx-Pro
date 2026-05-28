/**
 * Custom hook for fetching list of diagnostics with filtering.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type DiagnosticFilter = "all" | "completed" | "running" | "denied";

interface UseDiagnosticsOptions {
  /** Filter by status */
  filter?: DiagnosticFilter;
  /** Enable auto-refetch (default: true) */
  autoRefetch?: boolean;
  /** Refetch interval in ms (default: 10000) */
  refetchInterval?: number;
}

export function useDiagnostics({ 
  filter = "all",
  autoRefetch = true,
  refetchInterval = 10000
}: UseDiagnosticsOptions = {}) {
  return useQuery({
    queryKey: ["diagnostics", filter],
    queryFn: async () => {
      const response = await api.get("/v2/diagnostics");
      const diagnostics = response.data;

      // Apply filter
      if (filter === "all") return diagnostics;
      
      return diagnostics.filter((d: any) => {
        switch (filter) {
          case "completed":
            return d.status === "completed";
          case "running":
            return d.status === "running" || d.status === "pending" || d.status === "awaiting_responses";
          case "denied":
            return d.status === "denied" || d.status === "failed";
          default:
            return true;
        }
      });
    },
    refetchInterval: autoRefetch ? refetchInterval : false,
  });
}
