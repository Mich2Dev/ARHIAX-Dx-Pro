"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Spinner } from "@/components/ui/Spinner";
import type { DiagnosticFormData } from "@/lib/types";

// Human-readable names and descriptions in Spanish
const TOOL_LABELS: Record<string, { label: string; desc: string }> = {
  g01_receptor:      { label: "Recepción del mandato",         desc: "Recibe la solicitud, captura el contexto organizacional e inicia la sesión gobernada." },
  g02_configurador:  { label: "Configuración del dominio",     desc: "Define benchmarks, KPIs y marcos de referencia para el diagnóstico." },
  g03_cienciometro:  { label: "Revisión de literatura",        desc: "Mapea evidencia académica relevante para el cuello de botella diagnosticado." },
  academic_search:   { label: "Búsqueda académica",            desc: "Consulta bases de datos académicas para evidencia de soporte." },
  web_search:        { label: "Búsqueda web sectorial",        desc: "Enriquece el contexto con fuentes web del sector." },
  g04_cartografo:    { label: "Mapa de procesos",              desc: "Construye el mapa de procesos y capacidades organizacionales." },
  g05_brechas:       { label: "Análisis de brechas",           desc: "Identifica brechas baseline e hipótesis diagnósticas." },
  g06_bpmn_architect:{ label: "Arquitectura BPMN (AS-IS)",     desc: "Produce la arquitectura del proceso actual en notación BPMN." },
  g07_cuellos:       { label: "Cuantificación de cuellos",     desc: "Cuantifica los cuellos de botella y el impacto en pérdida de oportunidad." },
  g08_optimizador:   { label: "Opciones de mejora (TO-BE)",    desc: "Diseña alternativas de mejora y escenarios de ROI." },
  bpmn_generator:    { label: "Generador de diagramas BPMN",   desc: "Renderiza los diagramas BPMN del proceso." },
  g09a_preguntas:    { label: "Banco de preguntas",            desc: "Genera las preguntas de la encuesta por rol." },
  g09b_ramificacion: { label: "Lógica de ramificación",        desc: "Define el flujo adaptativo de la encuesta según respuestas." },
  g09c_validacion:   { label: "Validación de encuesta",        desc: "Verifica completitud e integridad de las respuestas." },
  g10a_scoring:      { label: "Matrices de scoring",           desc: "Construye matrices de puntuación por rol y dimensión." },
  g10b_psicometria:  { label: "Análisis psicométrico",         desc: "Calcula confiabilidad, alpha de Cronbach y consistencia estadística." },
  g11a_bayesiano:    { label: "Análisis Bayesiano",            desc: "Analiza hipótesis de cuellos de botella y brechas de percepción." },
  g11b_nlp:          { label: "Análisis de texto libre (NLP)", desc: "Sintetiza comentarios cualitativos de los encuestados." },
  irr_calculator:    { label: "Confiabilidad inter-evaluador", desc: "Calcula el IRR y señales de calidad para el diagnóstico." },
  scoring_engine:    { label: "Motor de normalización",        desc: "Normaliza y agrega los datos de scoring." },
  g12_hallazgos:     { label: "Consolidación de hallazgos",    desc: "Consolida los hallazgos confirmados y recomendaciones priorizadas." },
  g13_redactor:      { label: "Redacción ejecutiva",           desc: "Redacta la narrativa ejecutiva del diagnóstico para revisión humana." },
  g14_qa_control:    { label: "Control de calidad (QA)",       desc: "Verifica calidad y gobernanza antes de generar el documento final." },
  docx_generator:    { label: "Generación del reporte Word",   desc: "Genera el reporte ejecutivo en formato Word tras aprobación QA." },
};

const PHASE_GROUPS: { phase: string; label: string; icon: string }[] = [
  { phase: "intake",         label: "1. Recepción",           icon: "📥" },
  { phase: "research",       label: "2. Investigación",       icon: "🔬" },
  { phase: "mapping",        label: "3. Mapeo organizacional",icon: "🗺️" },
  { phase: "design",         label: "4. Diseño de procesos",  icon: "⚙️" },
  { phase: "quantification", label: "5. Cuantificación",      icon: "📊" },
  { phase: "survey_design",  label: "6. Diseño de encuesta",  icon: "📋" },
  { phase: "analysis",       label: "7. Análisis",            icon: "🧠" },
  { phase: "synthesis",      label: "8. Síntesis",            icon: "🔗" },
  { phase: "reporting",      label: "9. Redacción",           icon: "✍️" },
  { phase: "qa",             label: "10. Control de calidad", icon: "✅" },
  { phase: "rendering",      label: "11. Generación final",   icon: "📄" },
];

