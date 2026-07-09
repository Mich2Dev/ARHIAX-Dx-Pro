"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { apiPro } from "@/lib/api-pro";
import { Spinner } from "@/components/ui/Spinner";
import { CheckCircle, ShieldCheck, Cpu, Loader2, Check, ChevronRight } from "lucide-react";

interface Question {
  id: string;
  dimension: string;
  text: string;
  type: "likert_5" | "open_text" | "multiple_choice";
  roles: string[];
  rationale?: string;
  hypothesis_tested?: string;
  expected_direction?: string;
}

// ── Robust question parser ────────────────────────────────────────────────────
function parseQuestions(questionsData: any): Question[] {
  if (!questionsData) return [];

  let data = questionsData;

  // If Gemini returned raw_output (truncated/unparsed JSON), try to parse it
  if (data.raw_output) {
    try {
      data = JSON.parse(data.raw_output);
    } catch {
      const match = data.raw_output.match(/\{[\s\S]*\}/);
      if (match) {
        try { data = JSON.parse(match[0]); } catch { return []; }
      } else {
        return [];
      }
    }
  }

  let questions: any[] = [];
  if (Array.isArray(data)) {
    questions = data;
  } else if (data.questions && Array.isArray(data.questions)) {
    questions = data.questions;
  } else {
    return [];
  }

  return questions.map((q: any, i: number) => ({
    id: q.id ?? `Q${i + 1}`,
    dimension: q.dimension ?? q.dim ?? "General",
    text: q.text ?? q.texto ?? q.question ?? q.pregunta ?? `Pregunta ${i + 1}`,
    type: normalizeType(q.type ?? q.tipo ?? q.escala ?? "likert_5"),
    roles: normalizeRoles(q.roles ?? q.rol_target ?? q.role ?? "all"),
    rationale: q.rationale ?? q.razon ?? undefined,
    hypothesis_tested: q.hypothesis_tested ?? q.hipotesis ?? undefined,
    expected_direction: q.expected_direction ?? undefined,
  }));
}

function normalizeType(t: string): "likert_5" | "open_text" | "multiple_choice" {
  const s = String(t).toLowerCase();
  if (s.includes("open") || s.includes("text") || s.includes("abierta") || s.includes("libre")) return "open_text";
  if (s.includes("multiple") || s.includes("choice")) return "multiple_choice";
  return "likert_5";
}

function normalizeRoles(r: any): string[] {
  if (Array.isArray(r)) return r;
  const s = String(r).toLowerCase();
  if (s === "all" || s === "todos" || s === "all roles" || s === "all_roles") {
    return ["Estratégico", "Táctico", "Operativo"];
  }
  if (s.includes(",")) return s.split(",").map((x: string) => x.trim());
  if (s.includes("estrat")) return ["Estratégico"];
  if (s.includes("tact") || s.includes("táct")) return ["Táctico"];
  if (s.includes("operat")) return ["Operativo"];
  return ["Estratégico", "Táctico", "Operativo"];
}

function getQuestionsForRole(questions: Question[], branching: any, role: string): Question[] {
  // Try branching role_tracks first
  if (branching?.role_tracks?.[role]) {
    const track = branching.role_tracks[role];
    let ids: string[] = [];
    if (Array.isArray(track.question_ids)) {
      ids = track.question_ids;
    } else if (typeof track.question_ids === "string") {
      ids = track.question_ids.split(/[\s,]+/).filter(Boolean);
    }
    if (ids.length > 0) {
      const qMap = new Map(questions.map(q => [q.id, q]));
      const result = ids.map(id => qMap.get(id)).filter(Boolean) as Question[];
      if (result.length > 0) return result;
    }
  }
  // Fallback: filter by roles field
  const filtered = questions.filter(q => q.roles.includes(role));
  // If still nothing, return all questions (better than blank)
  return filtered.length > 0 ? filtered : questions;
}

