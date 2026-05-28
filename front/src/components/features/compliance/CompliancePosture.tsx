"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";

export function CompliancePosture() {
  const { data, isLoading } = useQuery({
    queryKey: ["compliance"],
    queryFn: async () => {
      const govUrl = process.env.NEXT_PUBLIC_GOVERNANCE_URL ?? "http://localhost:8088";
      const res = await fetch(`${govUrl}/v1/compliance/posture`);
      return res.json();
    },
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Postura de Cumplimiento</h1>

      {/* Identity */}
      <Card title="Identidad del Agente">
        <Row label="Nombre"     value={data.agent_identity?.name} />
        <Row label="Versión"    value={data.agent_identity?.version} />
        <Row label="Propietario" value={data.agent_identity?.owner} />
        <Row label="Boundary"   value={data.agent_identity?.authorization_boundary_id} />
        <Row label="Autonomía inicial" value={data.agent_identity?.initial_autonomy_level} />
        <Row label="Autonomía máxima"  value={data.agent_identity?.allowed_autonomy_ceiling} />
      </Card>

      {/* Governance metadata */}
      <Card title="Versiones de Gobernanza">
        {Object.entries(data.governance_metadata ?? {}).map(([k, v]) => (
          <Row key={k} label={k} value={String(v)} />
        ))}
      </Card>

      {/* Policy bundles */}
      <Card title="Bundles de Política">
        {data.policy_matrix?.controls?.map((c: any) => (
          <div key={c.policy_id} className="flex items-start gap-3 py-1.5 border-b border-gray-50 last:border-0">
            <Badge variant="blue">{c.policy_id}</Badge>
            <div>
              <p className="text-sm font-medium text-gray-800">{c.title}</p>
              <p className="text-xs text-gray-400">{c.rule_ids?.join(", ")}</p>
            </div>
          </div>
        ))}
      </Card>

      {/* Tool manifest count */}
      <Card title={`Catálogo de Herramientas (${data.tool_manifest?.length ?? 0})`}>
        <div className="flex flex-wrap gap-1.5">
          {data.tool_manifest?.map((t: any) => (
            <Badge key={t.name} variant={t.severity === "CRITICAL" ? "red" : t.severity === "HIGH" ? "orange" : "gray"}>
              {t.name}
            </Badge>
          ))}
        </div>
      </Card>

      {/* Install readiness */}
      <InstallReadiness />
    </div>
  );
}

function InstallReadiness() {
  const { data } = useQuery({
    queryKey: ["install-readiness"],
    queryFn: async () => {
      const govUrl = process.env.NEXT_PUBLIC_GOVERNANCE_URL ?? "http://localhost:8088";
      const res = await fetch(`${govUrl}/v1/compliance/install-readiness`);
      return res.json();
    },
  });

  if (!data) return null;

  return (
    <Card title="Estado de Instalación">
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-sm font-bold ${data.install_ready ? "text-green-600" : "text-orange-600"}`}>
          {data.install_ready ? "✓ Listo para producción" : "⚠ Bindings pendientes"}
        </span>
      </div>
      {data.post_install_requirements?.map((r: any) => (
        <div key={r.requirement} className="flex items-center gap-2 py-1 text-sm">
          <Badge variant={r.status === "configured" ? "green" : r.status === "optional_not_enabled" ? "gray" : "orange"}>
            {r.status}
          </Badge>
          <span className="text-gray-700">{r.requirement}</span>
        </div>
      ))}
    </Card>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex gap-2 text-sm py-0.5">
      <span className="text-gray-400 w-40 shrink-0">{label}</span>
      <span className="text-gray-800 font-medium">{value ?? "—"}</span>
    </div>
  );
}
