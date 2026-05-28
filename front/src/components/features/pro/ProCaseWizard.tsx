"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { apiPro } from "@/lib/api-pro";
import { ProStep1Client, defaultClient } from "./wizard/ProStep1Client";
import { ProStep2Scope, defaultScope } from "./wizard/ProStep2Scope";
import { ProStep3Review, defaultConsent } from "./wizard/ProStep3Review";
import type { ProClientData } from "./wizard/ProStep1Client";
import type { ProScopeData } from "./wizard/ProStep2Scope";
import type { ProConsentData } from "./wizard/ProStep3Review";

const DRAFT_KEY = "dxpro_wizard_draft";

function loadDraft(): { client: ProClientData; scope: ProScopeData; step: number } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveDraft(client: ProClientData, scope: ProScopeData, step: number) {
  if (typeof window === "undefined") return;
  localStorage.setItem(DRAFT_KEY, JSON.stringify({ client, scope, step }));
}

function clearDraft() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(DRAFT_KEY);
}

// ── pasos ─────────────────────────────────────────────────────────────────────
const STEPS = [
  { n: 1, label: "Perfil" },
  { n: 2, label: "Arquitectura" },
  { n: 3, label: "Validación" },
];

// ── validación paso 1 ─────────────────────────────────────────────────────────
function validateStep1(d: ProClientData): Partial<Record<keyof ProClientData, string>> {
  const e: Partial<Record<keyof ProClientData, string>> = {};
  if (!d.client_name.trim())    e.client_name    = "Requerido";
  if (!d.legal_name.trim())     e.legal_name     = "Requerido";
  if (!d.nit.trim())            e.nit            = "Requerido";
  if (!d.sector)                e.sector         = "Selecciona un sector";
  if (!d.city)                  e.city           = "Selecciona una ciudad";
  if (!d.size_org)              e.size_org       = "Requerido";
  if (!d.years_operating)       e.years_operating = "Requerido";
  if (!d.contact_name.trim())   e.contact_name   = "Requerido";
  if (!d.contact_role.trim())   e.contact_role   = "Requerido";
  if (!d.contact_email.includes("@")) e.contact_email = "Email inválido";
  if (!d.contact_phone.trim())  e.contact_phone  = "Requerido";
  if (!d.domain)                e.domain         = "Selecciona un área";
  if (d.symptom.trim().length < 20) e.symptom    = "Describe el problema (mín. 20 caracteres)";
  if (!d.problem_since.trim())  e.problem_since  = "Requerido";
  if (d.expected_outcome.trim().length < 10) e.expected_outcome = "Describe el resultado esperado";
  return e;
}