export function SurveyForm({ token, variant = "standard" }: { token: string; variant?: "standard" | "pro" }) {
  const client = variant === "pro" ? apiPro : api;
  const surveyBase = variant === "pro" ? "/pro/survey" : "/survey";
  const [step, setStep] = useState<"role" | "questions" | "completed">("role");
  const [role, setRole] = useState<string>("");
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [openAnswers, setOpenAnswers] = useState<Record<string, string>>({});

  const { data: survey, isLoading, error } = useQuery({
    queryKey: ["survey", token],
    queryFn: () => client.get(`${surveyBase}/${token}`).then((r) => r.data),
    retry: false,
  });

  const [submitError, setSubmitError] = useState<string | null>(null);

  const ROLE_LABELS: Record<string, string> = {
    executive:   "Estratégico",
    operations:  "Operativo",
    technology:  "Táctico",
    strategy:    "Planeación",
    finance:     "Finanzas",
    hr:          "Recursos humanos",
    "Estratégico": "Estratégico",
    "Táctico":    "Táctico",
    "Operativo":  "Operativo",
    "Planeación": "Planeación",
  };

  const normalizeRole = (r: string) => ROLE_LABELS[r] ?? r;

  const submitMutation = useMutation({
    mutationFn: (payload: any) =>
      client.post(`${surveyBase}/${token}/submit`, payload).then((r) => r.data),
    onSuccess: () => { setSubmitError(null); setStep("completed"); },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? err?.message ?? "Error al enviar. Intenta de nuevo.";
      setSubmitError(String(detail));
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f4f1ea]">
        <Loader2 className="w-8 h-8 text-[#171717] animate-spin" />
      </div>
    );
  }

  if (error || !survey) {
    const errMsg = (error as Error)?.message || "";
    const isUnavailable = errMsg.includes("503") || errMsg.includes("no está disponible") || errMsg.includes("no se generó");
    return (
      <div className="min-h-screen bg-[#f4f1ea] p-4 flex items-center justify-center">
        <div className="bg-white border border-[#171717]/10 shadow-sm max-w-2xl w-full overflow-hidden">
          <div className="p-12 text-center">
            <h1 className="text-2xl font-serif text-[#171717] mb-4" style={{ fontFamily: "Cormorant Garamond, serif" }}>
              {isUnavailable ? "Encuesta no disponible" : "Encuesta no encontrada"}
            </h1>
            <p className="text-sm text-[#706f69] font-mono" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
              {isUnavailable
                ? "El instrumento aún no está listo o el caso falló en arquitectura. Pida al consultor un enlace nuevo."
                : "Esta encuesta no existe o ha sido cerrada por el consultor."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const ROLE_CATALOG: Record<string, { label: string; description: string }> = {
    executive:  { label: "Estratégico", description: "Alta dirección y gobernanza" },
    operations: { label: "Operativo", description: "Ejecución y procesos en planta" },
    technology: { label: "Táctico", description: "Gestión, coordinación y sistemas" },
    strategy:   { label: "Planeación", description: "Área de estrategia y planeación (rol funcional)" },
    finance:    { label: "Finanzas", description: "Perspectiva del área financiera" },
    hr:         { label: "Recursos humanos", description: "Perspectiva de talento y cultura" },
  };

  const ROLE_DESCRIPTIONS: Record<string, string> = {
    "Estratégico": "Alta dirección y gobernanza",
    "Operativo": "Ejecución y procesos en planta",
    "Táctico": "Gestión, coordinación y sistemas",
    "Planeación": "Área de estrategia y planeación (rol funcional)",
    "Finanzas": "Perspectiva del área financiera",
    "Recursos humanos": "Perspectiva de talento y cultura",
  };

  function normalizeRoleOption(raw: string): { id: string; label: string; description: string } {
    const key = String(raw || "").trim().toLowerCase();
    if (ROLE_CATALOG[key]) {
      return { id: key, ...ROLE_CATALOG[key] };
    }
    const label = ROLE_DESCRIPTIONS[raw] ? raw : raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return {
      id: raw,
      label,
      description: ROLE_DESCRIPTIONS[label] ?? ROLE_DESCRIPTIONS[raw] ?? "Perspectiva definida para este diagnóstico",
    };
  }

  const rawRoles: string[] =
    (survey.available_roles?.length ? survey.available_roles : null) ??
    (survey.roles?.length ? survey.roles : null) ??
    ["Estratégico", "Táctico", "Operativo"];

  const roleOptions: { id: string; label: string; description: string }[] = (() => {
    const sources: string[] = survey.role_options?.length
      ? survey.role_options.map((o: { id?: string; label?: string }) => o.id ?? o.label ?? "")
      : rawRoles;
    const seen = new Set<string>();
    return sources.map(normalizeRoleOption).filter((o) => {
      if (seen.has(o.label)) return false;
      seen.add(o.label);
      return true;
    });
  })();

  const availableRoles: string[] = roleOptions.map((o) => o.label);

  const allQuestions = parseQuestions(survey.questions);
  const questionsForRole = role
    ? getQuestionsForRole(allQuestions, survey.branching, role)
    : [];

  const currentQuestion = questionsForRole[currentQ];
  const progress = questionsForRole.length > 0
    ? ((currentQ + 1) / questionsForRole.length) * 100
    : 0;

  // ── Step 1: Role Selection ────────────────────────────────────────────────
  if (step === "role") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f4f1ea] p-4">
        <div className="bg-white border border-[#171717]/12 shadow-sm overflow-hidden max-w-xl w-full">
          {/* Governance Banner */}
          {survey.is_pro && (
            <div className="bg-[#171717] px-6 py-2.5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu size={12} className="text-[#f4f1ea]/60" />
                <span className="text-[10px] font-medium text-[#f4f1ea]/80 tracking-[0.1em] uppercase font-mono" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                  Certificado de Gobernanza G09c
                </span>
              </div>
              <div className="flex items-center gap-1.5 bg-[#56624b] px-2 py-0.5">
                <ShieldCheck size={10} className="text-[#f4f1ea]" />
                <span className="text-[9px] font-bold text-[#f4f1ea] font-mono" style={{ fontFamily: "IBM Plex Mono, monospace" }}>TRUSTED</span>
              </div>
            </div>
          )}

          <div className="p-10">
            <div className="text-center mb-10">
              <p className="text-[11px] font-medium text-[#56624b] tracking-[0.2em] uppercase font-mono mb-2" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                § Diagnóstico Organizacional
              </p>
              <h1 className="text-4xl font-medium text-[#171717] leading-tight mb-3" style={{ fontFamily: "Cormorant Garamond, serif" }}>
                {survey.organization_name}
              </h1>
              <div className="h-px w-12 bg-[#171717]/20 mx-auto"></div>
            </div>

            <div className="bg-[#f4f1ea]/50 border border-[#171717]/5 p-6 mb-8">
              <p className="text-[13px] text-[#171717] leading-relaxed mb-4">
                Estamos realizando un diagnóstico profundo de madurez organizacional. 
                Sus respuestas son tratadas mediante un ciclo de anonimización gobernada y serán procesadas por modelos de síntesis bayesiana.
              </p>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#706f69]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>TIEMPO:</span>
                  <span className="text-[11px] font-mono text-[#171717] font-bold" style={{ fontFamily: "IBM Plex Mono, monospace" }}>{survey.estimated_minutes} MIN</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#706f69]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>PRIVACIDAD:</span>
                  <span className="text-[11px] font-mono text-[#56624b] font-bold" style={{ fontFamily: "IBM Plex Mono, monospace" }}>ANÓNIMO</span>
                </div>
              </div>
            </div>

            <div className="space-y-2 mb-10">
              <p className="text-[11px] font-bold text-[#171717] uppercase tracking-wider mb-4 font-mono" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                Seleccione su perspectiva:
              </p>
              {roleOptions.map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => setRole(opt.label)}
                  className={`w-full text-left p-5 transition-all border ${
                    role === opt.label
                      ? "border-[#171717] bg-[#171717]/5"
                      : "border-[#171717]/10 hover:border-[#171717]/30 bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className={`text-sm font-bold ${role === opt.label ? "text-[#171717]" : "text-[#706f69]"}`}>{opt.label.toUpperCase()}</p>
                      <p className="text-[11px] text-[#706f69] mt-1 italic">{opt.description}</p>
                    </div>
                    <div className={`w-4 h-4 border ${role === opt.label ? "bg-[#171717] border-[#171717]" : "border-[#171717]/20"}`}>
                      {role === opt.label && <Check size={12} className="text-white" />}
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={() => setStep("questions")}
              disabled={!role}
              className="w-full bg-[#171717] text-[#f4f1ea] py-4 text-xs font-bold tracking-[0.2em] uppercase font-mono disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:bg-[#222522]"
              style={{ fontFamily: "IBM Plex Mono, monospace" }}
            >
              {role ? "Iniciar Diagnóstico" : "Seleccione su rol"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Step 2: Questions ──────────────────────────────────────────────────────
  if (step === "questions") {
    if (questionsForRole.length === 0) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#f4f1ea] p-4">
          <div className="bg-white border border-[#171717]/12 shadow-sm p-12 max-w-md text-center">
            <h1 className="text-xl font-serif text-[#171717] mb-4" style={{ fontFamily: "Cormorant Garamond, serif" }}>Sin preguntas disponibles</h1>
            <p className="text-sm text-[#706f69] mb-8">
              No hay ítems configurados para el rol seleccionado.
            </p>
            <button onClick={() => setStep("role")} className="text-[11px] font-mono text-[#56624b] uppercase tracking-wider font-bold">
              ← Volver al inicio
            </button>
          </div>
        </div>
      );
    }

    if (!currentQuestion) {
      submitMutation.mutate({ role, answers, open_answers: openAnswers });
      return <div className="min-h-screen flex items-center justify-center bg-[#f4f1ea]"><Loader2 className="w-8 h-8 text-[#171717] animate-spin" /></div>;
    }

    const handleNext = () => {
      if (currentQ < questionsForRole.length - 1) {
        setCurrentQ(currentQ + 1);
      } else {
        setSubmitError(null);
        submitMutation.mutate({
          role: normalizeRole(role),
          answers,
          open_answers: openAnswers,
        });
      }
    };

    const isAnswered = currentQuestion.type === "open_text"
      ? !!openAnswers[currentQuestion.id]?.trim()
      : answers[currentQuestion.id] !== undefined;

    return (
      <div className="min-h-screen bg-[#f4f1ea] py-12 px-4 flex flex-col items-center">
        <div className="max-w-2xl w-full">
          {/* Header Progress */}
          <div className="mb-8 flex items-end justify-between border-b border-[#171717]/10 pb-4">
            <div>
              <p className="text-[10px] font-mono text-[#56624b] tracking-[0.2em] uppercase font-bold mb-1" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                ITEM {currentQ + 1} / {questionsForRole.length}
              </p>
              <h3 className="text-sm font-bold text-[#171717] uppercase tracking-wider font-mono" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                {currentQuestion.dimension}
              </h3>
            </div>
            <p className="text-[11px] font-mono text-[#706f69]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
              PROGRESO: {Math.round(progress)}%
            </p>
          </div>

          <div className="bg-white border border-[#171717]/12 p-12 shadow-sm mb-6 min-h-[400px] flex flex-col">
            <div className="flex-1">
              {(currentQuestion.hypothesis_tested || currentQuestion.rationale) && (
                <div className="mb-6 p-4 bg-[#f4f1ea]/80 border border-[#171717]/8">
                  {currentQuestion.hypothesis_tested && (
                    <p className="text-[10px] font-mono text-[#56624b] uppercase tracking-wider mb-1" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                      Hipótesis: {currentQuestion.hypothesis_tested}
                    </p>
                  )}
                  {currentQuestion.rationale && (
                    <p className="text-[12px] text-[#706f69] leading-relaxed m-0" style={{ fontFamily: "Manrope, sans-serif" }}>
                      {currentQuestion.rationale}
                    </p>
                  )}
                </div>
              )}
              <h2 className="text-3xl font-medium text-[#171717] leading-tight mb-12" style={{ fontFamily: "Cormorant Garamond, serif" }}>
                {currentQuestion.text}
              </h2>

              {currentQuestion.type === "likert_5" && (
                <div className="space-y-2">
                  {[
                    { value: 1, label: "Totalmente en desacuerdo" },
                    { value: 2, label: "En desacuerdo" },
                    { value: 3, label: "Neutral / No sabe" },
                    { value: 4, label: "De acuerdo" },
                    { value: 5, label: "Totalmente de acuerdo" },
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setAnswers({ ...answers, [currentQuestion.id]: option.value })}
                      className={`w-full text-left p-5 border transition-all ${
                        answers[currentQuestion.id] === option.value
                          ? "border-[#171717] bg-[#171717]/5"
                          : "border-[#171717]/10 hover:border-[#171717]/30"
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 border flex items-center justify-center text-[11px] font-bold font-mono transition-all ${
                          answers[currentQuestion.id] === option.value
                            ? "bg-[#171717] text-white border-[#171717]" : "border-[#171717]/20 text-[#706f69]"
                        }`} style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                          {option.value}
                        </div>
                        <span className="text-sm font-medium text-[#171717]">{option.label}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {currentQuestion.type === "open_text" && (
                <textarea
                  value={openAnswers[currentQuestion.id] || ""}
                  onChange={(e) => setOpenAnswers({ ...openAnswers, [currentQuestion.id]: e.target.value })}
                  placeholder="Por favor, detalle su respuesta..."
                  className="w-full h-48 p-6 border border-[#171717]/10 bg-[#f4f1ea]/30 focus:border-[#171717]/30 focus:outline-none resize-none text-sm leading-relaxed"
                />
              )}
            </div>

            <div className="flex gap-4 mt-12 pt-8 border-t border-[#171717]/5 flex-col">
              {submitError && (
                <div className="p-3 border-l-2 border-[#8b3a3a] bg-[#8b3a3a]/5 text-[12px] text-[#8b3a3a]">
                  {submitError}
                </div>
              )}
              <div className="flex gap-4">
              <button
                onClick={() => currentQ > 0 ? setCurrentQ(currentQ - 1) : setStep("role")}
                className="px-8 py-4 border border-[#171717]/20 text-[11px] font-bold text-[#706f69] uppercase tracking-widest font-mono hover:border-[#171717] hover:text-[#171717] transition-all"
                style={{ fontFamily: "IBM Plex Mono, monospace" }}
              >
                Anterior
              </button>
              <button
                onClick={handleNext}
                disabled={!isAnswered || submitMutation.isPending}
                className="flex-1 bg-[#171717] text-[#f4f1ea] py-4 text-[11px] font-bold tracking-[0.2em] uppercase font-mono disabled:opacity-20 transition-all hover:bg-[#222522] flex items-center justify-center gap-3"
                style={{ fontFamily: "IBM Plex Mono, monospace" }}
              >
                {submitMutation.isPending ? (
                  "Procesando..."
                ) : currentQ === questionsForRole.length - 1 ? (
                  "Finalizar y Enviar"
                ) : (
                  "Siguiente \u00cdtem \u2192"
                )}
              </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Step 3: Completed ──────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f4f1ea] p-4">
      <div className="bg-white border border-[#171717]/12 shadow-sm p-16 max-w-xl w-full text-center">
        <div className="w-16 h-16 border border-[#56624b] flex items-center justify-center mx-auto mb-8">
          <Check size={32} className="text-[#56624b]" />
        </div>
        <h1 className="text-4xl font-medium text-[#171717] mb-6" style={{ fontFamily: "Cormorant Garamond, serif" }}>
          Diagnóstico Finalizado
        </h1>
        <div className="h-px w-12 bg-[#171717]/20 mx-auto mb-8"></div>
        <p className="text-sm text-[#706f69] leading-relaxed mb-10">
          Su contribución ha sido integrada exitosamente en el ciclo de diagnóstico. 
          Los datos han sido anonimizados según el protocolo de gobernanza activa.
        </p>
        <p className="text-[10px] text-[#706f69] font-mono uppercase tracking-[0.2em]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
          Puede cerrar esta ventana de forma segura.
        </p>
      </div>
    </div>
  );
}
