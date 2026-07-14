"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { apiPro } from "@/lib/api-pro";
import { CaseWorkspace } from "@/components/features/pro/case-workspace/CaseWorkspace";

export default function ProCaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [reviewComment, setReviewComment] = useState("");

  const { data: caseData, isLoading, isError: isQueryError, isFetching } = useQuery({
    queryKey: ["pro-case", id],
    queryFn: () => apiPro.get(`/pro/cases/${id}`).then((r) => r.data),
    refetchInterval: (q: any) => {
      const data = q.state.data;
      const status = data?.case_status;
      if (status === "running") return 5000;
      if (data?.phenomenon?.status === "running") return 4000;
      if (status === "survey_open" || data?.survey?.status === "designing") return 4000;
      if (!data) return 6000;
      return false;
    },
    retry: 5,
    retryDelay: (attempt) => Math.min(2000 * (attempt + 1), 10000),
    staleTime: 0,
  });

  const approvalMutation = useMutation({
    mutationFn: ({ action, comment }: { action: string; comment?: string }) =>
      apiPro.post(`/pro/cases/${id}/approval`, { action, comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-case", id] });
      qc.invalidateQueries({ queryKey: ["pro-cases"] });
      setReviewComment("");
    },
  });

  const runMutation = useMutation({
    mutationFn: () => apiPro.post(`/pro/cases/${id}/run`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-case", id] });
      qc.invalidateQueries({ queryKey: ["pro-cases"] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Error al iniciar el diagnóstico.");
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => apiPro.post(`/pro/cases/${id}/analyze`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-case", id] });
    },
    onError: (err: any) => {
      alert(err.message || "Error al analizar el fenómeno.");
    },
  });

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "80px 0" }}>
        <Loader2 size={24} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
      </div>
    );
  }

  if (!caseData && isQueryError) {
    return (
      <div
        style={{
          padding: "48px 0",
          textAlign: "center",
          color: "#706f69",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 13,
        }}
      >
        No se pudo cargar el caso. Reintente en unos segundos.
      </div>
    );
  }

  if (!caseData) {
    return (
      <div
        style={{
          padding: "48px 0",
          textAlign: "center",
          color: "#706f69",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 13,
        }}
      >
        Caso no encontrado.
      </div>
    );
  }

  return (
    <CaseWorkspace
      caseId={id}
      caseData={caseData}
      isFetching={isFetching}
      reviewComment={reviewComment}
      onReviewComment={setReviewComment}
      onAnalyze={() => analyzeMutation.mutate()}
      analyzing={analyzeMutation.isPending}
      onRun={() => runMutation.mutate()}
      runningDiag={runMutation.isPending}
      onApprove={(action) => approvalMutation.mutate({ action, comment: reviewComment })}
      approving={approvalMutation.isPending}
      approveError={approvalMutation.isError}
      onRefresh={() => qc.invalidateQueries({ queryKey: ["pro-case", id] })}
    />
  );
}
