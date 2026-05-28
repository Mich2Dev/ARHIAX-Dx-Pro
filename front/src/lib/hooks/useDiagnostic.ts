/**
 * Custom hook for fetching and managing diagnostic data.
 * Automatically refetches when diagnostic is in progress.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface UseDiagnosticOptions {
  /** Diagnostic ID */
  id: string;
  /** Enable auto-refetch for running diagnostics (default: true) */
  autoRefetch?: boolean;
  /** Refetch interval in ms (default: 5000) */
  refetchInterval?: number;
}

export function useDiagnostic({ 
  id, 
  autoRefetch = true,
  refetchInterval = 5000 
}: UseDiagnosticOptions) {
  return useQuery({
    queryKey: ["diagnostic", id],
    queryFn: () => api.get(`/v2/diagnostics/${id}`).then((r) => r.data),
    refetchInterval: autoRefetch 
      ? (q) => {
          const status = q.state.data?.status;
          const isActive = status === "running" || 
                          status === "pending" || 
                          status === "awaiting_responses";
          return isActive ? refetchInterval : false;
        }
      : false,
  });
}
