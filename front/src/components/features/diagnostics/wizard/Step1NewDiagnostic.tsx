"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Building2, User, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { AREAS } from "@/config/pipeline-presets";
import type { ClientData } from "@/lib/types";
import { coherentText } from "@/lib/utils/validation";

// Only validate the fields that change per-diagnostic
const schema = z.object({
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

type ProblemFields = Pick<
  ClientData,
  | "area" | "symptom" | "problem_since" | "previous_attempts"
  | "expected_outcome" | "areas_count" | "survey_participants"
  | "deadline" | "confidentiality"
>;

export function Step1NewDiagnostic({
  client,
  onChange,
  onNext,
}: {
  client: ClientData;
  onChange: (d: ClientData) => void;
  onNext: () => void;
}) {
  const [showClientDetail, setShowClientDetail] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<ProblemFields>({
    resolver: zodResolver(schema),
    defaultValues: {
      area:                client.area,
      symptom:             client.symptom,
      problem_since:       client.problem_since,
      previous_attempts:   client.previous_attempts,
      expected_outcome:    client.expected_outcome,
      areas_count:         client.areas_count || "1",
      survey_participants: client.survey_participants,
      deadline:            client.deadline,
      confidentiality:     client.confidentiality,
    },
  });

  function onSubmit(values: ProblemFields) {
    onChange({ ...client, ...values });
    onNext();
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-gray-900">Nuevo diagnóstico</h2>
        <p className="text-sm text-gray-500 mt-1">
          Los datos del cliente ya están guardados. Solo describe el nuevo problema.
        </p>
      </div>

      {/* ── Client banner ── */}
      <div className="bg-brand-50 border border-brand-200 rounded-xl overflow-hidden">
        <button
          type="button"
          onClick={() => setShowClientDetail(v => !v)}
          className="w-full flex items-center justify-between px-4 py-3 text-left"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center shrink-0">
              <Building2 size={16} className="text-white" />
            </div>
            <div>
              <p className="font-semibold text-brand-900 text-sm">
                {client.organization_name || "Cliente"}
              </p>
              <p className="text-xs text-brand-600">
                {[client.sector, client.city, client.size_org ? `${client.size_org} empleados` : ""]
                  .filter(Boolean).join(" · ") || client.legal_name}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-brand-500">
            <span className="text-xs font-medium">
              {showClientDetail ? "Ocultar" : "Ver datos"}
            </span>
            {showClientDetail
              ? <ChevronUp size={14} />
              : <ChevronDown size={14} />
            }
          </div>
        </button>

        {showClientDetail && (
          <div className="border-t border-brand-200 px-4 py-3 grid grid-cols-2 gap-x-6 gap-y-2 bg-white">
            {[
              ["Razón social",  client.legal_name],
              ["NIT",           client.nit],
              ["Sector",        client.sector],
              ["Ciudad",        client.city],
              ["Empleados",     client.size_org],
              ["Años operando", client.years_operating],
            ].map(([label, value]) => value ? (
              <div key={label}>
                <p className="text-xs text-gray-400">{label}</p>
                <p className="text-sm font-medium text-gray-800">{value}</p>
              </div>
            ) : null)}

            {(client.contact_name || client.contact_email) && (
              <div className="col-span-2 pt-2 border-t border-gray-100 flex items-center gap-2">
                <User size={13} className="text-gray-400" />
                <span className="text-xs text-gray-600">
                  {[client.contact_name, client.contact_role, client.contact_email]
                    .filter(Boolean).join(" · ")}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── New problem ── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
          🔍 El nuevo problema a diagnosticar
        </p>

        <Field label="Área o proceso a diagnosticar" error={errors.area?.message} full>
          <select {...register("area")} className="input">
            <option value="">Seleccionar...</option>
            {AREAS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </Field>

        <Field label="¿Cuál es el síntoma o problema principal?" error={errors.symptom?.message} full>
          <textarea
            {...register("symptom")}
            rows={3}
            className="input resize-none"
            placeholder="Ej: Los costos operativos subieron un 30%, hay alta rotación en producción..."
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
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
            className="input resize-none"
            placeholder="Ej: Contratamos una consultoría en 2023..."
          />
        </Field>

        <Field label="¿Qué espera obtener con este diagnóstico?" error={errors.expected_outcome?.message} full>
          <textarea
            {...register("expected_outcome")}
            rows={2}
            className="input resize-none"
            placeholder="Ej: Identificar causas raíz, reducir costos en un 15%..."
          />
        </Field>
      </div>

      {/* ── Scope ── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
          📐 Alcance
        </p>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Personas en la encuesta" error={errors.survey_participants?.message}>
            <input {...register("survey_participants")} type="number" min="1" className="input" placeholder="45" />
          </Field>
          <Field label="Fecha límite (opcional)" error={errors.deadline?.message}>
            <input {...register("deadline")} type="date" className="input" />
          </Field>
          <Field label="Confidencialidad" error={errors.confidentiality?.message} full>
            <select {...register("confidentiality")} className="input">
              <option value="Confidencial - Uso Estratégico">Confidencial — Uso Estratégico</option>
              <option value="Restringido - Solo Dirección">Restringido — Solo Dirección</option>
              <option value="Interno">Interno</option>
            </select>
          </Field>
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary px-8">
          Siguiente →
        </button>
      </div>
    </form>
  );
}

function Field({
  label, error, children, full,
}: {
  label: string; error?: string; children: React.ReactNode; full?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-1 ${full ? "col-span-2" : ""}`}>
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}
