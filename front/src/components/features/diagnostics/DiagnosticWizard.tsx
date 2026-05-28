"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DEPTH_PRESETS } from "@/config/pipeline-presets";
import { Step1ClientData } from "./wizard/Step1ClientData";
import { Step1NewDiagnostic } from "./wizard/Step1NewDiagnostic";
import { Step2Depth } from "./wizard/Step2Depth";
import { Step3Review } from "./wizard/Step3Review";
import { Step4Documents } from "./wizard/Step4Documents";
import { Spinner } from "@/components/ui/Spinner";
import type { ClientData, DiagnosticDepth } from "@/lib/types";

const STEPS_EXISTING = [
  { n: 1, label: "El problema" },
  { n: 2, label: "Tipo de diagnostico" },
  { n: 3, label: "Revision y envio" },
  { n: 4, label: "Documentos" },
];

const STEPS_NEW = [
  { n: 1, label: "Datos del cliente" },
  { n: 2, label: "Tipo de diagnostico" },
  { n: 3, label: "Revision y envio" },
  { n: 4, label: "Documentos" },
];

const defaultClient: ClientData = {
  organization_name: "",
  legal_name: "",
  nit: "",
  sector: "",
  city: "",
  country: "Colombia",
  size_org: "",
  years_operating: "",
  contact_name: "",
  contact_role: "",
  contact_email: "",
  contact_phone: "",
  area: "",
  symptom: "",
  problem_since: "",
  previous_attempts: "",
  expected_outcome: "",
  areas_count: "1",
  survey_participants: "",
  deadline: "",
  confidentiality: "Confidencial - Uso Estrategico",
};

export function DiagnosticWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const existingClientId = searchParams.get("client") ?? "";
  const isExistingClient = !!existingClientId;

  const [step, setStep]               = useState(1);
  const [client, setClient]           = useState<ClientData>(defaultClient);
  const [depth, setDepth]             = useState<DiagnosticDepth>("standard");
  const [publish, setPublish]         = useState(false);
  const [certificate, setCertificate] = useState(true);
  const [createdId, setCreatedId]     = useState<string | null>(null);
  const [prefilling, setPrefilling]   = useState(isExistingClient);

  useEffect(() => {
    if (!existingClientId) return;
    const t = setTimeout(() => setPrefilling(false), 5000);
    api.get(`/v2/diagnostics/clients/${existingClientId}/prefill`)
      .then(r => {
        const d = r.data;
        setClient(prev => ({
          ...prev,
          organization_name: d.organization_name || prev.organization_name,
          legal_name:        d.legal_name        || prev.legal_name,
          nit:               d.nit               || prev.nit,
          sector:            d.sector            || prev.sector,
          city:              d.city              || prev.city,
          country:           d.country           || prev.country,
          size_org:          d.size_org          || prev.size_org,
          years_operating:   d.years_operating   || prev.years_operating,
          contact_name:      d.contact_name      || prev.contact_name,
          contact_role:      d.contact_role      || prev.contact_role,
          contact_email:     d.contact_email     || prev.contact_email,
          contact_phone:     d.contact_phone     || prev.contact_phone,
          confidentiality:   d.confidentiality   || prev.confidentiality,
        }));
      })
      .catch(() => {})
      .finally(() => { clearTimeout(t); setPrefilling(false); });
    return () => clearTimeout(t);
  }, [existingClientId]);

  const mutation = useMutation({
    mutationFn: (payload: any) =>
      api.post("/v2/diagnostics/submit", payload).then(r => r.data),
    onSuccess: (data) => { setCreatedId(data.id); setStep(4); },
  });

  function handleSubmit() {
    mutation.mutate({
      organization_name:        client.organization_name,
      legal_name:               client.legal_name,
      client_id:                existingClientId || `client-${client.nit || Date.now()}`,
      domain:                   client.sector,
      subprocess:               client.area,
      size_org:                 client.size_org,
      objective:                client.symptom,
      extra_context: {
        nit:             client.nit,
        sector:          client.sector,
        city:            client.city,
        country:         client.country,
        years_operating: client.years_operating,
        contact_name:    client.contact_name,
        contact_role:    client.contact_role,
        contact_email:   client.contact_email,
        contact_phone:   client.contact_phone,
        confidentiality: client.confidentiality,
      },
      requested_tools:          DEPTH_PRESETS[depth].tools,
      requested_operations:     ["modelInvoke", "toolCall", "dataAccess", "interAgentCall"],
      requested_data_scopes:    ["organizational_context", "survey_responses", "report_outputs", "audit_log"],
      requested_autonomy_level: "A1",
      processing_profile: {
        store_raw_respondent_data: false,
        publish_report:            false,  // always internal — consultant downloads and delivers manually
        issue_certificate:         certificate,
        retention_days:            30,
      },
    });
  }

  if (prefilling) {
    return (
      <div className="max-w-2xl mx-auto flex justify-center py-16">
        <div className="text-center space-y-3">
          <Spinner className="w-8 h-8 mx-auto" />
          <p className="text-sm text-gray-500">Cargando datos del cliente...</p>
        </div>
      </div>
    );
  }

  const steps = isExistingClient ? STEPS_EXISTING : STEPS_NEW;

  return (
    <div style={{ maxWidth: "760px", margin: "0 auto" }}>
      {/* Stepper */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "32px" }}>
        {steps.map((s, i) => (
          <div key={s.n} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{
              width: "26px", height: "26px", borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
              background: s.n < step ? "#56624b" : s.n === step ? "#171717" : "transparent",
              color: s.n <= step ? "#f4f1ea" : "#c0bdb6",
              border: s.n > step ? "1px solid rgba(23,23,23,0.14)" : "none",
            }}>{s.n}</div>
            <span style={{
              fontSize: "12px", fontFamily: "IBM Plex Mono, monospace",
              color: s.n === step ? "#171717" : "#c0bdb6",
              fontWeight: s.n === step ? 500 : 400,
            }}>{s.label}</span>
            {i < steps.length - 1 && (
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
        maxHeight: "calc(100vh - 260px)", overflowY: "auto",
      }}>
        {step === 1 && isExistingClient && (
          <Step1NewDiagnostic
            client={client}
            onChange={setClient}
            onNext={() => setStep(2)}
          />
        )}
        {step === 1 && !isExistingClient && (
          <Step1ClientData
            key={client.organization_name}
            data={client}
            onChange={setClient}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <Step2Depth
            depth={depth}
            publish={publish}
            certificate={certificate}
            onDepth={setDepth}
            onPublish={setPublish}
            onCertificate={setCertificate}
            onNext={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <Step3Review
            client={client}
            depth={depth}
            publish={publish}
            certificate={certificate}
            isExistingClient={isExistingClient}
            onBack={() => setStep(2)}
            onSubmit={handleSubmit}
            isSubmitting={mutation.isPending}
            error={mutation.error?.message}
          />
        )}
        {step === 4 && createdId && (
          <Step4Documents
            diagnosticId={createdId}
            onDone={() => router.push(`/dashboard/diagnostics/${createdId}`)}
            onSkip={() => router.push(`/dashboard/diagnostics/${createdId}`)}
          />
        )}
      </div>
    </div>
  );
}