// ── componente ────────────────────────────────────────────────────────────────
export function ProCaseWizard() {
  const router = useRouter();
  const draft = loadDraft();
  const [step, setStep]       = useState(draft?.step ?? 1);
  const [client, setClient]   = useState<ProClientData>(draft?.client ?? defaultClient);
  const [scope, setScope]     = useState<ProScopeData>(draft?.scope ?? defaultScope);
  const [consent, setConsent] = useState<ProConsentData>(defaultConsent);
  const [errors, setErrors]   = useState<Partial<Record<keyof ProClientData, string>>>({});

  // Guardar borrador cada vez que cambian los datos
  useEffect(() => { saveDraft(client, scope, step); }, [client, scope, step]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const cloneId = params.get("clone_from");
    
    // Si venimos de un clone explícito, ignoramos el borrador local
    if (cloneId) {
      clearDraft();
      apiPro.get(`/pro/cases/${cloneId}`).then(res => {
        const data = res.data;
        const extra = data.input_payload?.extra || {};
        setClient({
          engagement_id: data.engagement_id || "",
          client_name: data.client_name || "",
          legal_name: extra.legal_name || "",
          nit: extra.nit || "",
          sector: extra.sector || "Tecnología",
          city: extra.city || "",
          country: extra.country || "",
          size_org: extra.size_org || "51-200",
          years_operating: extra.years_operating || "",
          contact_name: extra.contact_name || "",
          contact_role: extra.contact_role || "",
          contact_email: extra.contact_email || "",
          contact_phone: extra.contact_phone || "",
          domain: data.domain || "Desarrollo de software",
          symptom: "", // Limpio para el nuevo diagnóstico
          problem_since: "",
          areas_count: "1",
          previous_attempts: "No",
          expected_outcome: "",
          deadline: "30 días",
          confidentiality: "Standard",
        });
      });
    }
  }, []);

  const mutation = useMutation({
    mutationFn: (payload: any) => apiPro.post("/pro/cases", payload).then(r => r.data),
    onSuccess: (data) => {
      clearDraft();
      router.push(`/dashboard-pro/cases/${data.id}`);
    },
  });

  function handleNext1() {
    const e = validateStep1(client);
    if (Object.keys(e).length > 0) { setErrors(e); return; }
    setErrors({});
    setStep(2);
  }

  function handleSubmit() {
    const engId = client.engagement_id.trim() || `eng-${Date.now()}`;
    mutation.mutate({
      consent: { action: "ingest_to_llm", consents: { T1: consent.t1, T3: consent.t3 } },
      engagement_id: engId,
      client_name: client.client_name,
      domain: client.domain,
      roles: scope.roles,
      dimensions: scope.dimensions,
      hypotheses: scope.hypotheses.filter(h => h.trim()),
      grey_sources: scope.grey_sources.filter(g => g.trim()),
      // Contexto extra para el reporte
      extra: {
        legal_name:       client.legal_name,
        nit:              client.nit,
        sector:           client.sector,
        city:             client.city,
        country:          client.country,
        size_org:         client.size_org,
        years_operating:  client.years_operating,
        contact_name:     client.contact_name,
        contact_role:     client.contact_role,
        contact_email:    client.contact_email,
        contact_phone:    client.contact_phone,
        symptom:          client.symptom,
        problem_since:    client.problem_since,
        areas_count:      client.areas_count,
        previous_attempts: client.previous_attempts,
        expected_outcome: client.expected_outcome,
        deadline:         client.deadline,
        confidentiality:  client.confidentiality,
      },
    });
  }

  return (
    <div style={{ maxWidth: "760px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ paddingBottom: "24px", borderBottom: "1px solid rgba(23,23,23,0.12)", marginBottom: "32px" }}>
        <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.06em" }}>
          § nuevo caso
        </p>
        <h1 style={{ margin: "6px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "52px", lineHeight: 0.92, color: "#171717" }}>
          Nuevo Diagnóstico Pro
        </h1>
        <p style={{ margin: "10px 0 0", fontSize: "14px", color: "#706f69", maxWidth: "600px", lineHeight: 1.5 }}>
          Inicie un ciclo de evaluación de alta fidelidad. El sistema generará instrumentos adaptativos y procesará los resultados mediante síntesis bayesiana gobernada.
        </p>
        {loadDraft() && (
          <button
            onClick={() => { clearDraft(); setClient(defaultClient); setScope(defaultScope); setStep(1); }}
            style={{ marginTop: "8px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#8b3a3a", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
            type="button"
          >
            × Limpiar borrador guardado
          </button>
        )}
      </div>

      {/* Stepper */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "32px" }}>
        {STEPS.map((s, i) => (
          <div key={s.n} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{
              width: "26px", height: "26px", borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
              background: s.n < step ? "#56624b" : s.n === step ? "#171717" : "transparent",
              color: s.n <= step ? "#f4f1ea" : "#c0bdb6",
              border: s.n > step ? "1px solid rgba(23,23,23,0.14)" : "none",
            }}>
              {s.n < step ? <Check size={11} /> : s.n}
            </div>
            <span style={{
              fontSize: "12px", fontFamily: "IBM Plex Mono, monospace",
              color: s.n === step ? "#171717" : "#c0bdb6",
              fontWeight: s.n === step ? 500 : 400,
            }}>{s.label}</span>
            {i < STEPS.length - 1 && (
              <div style={{ width: "28px", height: "1px", background: "rgba(23,23,23,0.12)", margin: "0 4px" }} />
            )}
          </div>
        ))}
      </div>

      {/* Panel */}
      <div style={{
        background: "rgba(255,255,255,0.72)",
        border: "1px solid rgba(23,23,23,0.1)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        padding: "32px 36px",
        maxHeight: "calc(100vh - 280px)",
        overflowY: "auto",
      }}>
        {step === 1 && (
          <ProStep1Client data={client} onChange={setClient} onNext={handleNext1} errors={errors} />
        )}
        {step === 2 && (
          <ProStep2Scope data={scope} onChange={setScope} onNext={() => setStep(3)} onBack={() => setStep(1)} />
        )}
        {step === 3 && (
          <ProStep3Review
            client={client} scope={scope} consent={consent} onConsent={setConsent}
            onBack={() => setStep(2)} onSubmit={handleSubmit}
            isSubmitting={mutation.isPending}
            error={mutation.isError ? "Error al crear el caso. Verifica la conexión con el servidor." : undefined}
          />
        )}
      </div>
    </div>
  );
}
