"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { SECTORS, AREAS } from "@/config/pipeline-presets";
import { COUNTRIES, getCities } from "@/lib/utils/geo";
import type { ClientData } from "@/lib/types";
import { coherentText, coherentName } from "@/lib/utils/validation";

const schema = z.object({
  organization_name:   coherentName("Nombre comercial"),
  legal_name:          coherentName("Razón social"),
  nit:                 z.string().min(5, "Requerido"),
  sector:              z.string().min(1, "Selecciona un sector"),
  city:                z.string().min(2, "Requerido"),
  country:             z.string().min(2, "Requerido"),
  size_org:            z.string().min(1, "Requerido"),
  years_operating:     z.string().min(1, "Requerido"),
  contact_name:        coherentName("Nombre del contacto"),
  contact_role:        z.string().min(2, "Requerido"),
  contact_email:       z.string().email("Email inválido"),
  contact_phone:       z.string().min(7, "Requerido"),
  area:                z.string().min(1, "Selecciona un área"),
  symptom:             coherentText(20, "El síntoma"),
  problem_since:       z.string().min(1, "Requerido"),
  previous_attempts:   z.string().optional().default(""),
  expected_outcome:    coherentText(10, "El resultado esperado"),
  areas_count:         z.string().min(1, "Requerido"),
  survey_participants: z.string().min(1, "Requerido"),
  deadline:            z.string().optional().default(""),
  confidentiality:     z.string(),
});

