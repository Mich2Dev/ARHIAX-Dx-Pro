"use client";

import { Component, type ReactNode } from "react";
import dynamic from "next/dynamic";
import type { BrainSectionHint, BrainVariant } from "@/components/features/pro/CaseDecisionBrain";

/**
 * Carga el mapa 2D legible (no el globo 3D oscuro).
 * El 3D queda aparcado hasta que haya una lectura que realmente aporte.
 */
const CaseTraceGraphInner = dynamic(
  () => import("@/components/features/pro/CaseTraceGraph").then((m) => m.CaseTraceGraph),
  {
    ssr: false,
    loading: () => (
      <section
        style={{
          border: "1px solid rgba(23,23,23,0.12)",
          padding: "48px 20px",
          textAlign: "center",
          color: "#706f69",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 12,
          background: "#f4f1ea",
          minHeight: 280,
        }}
      >
        Cargando traza…
      </section>
    ),
  }
);

type Props = {
  caseData: any;
  variant?: BrainVariant;
  section?: BrainSectionHint;
};

class MapErrorBoundary extends Component<
  { children: ReactNode; onReset?: () => void },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <section
          style={{
            border: "1px solid rgba(139,58,58,0.35)",
            padding: "28px 18px",
            background: "#f4f1ea",
            minHeight: 220,
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              color: "#8b3a3a",
              letterSpacing: "0.08em",
            }}
          >
            MAPA · ERROR
          </p>
          <p style={{ margin: "8px 0 0", fontSize: 14, color: "#171717", lineHeight: 1.45 }}>
            La traza se cayó al renderizar. El resto del caso sigue usable.
          </p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: 14,
              padding: "8px 12px",
              border: "1px solid rgba(23,23,23,0.14)",
              background: "#fff",
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: 11,
              cursor: "pointer",
              color: "#171717",
            }}
          >
            Reintentar mapa
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}

export function CaseDecisionBrainLazy({ caseData, variant = "full", section }: Props) {
  return (
    <MapErrorBoundary>
      <CaseTraceGraphInner caseData={caseData} variant={variant} section={section} />
    </MapErrorBoundary>
  );
}
