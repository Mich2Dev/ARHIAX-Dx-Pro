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
    return humanizeApiDetail(json.detail) ?? "No se pudo descargar el archivo.";
  } catch {
    /* not JSON */
  }
  return "No se pudo descargar el archivo. Verifica que el caso esté aprobado.";
}

/** Traduce 403/409 de entregables a lenguaje de consultor (nunca “status code 409”). */
export function humanizeApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    if (/aprobaci[oó]n|HIL|sell/i.test(detail)) {
      return "El informe solo se descarga después de sellar el caso.";
    }
    return detail;
  }
  if (!detail || typeof detail !== "object") return null;
  const d = detail as { message?: string; missing_sections?: string[] };
  const sections = d.missing_sections ?? [];
  if (sections.length) {
    const plain = sections.map(humanizeMissingSection).filter(Boolean);
    return (
      "El informe no se puede entregar todavía: parte del análisis no cuadra con el caso " +
      "(para no inventar contenido). " +
      (plain.length ? `Detalle: ${plain.join("; ")}. ` : "") +
      "Usá «Regenerar informe» y volvé a intentar."
    );
  }
  if (d.message) {
    if (/incoherent|incomplet|coherenc/i.test(d.message)) {
      return (
        "El informe no pasó el control de coherencia con el caso. " +
        "No lo descargamos para evitar un PDF inventado. Regenerá el informe e intentá de nuevo."
      );
    }
    return d.message;
  }
  return null;
}

function humanizeMissingSection(raw: string): string {
  const s = raw.trim();
  if (/g06_bpmn/i.test(s)) {
    return "el mapa de proceso (BPMN) no habla del síntoma del cliente";
  }
  if (/g04_cartog/i.test(s)) return "la cartografía sectorial se desvió del caso";
  if (/g03_ciencia/i.test(s)) return "la cienciometría no está anclada al síntoma";
  if (/g12_hallazgos/i.test(s)) return "los hallazgos no están anclados al caso";
  if (/g13_redactor/i.test(s)) return "la redacción ejecutiva no cuadra con el caso";
  if (/ajeno|credit|vacation|hr_/i.test(s)) return "apareció un tema ajeno al encargo";
  if (/poca relación/i.test(s)) return "poca relación con el dolor del cliente";
  return s.replace(/^Coherencia\s+/i, "").slice(0, 120);
}

async function extractDownloadError(e: unknown): Promise<string> {
  if (axios.isAxiosError(e)) {
    const status = e.response?.status;
    const data = e.response?.data;
    if (data instanceof Blob) return blobErrorMessage(data);
    if (data && typeof data === "object") {
      const human = humanizeApiDetail((data as { detail?: unknown }).detail);
      if (human) return human;
    }
    if (status === 409) {
      return (
        "El informe no pasó el control de coherencia. " +
        "No lo descargamos para evitar contenido inventado. Regenerá el informe."
      );
    }
    if (status === 403) {
      return "El informe solo se descarga después de sellar el caso.";
    }
  }
  if (e instanceof Error && /status code 409/i.test(e.message)) {
    return (
      "El informe no pasó el control de coherencia. " +
      "No lo descargamos para evitar contenido inventado. Regenerá el informe."
    );
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

  return { download, loading, error, setError };
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
