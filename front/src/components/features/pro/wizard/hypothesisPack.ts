export type HypothesisConfidence = "ALTA" | "MEDIA" | "BAJA";
export type DatoDuro = "ALTO" | "BAJO";

export interface ProHypothesis {
  hipotesis_id: string;
  enunciado: string;
  confianza: HypothesisConfidence;
  observacion_refutadora: string;
  informante_id: string;
  incidente_texto: string;
  dato_duro: DatoDuro;
}

export function emptyHypothesis(index: number): ProHypothesis {
  return {
    hipotesis_id: `H-${String(index + 1).padStart(2, "0")}`,
    enunciado: "",
    confianza: "MEDIA",
    observacion_refutadora: "",
    informante_id: "INF-01",
    incidente_texto: "",
    dato_duro: "ALTO",
  };
}

export function isHypothesisComplete(h: ProHypothesis): boolean {
  return (
    h.enunciado.trim().length >= 12 &&
    h.observacion_refutadora.trim().length >= 8 &&
    h.incidente_texto.trim().length >= 20
  );
}

export function buildHypothesisPayload(pack: ProHypothesis[]) {
  const valid = pack.filter(isHypothesisComplete);
  const paquete_hipotesis = valid.map((h) => ({
    hipotesis_id: h.hipotesis_id,
    confianza: h.confianza,
    enunciado: h.enunciado.trim(),
    observacion_refutadora: h.observacion_refutadora.trim(),
    informante_id: h.informante_id.trim() || "INF-01",
    incidente_texto: h.incidente_texto.trim(),
    dato_duro: h.dato_duro,
  }));
  return {
    paquete_hipotesis,
    hypotheses: valid.map((h) => h.enunciado.trim()),
  };
}
