import { useState } from "react";
import { api } from "@/lib/api";
import { apiPro } from "@/lib/api-pro";

/** Descarga un PDF de diagnóstico Standard */
export function useDownloadDiagnostic() {
  const [loading, setLoading] = useState(false);

  async function download(diagnosticId: string, orgName: string) {
    setLoading(true);
    try {
      const res = await api.get(`/v2/diagnostics/${diagnosticId}/download-pdf`, { responseType: "blob" });
      _triggerDownload(res.data, "application/pdf", `diagnostico_${orgName.replace(/\s+/g, "_")}.pdf`);
    } finally {
      setLoading(false);
    }
  }

  return { download, loading };
}

/** Descarga un entregable de caso Pro (markdown | docx | pdf) */
export function useDownloadProCase() {
  const [loading, setLoading] = useState<string | null>(null);

  async function download(caseId: string, target: string, clientName: string) {
    setLoading(target);
    try {
      const res = await apiPro.get(`/pro/cases/${caseId}/download/${target}`, { responseType: "blob" });
      const ext: Record<string, string> = { markdown: "md", docx: "docx", pdf: "pdf" };
      const mime: Record<string, string> = {
        markdown: "text/markdown",
        docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        pdf: "application/pdf",
      };
      _triggerDownload(res.data, mime[target], `${clientName.replace(/\s+/g, "_")}.${ext[target]}`);
    } finally {
      setLoading(null);
    }
  }

  return { download, loading };
}

function _triggerDownload(data: any, mimeType: string, filename: string) {
  const url = window.URL.createObjectURL(new Blob([data], { type: mimeType }));
  const a = document.createElement("a");
  a.href = url;
  a.setAttribute("download", filename);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
