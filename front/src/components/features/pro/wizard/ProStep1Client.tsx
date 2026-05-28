"use client";

import { SECTORS, AREAS } from "@/config/pipeline-presets";
import { COUNTRIES, getCities } from "@/lib/utils/geo";

// ── tipos ─────────────────────────────────────────────────────────────────────
export interface ProClientData {
  // Identidad
  client_name: string;
  legal_name: string;
  nit: string;
  sector: string;
  city: string;
  country: string;
  size_org: string;
  years_operating: string;
  // Contacto
  contact_name: string;
  contact_role: string;
  contact_email: string;
  contact_phone: string;
  // Problema
  domain: string;
  symptom: string;
  problem_since: string;
  areas_count: string;
  previous_attempts: string;
  expected_outcome: string;
  // Alcance
  engagement_id: string;
  deadline: string;
  confidentiality: string;
}

export const defaultClient: ProClientData = {
  client_name: "", legal_name: "", nit: "", sector: "",
  city: "", country: "Colombia", size_org: "", years_operating: "",
  contact_name: "", contact_role: "", contact_email: "", contact_phone: "",
  domain: "", symptom: "", problem_since: "", areas_count: "1",
  previous_attempts: "", expected_outcome: "",
  engagement_id: "", deadline: "", confidentiality: "Confidencial - Uso Estratégico",
};

// ── estilos compartidos ───────────────────────────────────────────────────────
const inp: React.CSSProperties = {
  width: "100%", minHeight: "38px", padding: "8px 12px",
  border: "1px solid rgba(23,23,23,0.18)",
  background: "rgba(255,255,255,0.6)",
  backdropFilter: "blur(4px)",
  color: "#171717", fontFamily: "Manrope, sans-serif", fontSize: "13px",
  outline: "none", boxSizing: "border-box",
  transition: "border-color 0.15s, background 0.15s",
};
const lbl: React.CSSProperties = {
  display: "block", marginBottom: "6px",
  fontSize: "11px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace",
  letterSpacing: "0.02em",
};
const err: React.CSSProperties = {
  fontSize: "10px", color: "#8b3a3a", marginTop: "4px",
  fontFamily: "IBM Plex Mono, monospace",
};

// ── helpers ───────────────────────────────────────────────────────────────────
function Field({ label, error, children, span2 }: {
  label: string; error?: string; children: React.ReactNode; span2?: boolean;
}) {
  return (
    <div style={{ gridColumn: span2 ? "1 / -1" : undefined, minWidth: 0 }}>
      <label style={lbl}>{label}</label>
      {children}
      {error && <p style={err}>{error}</p>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "28px" }}>
      <p style={{
        margin: "0 0 16px", fontSize: "11px", fontWeight: 500, color: "#171717",
        fontFamily: "IBM Plex Mono, monospace", paddingBottom: "10px",
        borderBottom: "1px solid rgba(23,23,23,0.1)", letterSpacing: "0.04em",
      }}>{title}</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", minWidth: 0 }}>
        {children}
      </div>
    </div>
  );
}

