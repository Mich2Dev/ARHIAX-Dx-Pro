import { DiagnosticDetail } from "@/components/features/diagnostics/DiagnosticDetail";

export default function DiagnosticDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <DiagnosticDetail id={params.id} />;
}
