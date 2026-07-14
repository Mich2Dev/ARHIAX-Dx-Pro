"use client";

import dynamic from "next/dynamic";
import type { BrainSectionHint, BrainVariant } from "@/components/features/pro/CaseDecisionBrain";

const CaseDecisionBrainInner = dynamic(
  () => import("@/components/features/pro/CaseDecisionBrain").then((m) => m.CaseDecisionBrain),
  {
    ssr: false,
    loading: () => (
      <section
        style={{
          border: "1px solid rgba(42,47,40,0.1)",
          borderRadius: 12,
          padding: "48px 20px",
          textAlign: "center",
          color: "#6b7280",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 12,
          background: "linear-gradient(165deg, #f7f1e6 0%, #e8e1d2 55%, #ddd4c4 100%)",
          minHeight: 280,
          display: "grid",
          placeItems: "center",
        }}
      >
        Preparando traza 3D…
      </section>
    ),
  }
);

type Props = {
  caseData: any;
  variant?: BrainVariant;
  section?: BrainSectionHint;
};

export function CaseDecisionBrainLazy({ caseData, variant = "full", section }: Props) {
  return <CaseDecisionBrainInner caseData={caseData} variant={variant} section={section} />;
}