// ── componente ────────────────────────────────────────────────────────────────
export function ProStep1Client({
  data, onChange, onNext, errors,
}: {
  data: ProClientData;
  onChange: (d: ProClientData) => void;
  onNext: () => void;
  errors: Partial<Record<keyof ProClientData, string>>;
}) {
  const set = (k: keyof ProClientData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    onChange({ ...data, [k]: e.target.value });

  const cities = getCities(data.country);

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Datos del cliente
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Información de la organización y el problema a diagnosticar.
        </p>
      </div>

      {/* Identidad */}
      <Section title="🏢 Identidad de la empresa">
        <Field label="Nombre comercial *" error={errors.client_name}>
          <input style={inp} value={data.client_name} onChange={set("client_name")} placeholder="Empresa S.A.S." />
        </Field>
        <Field label="Razón social (nombre legal) *" error={errors.legal_name}>
          <input style={inp} value={data.legal_name} onChange={set("legal_name")} placeholder="Empresa S.A.S." />
        </Field>
        <Field label="NIT *" error={errors.nit}>
          <input style={inp} value={data.nit} onChange={set("nit")} placeholder="900.123.456-7" />
        </Field>
        <Field label="Sector económico *" error={errors.sector}>
          <select style={inp} value={data.sector} onChange={set("sector")}>
            <option value="">Seleccionar...</option>
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="País *" error={errors.country}>
          <select style={inp} value={data.country} onChange={set("country")}>
            {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Ciudad *" error={errors.city}>
          <select style={inp} value={data.city} onChange={set("city")}>
            <option value="">Seleccionar...</option>
            {cities.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Número de empleados *" error={errors.size_org}>
          <input style={inp} type="number" min="1" value={data.size_org} onChange={set("size_org")} placeholder="250" />
        </Field>
        <Field label="Años de operación *" error={errors.years_operating}>
          <input style={inp} type="number" min="0" value={data.years_operating} onChange={set("years_operating")} placeholder="12" />
        </Field>
      </Section>

      {/* Contacto */}
      <Section title="👤 Contacto principal">
        <Field label="Nombre completo *" error={errors.contact_name}>
          <input style={inp} value={data.contact_name} onChange={set("contact_name")} placeholder="Juan Pérez" />
        </Field>
        <Field label="Cargo *" error={errors.contact_role}>
          <input style={inp} value={data.contact_role} onChange={set("contact_role")} placeholder="Gerente de Operaciones" />
        </Field>
        <Field label="Correo electrónico *" error={errors.contact_email}>
          <input style={inp} type="email" value={data.contact_email} onChange={set("contact_email")} placeholder="juan@empresa.co" />
        </Field>
        <Field label="Teléfono / WhatsApp *" error={errors.contact_phone}>
          <input style={inp} value={data.contact_phone} onChange={set("contact_phone")} placeholder="+57 300 123 4567" />
        </Field>
      </Section>

      {/* El problema */}
      <Section title="🔍 El problema a diagnosticar">
        <Field label="Dominio / área a diagnosticar *" error={errors.domain}>
          <select style={inp} value={data.domain} onChange={set("domain")}>
            <option value="">Seleccionar...</option>
            {AREAS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </Field>
        <Field label="¿Hace cuánto viene el problema? *" error={errors.problem_since}>
          <input style={inp} value={data.problem_since} onChange={set("problem_since")} placeholder="Ej: 6 meses, 2 años" />
        </Field>
        <Field label="¿Cuál es el síntoma o problema principal? *" error={errors.symptom} span2>
          <textarea style={{ ...inp, minHeight: "80px", resize: "vertical" }} value={data.symptom} onChange={set("symptom")}
            placeholder="Ej: Los pedidos están llegando tarde, hay alta rotación en el área de producción..." />
        </Field>
        <Field label="¿Cuántas áreas o sedes involucra?" error={errors.areas_count}>
          <input style={inp} type="number" min="1" value={data.areas_count} onChange={set("areas_count")} placeholder="1" />
        </Field>
        <Field label="¿Qué han intentado antes? (opcional)" error={errors.previous_attempts}>
          <input style={inp} value={data.previous_attempts} onChange={set("previous_attempts")} placeholder="Ej: Consultoría en 2023, cambio de ERP..." />
        </Field>
        <Field label="¿Qué espera obtener con este diagnóstico? *" error={errors.expected_outcome} span2>
          <textarea style={{ ...inp, minHeight: "64px", resize: "vertical" }} value={data.expected_outcome} onChange={set("expected_outcome")}
            placeholder="Ej: Identificar causas raíz, tener un plan de acción claro..." />
        </Field>
      </Section>

      {/* Alcance */}
      <Section title="📐 Alcance del caso">
        <Field label="ID de engagement (opcional)" error={errors.engagement_id}>
          <input style={inp} value={data.engagement_id} onChange={set("engagement_id")} placeholder="Ej: eng-2025-001 (se genera automáticamente)" />
        </Field>
        <Field label="Fecha límite (opcional)" error={errors.deadline}>
          <input style={inp} type="date" value={data.deadline} onChange={set("deadline")} />
        </Field>
        <Field label="Nivel de confidencialidad" error={errors.confidentiality} span2>
          <select style={inp} value={data.confidentiality} onChange={set("confidentiality")}>
            <option value="Confidencial - Uso Estratégico">Confidencial — Uso Estratégico</option>
            <option value="Restringido - Solo Dirección">Restringido — Solo Dirección</option>
            <option value="Interno">Interno</option>
          </select>
        </Field>
      </Section>

      <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "8px" }}>
        <button onClick={onNext} style={{
          height: "38px", padding: "0 24px", background: "#171717", color: "#f4f1ea",
          border: "none", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
        }}>
          Siguiente →
        </button>
      </div>
    </div>
  );
}
