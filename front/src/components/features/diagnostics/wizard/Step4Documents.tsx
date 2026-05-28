"use client";

import { useState, useRef } from "react";
import { Upload, X, FileText, FileSpreadsheet, Image, File, CheckCircle } from "lucide-react";
import { Spinner } from "@/components/ui/Spinner";

export interface UploadedDoc {
  id?: string;           // set after upload
  file: File;
  doc_type: string;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
  size_human?: string;
}

const DOC_TYPES = [
  { value: "context",     label: "Descripción del problema" },
  { value: "organigrama", label: "Organigrama" },
  { value: "financiero",  label: "Datos financieros / KPIs" },
  { value: "proceso",     label: "Manual de proceso" },
  { value: "otro",        label: "Otro" },
];

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"];
const MAX_FILES = 5;
const MAX_SIZE_MB = 10;

function fileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (["pdf", "docx", "doc", "txt"].includes(ext || "")) return <FileText size={18} className="text-blue-500" />;
  if (["xlsx", "xls"].includes(ext || "")) return <FileSpreadsheet size={18} className="text-green-500" />;
  if (["png", "jpg", "jpeg"].includes(ext || "")) return <Image size={18} className="text-purple-500" />;
  return <File size={18} className="text-gray-400" />;
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Step4Documents({
  diagnosticId,
  onDone,
  onSkip,
}: {
  diagnosticId: string;
  onDone: () => void;
  onSkip: () => void;
}) {
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | null) {
    if (!files) return;
    const newDocs: UploadedDoc[] = [];
    for (const file of Array.from(files)) {
      if (docs.length + newDocs.length >= MAX_FILES) break;
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) continue;
      if (file.size > MAX_SIZE_MB * 1024 * 1024) continue;
      newDocs.push({ file, doc_type: "context", status: "pending" });
    }
    setDocs(prev => [...prev, ...newDocs]);
  }

  function removeDoc(idx: number) {
    setDocs(prev => prev.filter((_, i) => i !== idx));
  }

  function setDocType(idx: number, type: string) {
    setDocs(prev => prev.map((d, i) => i === idx ? { ...d, doc_type: type } : d));
  }

  async function uploadAll() {
    const pending = docs.filter(d => d.status === "pending");
    if (pending.length === 0) { onDone(); return; }

    for (let i = 0; i < docs.length; i++) {
      if (docs[i].status !== "pending") continue;

      setDocs(prev => prev.map((d, idx) => idx === i ? { ...d, status: "uploading" } : d));

      try {
        const form = new FormData();
        form.append("file", docs[i].file);
        form.append("doc_type", docs[i].doc_type);

        const token = localStorage.getItem("token");
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/v2/diagnostics/${diagnosticId}/documents`,
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: form,
          }
        );

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        setDocs(prev => prev.map((d, idx) =>
          idx === i ? { ...d, status: "done", id: data.id, size_human: data.size_human } : d
        ));
      } catch (err: any) {
        setDocs(prev => prev.map((d, idx) =>
          idx === i ? { ...d, status: "error", error: err.message } : d
        ));
      }
    }

    onDone();
  }

  const allDone = docs.every(d => d.status === "done");
  const anyUploading = docs.some(d => d.status === "uploading");

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-gray-900">Documentos de contexto</h2>
        <p className="text-sm text-gray-500 mt-1">
          Opcional — Sube documentos que ayuden a los agentes a entender mejor el problema.
          Pueden ser reportes, organigramas, manuales o cualquier descripción detallada.
        </p>
      </div>

      {/* Drop zone */}
      {docs.length < MAX_FILES && (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            dragOver
              ? "border-brand-500 bg-brand-50"
              : "border-gray-200 hover:border-brand-300 hover:bg-gray-50"
          }`}
        >
          <Upload size={28} className="mx-auto text-gray-400 mb-2" />
          <p className="text-sm font-semibold text-gray-700">
            Arrastra archivos aquí o haz click para seleccionar
          </p>
          <p className="text-xs text-gray-400 mt-1">
            PDF, DOCX, TXT, XLSX, PNG, JPG · Máx. {MAX_SIZE_MB} MB por archivo · Máx. {MAX_FILES} archivos
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ALLOWED_EXTENSIONS.join(",")}
            className="hidden"
            onChange={e => addFiles(e.target.files)}
          />
        </div>
      )}

      {/* File list */}
      {docs.length > 0 && (
        <div className="space-y-2">
          {docs.map((doc, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                doc.status === "done"    ? "border-green-200 bg-green-50" :
                doc.status === "error"  ? "border-red-200 bg-red-50" :
                doc.status === "uploading" ? "border-blue-200 bg-blue-50" :
                "border-gray-200 bg-white"
              }`}
            >
              {/* Icon */}
              <div className="shrink-0">{fileIcon(doc.file.name)}</div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{doc.file.name}</p>
                <p className="text-xs text-gray-400">{humanSize(doc.file.size)}</p>
                {doc.status === "error" && (
                  <p className="text-xs text-red-600 mt-0.5">{doc.error}</p>
                )}
              </div>

              {/* Type selector */}
              {doc.status === "pending" && (
                <select
                  value={doc.doc_type}
                  onChange={e => setDocType(i, e.target.value)}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white shrink-0"
                >
                  {DOC_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              )}

              {/* Status indicator */}
              {doc.status === "uploading" && (
                <Spinner className="w-4 h-4 border-blue-500 border-t-blue-200 shrink-0" />
              )}
              {doc.status === "done" && (
                <CheckCircle size={18} className="text-green-500 shrink-0" />
              )}

              {/* Remove */}
              {doc.status === "pending" && (
                <button
                  onClick={() => removeDoc(i)}
                  className="shrink-0 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* What these docs are used for */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
        <p className="text-xs font-semibold text-blue-800 mb-2">¿Para qué sirven estos documentos?</p>
        <ul className="space-y-1">
          {[
            "Los agentes IA extraen el texto y lo usan como contexto adicional",
            "Mejoran la precisión de las hipótesis y brechas detectadas",
            "Permiten que las preguntas de la encuesta sean más específicas",
            "El texto se procesa de forma confidencial y no se comparte externamente",
          ].map((item, i) => (
            <li key={i} className="text-xs text-blue-700 flex gap-1.5">
              <span className="shrink-0">·</span>{item}
            </li>
          ))}
        </ul>
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-2">
        <button
          type="button"
          onClick={onSkip}
          className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Omitir este paso →
        </button>

        {docs.length > 0 && (
          <button
            type="button"
            onClick={uploadAll}
            disabled={anyUploading || allDone}
            className="btn-primary px-8 flex items-center gap-2 disabled:opacity-60"
          >
            {anyUploading && <Spinner className="w-4 h-4" />}
            {anyUploading ? "Subiendo..." : allDone ? "Continuar →" : `Subir ${docs.filter(d => d.status === "pending").length} archivo(s) →`}
          </button>
        )}
      </div>
    </div>
  );
}
