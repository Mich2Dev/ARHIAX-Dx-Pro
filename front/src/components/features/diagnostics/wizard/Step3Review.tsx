"use client";

import { DEPTH_PRESETS, type DepthKey } from "@/config/pipeline-presets";
import { Spinner } from "@/components/ui/Spinner";
import { Building2 } from "lucide-react";
import type { ClientData, DiagnosticDepth } from "@/lib/types";

export function Step3Review({
  client,
  depth,
  publish,
  certificate,
  onBack,
  onSubmit,
  isSubmitting,
  error,
  isExistingClient,
}: {
  client: ClientData;
  depth: DiagnosticDepth;
  publish: boolean;
  certificate: boolean;
  onBack: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  error?: string;
  isExistingClient?: boolean;
}) {
  const preset = DEPTH_PRESETS[depth as DepthKey];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-gray-900">Revision y envio</h2>
        <p className="text-sm text-gray-500 mt-1">Confirma los datos antes de iniciar el diagnostico.</p>
      </div>

      {isExistingClient ? (
        <div className="bg-brand-50 border border-brand-200 rounded-xl px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center shrink-0">
            <Building2 size={16} className="text-white" />
          </div>
          <div>
            <p className="font-semibold text-brand-900 text-sm">
              {client.organization_name || "Cliente existente"}
            </p>
            <p className="text-xs text-brand-600">
              {[client.sector || client.legal_name, client.size_org ? `${client.size_org} empleados` : ""]
                .filter(Boolean).join(" · ")}
            </p>
          </div>
        </div>
      ) : (
        <Card title="Empresa">
          <Row label="Nombre"    value={client.organization_name} />
          <Row label="NIT"       value={client.nit} />
          <Row label="Sector"    value={client.sector} />
          <Row label="Ciudad"    value={[client.city, client.country].filter(Boolean).join(", ")} />
          <Row label="Empleados" value={client.size_org} />
          <Row label="Contacto"  value={[client.contact_name, client.contact_role].filter(Boolean).join(" - ")} />
          <Row label="Email"     value={client.contact_email} />
        </Card>
      )}

      <Card title="El problema">
        <Row label="Area"           value={client.area} />
        <Row label="Sintoma"        value={client.symptom} />
        <Row label="Desde"          value={client.problem_since} />
        <Row label="Participantes"  value={client.survey_participants ? `${client.survey_participants} personas` : ""} />
        <Row label="Fecha limite"   value={client.deadline} />
        <Row label="Confidencialidad" value={client.confidentiality} />
      </Card>

      <Card title="Diagnostico">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-semibold text-gray-800">{preset.label}</span>
          <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-semibold">
            {preset.tools.length} modulos
          </span>
          <span className="text-xs text-gray-400">{preset.duration}</span>
        </div>
        <ul className="space-y-0.5">
          {preset.includes.map((item: string) => (
            <li key={item} className="text-xs text-gray-600 flex gap-1.5">
              <span className="text-green-500">v</span>{item}
            </li>
          ))}
        </ul>
        <div className="mt-2 pt-2 border-t border-gray-100 space-y-1">
          <Row label="Publicar reporte"    value={publish ? "Si (requiere aprobacion)" : "No"} />
          <Row label="Certificado digital" value={certificate ? "Si" : "No"} />
        </div>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} disabled={isSubmitting} className="btn-secondary">
          Atras
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting}
          className="btn-primary px-8 flex items-center gap-2 disabled:opacity-60"
        >
          {isSubmitting && <Spinner className="w-4 h-4" />}
          {isSubmitting ? "Iniciando diagnostico..." : "Iniciar diagnostico"}
        </button>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4 space-y-1.5">
      <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{title}</p>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-400 w-36 shrink-0">{label}</span>
      <span className="text-gray-800 font-medium">{value}</span>
    </div>
  );
}