export function Step2Pipeline({
  data,
  onChange,
  onNext,
  onBack,
}: {
  data: DiagnosticFormData;
  onChange: (p: Partial<DiagnosticFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const t = useTranslations("form");

  const { data: catalog, isLoading } = useQuery({
    queryKey: ["tool-catalog"],
    queryFn: async () => {
      const govUrl = process.env.NEXT_PUBLIC_GOVERNANCE_URL ?? "http://localhost:8088";
      const res = await fetch(`${govUrl}/v1/compliance/posture`);
      const json = await res.json();
      return json.tool_manifest as any[];
    },
  });

  function toggleTool(name: string) {
    const current = data.requested_tools;
    const next = current.includes(name)
      ? current.filter((t) => t !== name)
      : [...current, name];
    onChange({ requested_tools: next });
  }

  function selectAll() {
    const all = (catalog ?? []).map((t: any) => t.name);
    onChange({ requested_tools: all });
  }

  function selectDefault() {
    const defaults = (catalog ?? []).filter((t: any) => t.default_pipeline).map((t: any) => t.name);
    onChange({ requested_tools: defaults });
  }

  const canContinue = data.requested_tools.length > 0;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">{t("step2")}</h2>
        <p className="text-sm text-gray-500 mt-1">
          Selecciona los módulos que ejecutará el agente. Los marcados en verde son el pipeline estándar recomendado.
        </p>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2">
        <button onClick={selectDefault} type="button"
          className="text-xs px-3 py-1.5 rounded-lg border border-brand-500 text-brand-600 hover:bg-brand-50 transition-colors font-medium">
          Pipeline estándar
        </button>
        <button onClick={selectAll} type="button"
          className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors font-medium">
          Seleccionar todo
        </button>
        <span className="ml-auto text-xs text-gray-400 self-center">
          {data.requested_tools.length} módulos seleccionados
        </span>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : (
        <div className="space-y-4 max-h-[400px] overflow-y-auto pr-1">
          {PHASE_GROUPS.map(({ phase, label, icon }) => {
            const tools = (catalog ?? []).filter((t: any) => t.phase === phase);
            if (!tools.length) return null;
            return (
              <div key={phase}>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span>{icon}</span> {label}
                </p>
                <div className="space-y-1.5">
                  {tools.map((tool: any) => {
                    const selected = data.requested_tools.includes(tool.name);
                    const info = TOOL_LABELS[tool.name];
                    return (
                      <label
                        key={tool.name}
                        className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                          selected
                            ? "border-brand-400 bg-brand-50 shadow-sm"
                            : "border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => toggleTool(tool.name)}
                          className="mt-0.5 w-4 h-4 accent-brand-500 shrink-0"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-gray-800">
                              {info?.label ?? tool.name}
                            </span>
                            {tool.default_pipeline && (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand-100 text-brand-700">
                                ESTÁNDAR
                              </span>
                            )}
                            {tool.severity === "CRITICAL" && (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                                CRÍTICO
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                            {info?.desc ?? tool.description}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Processing profile */}
      <div className="border-t border-gray-100 pt-4 space-y-2">
        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Opciones de entrega</p>
        <label className="flex items-center gap-3 text-sm text-gray-700 cursor-pointer p-2 rounded-lg hover:bg-gray-50">
          <input
            type="checkbox"
            checked={data.processing_profile.publish_report}
            onChange={(e) =>
              onChange({ processing_profile: { ...data.processing_profile, publish_report: e.target.checked } })
            }
            className="w-4 h-4 accent-brand-500"
          />
          <div>
            <span className="font-medium">Publicar reporte final</span>
            <span className="text-gray-400 text-xs ml-2">(requiere aprobación humana)</span>
          </div>
        </label>
        <label className="flex items-center gap-3 text-sm text-gray-700 cursor-pointer p-2 rounded-lg hover:bg-gray-50">
          <input
            type="checkbox"
            checked={data.processing_profile.issue_certificate}
            onChange={(e) =>
              onChange({ processing_profile: { ...data.processing_profile, issue_certificate: e.target.checked } })
            }
            className="w-4 h-4 accent-brand-500"
          />
          <div>
            <span className="font-medium">Emitir certificado de gobernanza</span>
            <span className="text-gray-400 text-xs ml-2">(firmado digitalmente)</span>
          </div>
        </label>
      </div>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-secondary">{t("back")}</button>
        <button type="button" onClick={onNext} disabled={!canContinue}
          className="btn-primary disabled:opacity-40">
          {t("next")}
        </button>
      </div>
    </div>
  );
}