export function Step1ClientData({
  data,
  onChange,
  onNext,
}: {
  data: ClientData;
  onChange: (d: ClientData) => void;
  onNext: () => void;
}) {
  const { register, handleSubmit, control, formState: { errors } } = useForm<ClientData>({
    resolver: zodResolver(schema),
    defaultValues: data,
  });

  const selectedCountry = useWatch({ control, name: "country", defaultValue: data.country });
  const cities = getCities(selectedCountry);

  function onSubmit(values: ClientData) {
    onChange(values);
    onNext();
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: "grid", gap: "0" }}>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Datos del cliente
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Información de la empresa y el problema a diagnosticar.
        </p>
      </div>

      {/* ── Identidad ── */}
      <Section title="🏢 Identidad de la empresa">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
          <Field label="Nombre comercial" error={errors.organization_name?.message} full>
            <input {...register("organization_name")} className="input" placeholder="Empresa S.A.S." />
          </Field>
          <Field label="Razón social (nombre legal)" error={errors.legal_name?.message} full>
            <input {...register("legal_name")} className="input" placeholder="Empresa S.A.S." />
          </Field>
          <Field label="NIT" error={errors.nit?.message}>
            <input {...register("nit")} className="input" placeholder="900.123.456-7" />
          </Field>
          <Field label="Sector económico" error={errors.sector?.message}>
            <select {...register("sector")} className="input">
              <option value="">Seleccionar...</option>
              {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="Ciudad" error={errors.city?.message}>
            <select {...register("city")} className="input">
              <option value="">Seleccionar...</option>
              {cities.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="País" error={errors.country?.message}>
            <select {...register("country")} className="input">
              {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Número de empleados" error={errors.size_org?.message}>
            <input {...register("size_org")} type="number" min="1" className="input" placeholder="250" />
          </Field>
          <Field label="Años de operación" error={errors.years_operating?.message}>
            <input {...register("years_operating")} type="number" min="0" className="input" placeholder="12" />
          </Field>
        </div>
      </Section>

      {/* ── Contacto ── */}
      <Section title="👤 Contacto principal">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
          <Field label="Nombre completo" error={errors.contact_name?.message}>
            <input {...register("contact_name")} className="input" placeholder="Juan Pérez" />
          </Field>
          <Field label="Cargo" error={errors.contact_role?.message}>
            <input {...register("contact_role")} className="input" placeholder="Gerente de Operaciones" />
          </Field>
          <Field label="Correo electrónico" error={errors.contact_email?.message}>
            <input {...register("contact_email")} type="email" className="input" placeholder="juan@empresa.co" />
          </Field>
          <Field label="Teléfono / WhatsApp" error={errors.contact_phone?.message}>
            <input {...register("contact_phone")} className="input" placeholder="+57 300 123 4567" />
          </Field>
        </div>
      </Section>

      {/* ── El problema ── */}
      <Section title="🔍 El problema a diagnosticar">
        <div style={{ display: "grid", gap: "14px" }}>
          <Field label="Área o proceso a diagnosticar" error={errors.area?.message} full>
            <select {...register("area")} className="input">
              <option value="">Seleccionar...</option>
              {AREAS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </Field>
          <Field label="¿Cuál es el síntoma o problema principal que reporta el cliente?" error={errors.symptom?.message} full>
            <textarea
              {...register("symptom")}
              rows={3}
              className="input"
              style={{ resize: "vertical" }}
              placeholder="Ej: Los pedidos están llegando tarde, hay alta rotación en el área de producción, los costos operativos subieron un 30%..."
            />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
            <Field label="¿Hace cuánto viene el problema?" error={errors.problem_since?.message}>
              <input {...register("problem_since")} className="input" placeholder="Ej: 6 meses, 2 años" />
            </Field>
            <Field label="¿Cuántas áreas o sedes involucra?" error={errors.areas_count?.message}>
              <input {...register("areas_count")} type="number" min="1" className="input" placeholder="1" />
            </Field>
          </div>
          <Field label="¿Qué han intentado antes para resolverlo? (opcional)" error={errors.previous_attempts?.message} full>
            <textarea
              {...register("previous_attempts")}
              rows={2}
              className="input"
              style={{ resize: "vertical" }}
              placeholder="Ej: Contratamos una consultoría en 2023, cambiamos el software ERP..."
            />
          </Field>
          <Field label="¿Qué espera obtener con este diagnóstico?" error={errors.expected_outcome?.message} full>
            <textarea
              {...register("expected_outcome")}
              rows={2}
              className="input"
              style={{ resize: "vertical" }}
              placeholder="Ej: Identificar las causas raíz, tener un plan de acción claro, reducir costos en un 15%..."
            />
          </Field>
        </div>
      </Section>

      {/* ── Alcance ── */}
      <Section title="📐 Alcance del diagnóstico">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
          <Field label="Personas que participarán en la encuesta" error={errors.survey_participants?.message}>
            <input {...register("survey_participants")} type="number" min="1" className="input" placeholder="45" />
          </Field>
          <Field label="Fecha límite para el reporte (opcional)" error={errors.deadline?.message}>
            <input {...register("deadline")} type="date" className="input" />
          </Field>
          <Field label="Nivel de confidencialidad" error={errors.confidentiality?.message} full>
            <select {...register("confidentiality")} className="input">
              <option value="Confidencial - Uso Estratégico">Confidencial — Uso Estratégico</option>
              <option value="Restringido - Solo Dirección">Restringido — Solo Dirección</option>
              <option value="Interno">Interno</option>
            </select>
          </Field>
        </div>
      </Section>

      <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "8px" }}>
        <button type="submit" className="btn-primary" style={{ padding: "0 24px", height: "38px" }}>
          Siguiente →
        </button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "28px" }}>
      <p style={{
        margin: "0 0 14px", fontSize: "11px", fontWeight: 500,
        color: "#171717", fontFamily: "IBM Plex Mono, monospace",
        paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)",
        letterSpacing: "0.04em",
      }}>{title}</p>
      {children}
    </div>
  );
}

function Field({
  label, error, children, full,
}: {
  label: string; error?: string; children: React.ReactNode; full?: boolean;
}) {
  return (
    <div className={full ? "col-span-2" : ""} style={{ minWidth: 0 }}>
      <label style={{
        display: "block", marginBottom: "6px",
        fontSize: "11px", color: "#706f69",
        fontFamily: "IBM Plex Mono, monospace",
      }}>{label}</label>
      {children}
      {error && <span style={{ fontSize: "10px", color: "#8b3a3a", marginTop: "4px", display: "block", fontFamily: "IBM Plex Mono, monospace" }}>{error}</span>}
    </div>
  );
}
