import { useState } from "react";
import axios from "axios";
import { api } from "@/lib/api";
import { apiPro } from "@/lib/api-pro";

const WIN_RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;

/** Nombre seguro para Windows: evita `algo.exe.pdf` que el Explorador muestra como .exe */
function safeDownloadName(clientName: string, ext: string): string {
  const base = (clientName || "diagnostico")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\s-]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^\.+|\.+$/g, "")
    .slice(0, 60) || "diagnostico";
  const safe = WIN_RESERVED.test(base) ? `${base}_informe` : base;
  return `${safe}_diagnostico.${ext}`;
}

async function blobErrorMessage(data: Blob): Promise<string> {
  try {
    const text = await data.text();
    const json = JSON.parse(text);
    if (typeof json.detail === "string") return json.detail;
    if (json.detail && typeof json.detail === "object") {
      const d = json.detail as { message?: string; missing_sections?: string[] };
      if (d.missing_sections?.length) {
        return `${d.message ?? "PDF incompleto"}: ${d.missing_sections.join(", ")}`;
      }
      return d.message ?? JSON.stringify(json.detail);
    }
    if (Array.isArray(json.detail)) return json.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ");
  } catch {
    /* not JSON */
  }
  return "No se pudo descargar el archivo. Verifica que el caso esté aprobado.";
}

async function extractDownloadError(e: unknown): Promise<string> {
  if (axios.isAxiosError(e) && e.response?.data) {
    const data = e.response.data;
    if (data instanceof Blob) return blobErrorMessage(data);
    if (typeof data === "object" && data !== null) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (detail && typeof detail === "object") {
        const d = detail as { message?: string; missing_sections?: string[] };
        if (d.missing_sections?.length) {
          return `${d.message ?? "Entregable incompleto"}: ${d.missing_sections.join(", ")}`;
        }
        return d.message ?? JSON.stringify(detail);
      }
    }
  }
  return e instanceof Error ? e.message : "Error al descargar";
}

async function readBlobArrayBuffer(data: Blob): Promise<ArrayBuffer> {
  return data.arrayBuffer();
}

function pdfMagicOk(buf: ArrayBuffer): boolean {
  const view = new Uint8Array(buf);
  return view.length >= 4 && String.fromCharCode(view[0], view[1], view[2], view[3]) === "%PDF";
}

/** Descarga un PDF de diagnóstico Standard */
export function useDownloadDiagnostic() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download(diagnosticId: string, orgName: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/v2/diagnostics/${diagnosticId}/download-pdf`, { responseType: "blob" });
      const buf = await readBlobArrayBuffer(res.data);
      if (!pdfMagicOk(buf)) {
        throw new Error(await blobErrorMessage(res.data));
      }
      _triggerDownload(new Blob([buf], { type: "application/pdf" }), safeDownloadName(orgName, "pdf"));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al descargar PDF");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  return { download, loading, error };
}

/** Descarga un entregable de caso Pro (markdown | docx | pdf) */
export function useDownloadProCase() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(caseId: string, target: string, clientName: string) {
    setLoading(target);
    setError(null);
    try {
      const res = await apiPro.get(`/pro/cases/${caseId}/download/${target}`, { responseType: "blob" });
      const mime: Record<string, string> = {
        markdown: "text/markdown;charset=utf-8",
        docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        pdf: "application/pdf",
      };
      const ext: Record<string, string> = { markdown: "md", docx: "docx", pdf: "pdf" };
      const buf = await readBlobArrayBuffer(res.data);

      if (target === "pdf" && !pdfMagicOk(buf)) {
        throw new Error(await blobErrorMessage(res.data));
      }

      _triggerDownload(new Blob([buf], { type: mime[target] }), safeDownloadName(clientName, ext[target]));
    } catch (e: unknown) {
      const msg = await extractDownloadError(e);
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(null);
    }
  }

  return { download, loading, error };
}

function _triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
