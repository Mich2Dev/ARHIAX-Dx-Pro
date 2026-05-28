/**
 * Custom hook for fetching and managing survey data.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface UseSurveyOptions {
  /** Survey token */
  token: string;
}

export function useSurvey({ token }: UseSurveyOptions) {
  const queryClient = useQueryClient();

  // Fetch survey data
  const query = useQuery({
    queryKey: ["survey", token],
    queryFn: () => api.get(`/v2/survey/${token}`).then((r) => r.data),
  });

  // Submit survey response
  const submitMutation = useMutation({
    mutationFn: (data: any) => api.post(`/v2/survey/${token}/submit`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["survey", token] });
    },
  });

  return {
    ...query,
    submit: submitMutation.mutate,
    isSubmitting: submitMutation.isPending,
    submitError: submitMutation.error,
  };
}
