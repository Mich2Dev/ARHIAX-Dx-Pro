"use client";

import { Loader2, Check } from "lucide-react";
import type { ProClientData } from "./ProStep1Client";
import type { ProScopeData } from "./ProStep2Scope";

export interface ProConsentData {
  t1: boolean;
  t3: boolean;
}

export const defaultConsent: ProConsentData = { t1: true, t3: true };

function Row({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: "12px", padding: "6px 0", borderBottom: "1px solid rgba(23,23,23,0.05)" }}>
      <span style={{ width: "140px", flexShrink: 0, fontSize: "11px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>{label}</span>
      <span style={{ fontSize: "13px", color: "#171717" }}>{value}</span>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(23,23,23,0.02)", border: "1px solid rgba(23,23,23,0.08)", padding: "16px 20px", marginBottom: "16px" }}>
      <p style={{ margin: "0 0 12px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
        {title}
      </p>
      {children}
    </div>
  );
}

export function ProStep3Review({
  client, scope, consent, onConsent,
  onBack, onSubmit, isSubmitting, error,
}: {
  client: ProClientData;
  scope: ProScopeData;
  consent: ProConsentData;
  onConsent: (c: ProConsentData) => void;
  onBack: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  error?: string;
}) {
  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Revisión y envío
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Confirma los datos antes de iniciar el ciclo de fusión gobernado.
        </p>
      </div>

      {/* Empresa */}
      <Card title="EMPRESA">
        <Row label="Nombre comercial"  value={client.client_name} />
        <Row label="Razón social"      value={client.legal_name} />
        <Row label="NIT"               value={client.nit} />
        <Row label="Sector"            value={client.sector} />
        <Row label="Ciudad"            value={[client.city, client.country].filter(Boolean).join(", ")} />
        <Row label="Empleados"         value={client.size_org} />
        <Row label="Contacto"          value={[client.contact_name, client.contact_role].filter(Boolean).join(" · ")} />
        <Row label="Email"             value={client.contact_email} />
      </Card>

      {/* Problema */}
      <Card title="EL PROBLEMA">
        <Row label="Dominio"           value={client.domain} />
        <Row label="Síntoma"           value={client.symptom} />
        <Row label="Desde"             value={client.problem_since} />
        <Row label="Resultado esperado" value={client.expected_outcome} />
        <Row label="Confidencialidad"  value={client.confidentiality} />
      </Card>

      {/* Alcance */}
      <Card title="ALCANCE PRO">
        <Row label="Roles"       value={scope.roles.join(", ")} />
        <Row label="Dimensiones" value={scope.dimensions.join(", ")} />
        {scope.hypotheses.filter(h => h.trim()).length > 0 && (
          <Row label="Hipótesis" value={`${scope.hypotheses.filter(h => h.trim()).length} definidas`} />
        )}
        {scope.grey_sources.filter(g => g.trim()).length > 0 && (
          <Row label="Fuentes" value={`${scope.grey_sources.filter(g => g.trim()).length} fuentes`} />
        )}
        <Row label="Engagement ID" value={client.engagement_id || "Se genera automáticamente"} />
      </Card>

      {/* Consentimiento */}
      <div style={{ border: "1px solid rgba(23,23,23,0.12)", padding: "20px", marginBottom: "16px" }}>
        <p style={{ margin: "0 0 14px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
          CONSENTIMIENTO DE PROCESAMIENTO
        </p>
        {[
          { key: "t1" as const, label: "T1 — Procesamiento de datos organizacionales", desc: "Autorizo el procesamiento de datos de la organización para el diagnóstico gobernado." },
          { key: "t3" as const, label: "T3 — Ingesta a modelo de lenguaje", desc: "Autorizo el envío de datos al modelo de lenguaje para análisis diagnóstico PMEL/ATK." },
        ].map(({ key, label, desc }) => (
          <label key={key} style={{ display: "flex", gap: "12px", cursor: "pointer", alignItems: "flex-start", marginBottom: "12px" }}>
            <div
              onClick={() => onConsent({ ...consent, [key]: !consent[key] })}
              style={{
                width: "18px", height: "18px", flexShrink: 0, marginTop: "2px",
                border: `1px solid ${consent[key] ? "#222522" : "rgba(23,23,23,0.2)"}`,
                background: consent[key] ? "#222522" : "transparent",
                display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
              }}
            >
              {consent[key] && <Check size={11} color="#f4f1ea" />}
            </div>
            <div>
              <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>{label}</p>
              <p style={{ margin: "3px 0 0", fontSize: "12px", color: "#706f69" }}>{desc}</p>
            </div>
          </label>
        ))}
      </div>

      {error && (
        <div style={{ padding: "12px 16px", border: "1px solid rgba(139,58,58,0.3)", borderLeft: "3px solid #8b3a3a", background: "rgba(139,58,58,0.05)", marginBottom: "16px", fontSize: "13px", color: "#6b2f2f" }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px" }}>
        <button onClick={onBack} disabled={isSubmitting} style={{ height: "38px", padding: "0 20px", background: "transparent", color: "#706f69", border: "1px solid rgba(23,23,23,0.14)", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer" }}>
          ← Atrás
        </button>
        <button
          onClick={onSubmit}
          disabled={!consent.t1 || isSubmitting}
          style={{
            display: "flex", alignItems: "center", gap: "8px",
            height: "38px", padding: "0 24px",
            background: "#56624b", color: "#f4f1ea",
            border: "none", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace",
            cursor: (!consent.t1 || isSubmitting) ? "not-allowed" : "pointer",
            opacity: (!consent.t1 || isSubmitting) ? 0.5 : 1,
          }}
        >
          {isSubmitting
            ? <><Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} /> Iniciando ciclo...</>
            : <><Check size={13} /> Iniciar diagnóstico Pro</>
          }
        </button>
      </div>
    </div>
  );
}
