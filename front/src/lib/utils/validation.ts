/**
 * Shared validation helpers for diagnostic form fields.
 */
import { z } from "zod";

/**
 * Detects nonsense text: repeated characters, keyboard mashing, etc.
 * Returns true if the text looks like real content.
 */
export function isCoherentText(text: string): boolean {
  if (!text || text.trim().length === 0) return false;

  const t = text.trim();

  // Must have at least 3 words of 2+ letters
  const words = t.match(/[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,}/g) ?? [];
  if (words.length < 3) return false;

  // Unique words ratio — if >70% are the same word, it's spam
  const unique = new Set(words.map(w => w.toLowerCase()));
  if (unique.size < 2) return false;

  // No single character repeated more than 6 times consecutively
  if (/(.)\1{6,}/.test(t)) return false;

  // No sequence of 3+ identical chars making up >50% of the text
  const longestRun = (t.match(/(.)\1*/g) ?? []).reduce(
    (max, run) => Math.max(max, run.length), 0
  );
  if (longestRun > t.length * 0.4) return false;

  return true;
}

/** Zod refinement for coherent text fields */
export const coherentText = (minLen: number, fieldName: string) =>
  z.string()
    .min(minLen, `${fieldName} debe tener al menos ${minLen} caracteres`)
    .refine(isCoherentText, {
      message: `${fieldName} no parece ser texto coherente. Por favor describe el problema con palabras reales.`,
    });

/** Zod refinement for organization/person names */
export const coherentName = (fieldName: string) =>
  z.string()
    .min(2, `${fieldName} es requerido`)
    .refine(
      (v) => /[a-záéíóúüñA-ZÁÉÍÓÚÜÑA-Za-z]{2,}/.test(v),
      { message: `${fieldName} debe contener letras reales` }
    );
