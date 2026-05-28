import { Suspense } from "react";
import { DiagnosticWizard } from "@/components/features/diagnostics/DiagnosticWizard";
import { Spinner } from "@/components/ui/Spinner";

export default function NewDiagnosticPage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-16"><Spinner /></div>}>
      <DiagnosticWizard />
    </Suspense>
  );
}
