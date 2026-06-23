import { describe, it, expect } from 'vitest'
import { lintText, canPublish, compileReportText, type GrammarException } from '../lib/canonicalGrammar'

// Fixture intencional de mojibake para probar detección de encoding roto.
// Los caracteres Ã, Â, â, ¿, etc. son compatibles con lintText().
describe('canonicalGrammar — mojibake', () => {
  it('detecta encoding roto', () => {
    const r = lintText('La aprobaciÃ³n todavÃ­a no estÃ¡ lista.')
    expect(r.critical).toBeGreaterThanOrEqual(1)
    expect(r.findings[0].severity).toBe('critical')
  })

  it('texto limpio no produce críticos', () => {
    const r = lintText('La aprobación todavía no está lista.')
    expect(r.critical).toBe(0)
  })
})

describe('canonicalGrammar — coma de Oxford', () => {
  it('detecta coma antes de y en enumeración', () => {
    const r = lintText('El informe evalúa procesos, datos, y gobernanza.')
    expect(r.major).toBeGreaterThanOrEqual(1)
    expect(r.findings.some(f => f.ruleId === 'GC-03-OXFORD-001')).toBe(true)
  })

  it('no detecta enumeración sin coma serial', () => {
    const r = lintText('El informe evalúa procesos, datos y gobernanza.')
    const oxford = r.findings.filter(f => f.ruleId === 'GC-03-OXFORD-001')
    expect(oxford.length).toBe(0)
  })

  it('no detecta coma sin conjunción y/e/o/u', () => {
    const r = lintText('No se detectó, sin embargo, ningún error.')
    const oxford = r.findings.filter(f => f.ruleId === 'GC-03-OXFORD-001')
    expect(oxford.length).toBe(0)
  })
})

describe('canonicalGrammar — calcos del inglés', () => {
  it('detecta "hacer sentido"', () => {
    const r = lintText('La recomendación hace sentido para el cliente.')
    expect(r.findings.some(f => f.ruleId === 'GC-04-CALCO-001')).toBe(true)
  })

  it('detecta "en base a"', () => {
    const r = lintText('Decidimos en base a los resultados.')
    expect(r.findings.some(f => f.ruleId === 'GC-04-CALCO-002')).toBe(true)
  })

  it('detecta "a nivel de"', () => {
    const r = lintText('A nivel de proceso, observamos demoras.')
    expect(r.findings.some(f => f.ruleId === 'GC-04-CALCO-003')).toBe(true)
  })
})

describe('canonicalGrammar — terminología invariante', () => {
  it('detecta "Arhiax" en minúscula', () => {
    const r = lintText('Arhiax opera como herramienta.')
    expect(r.findings.some(f => f.ruleId === 'GC-02-TERM-001' || f.ruleId === 'GC-02-TERM-002')).toBe(true)
  })

  it('detecta "DxPro" sin espacio', () => {
    const r = lintText('El sistema DxPro es una plataforma.')
    expect(r.findings.some(f => f.ruleId === 'GC-02-TERM-003')).toBe(true)
  })

  it('sugiere "ARHIAX" para "arhiax"', () => {
    const r = lintText('El modulo arhiax procesa.')
    expect(r.findings.some(f => f.suggestion === 'ARHIAX')).toBe(true)
  })

  it('no marca DxPro en rutas técnicas', () => {
    const r = lintText('src/dxpro_runtime no debe sugerir Dx Pro.')
    expect(r.findings.some(f => f.ruleId === 'GC-02-TERM-003')).toBe(false)
  })

  it('no marca DXPRO en contextos de código', () => {
    const r = lintText('case_id: DXPRO_TEST_001')
    expect(r.findings.some(f => f.ruleId === 'GC-02-TERM-004')).toBe(false)
  })
})

describe('canonicalGrammar — ortografía RAE', () => {
  it('detecta mes con mayúscula', () => {
    const r = lintText('El informe se entregó en Enero.')
    expect(r.findings.some(f => f.ruleId === 'GC-06-RAE-001')).toBe(true)
  })

  it('detecta día con mayúscula', () => {
    const r = lintText('La reunión fue el Lunes.')
    expect(r.findings.some(f => f.ruleId === 'GC-06-RAE-002')).toBe(true)
  })
})

describe('canonicalGrammar — falsa fluidez', () => {
  it('detecta "Es importante mencionar que"', () => {
    const r = lintText('Es importante mencionar que el proceso mejoró.')
    expect(r.findings.some(f => f.ruleId === 'GC-05-FLUID-001')).toBe(true)
  })
})

describe('canonicalGrammar — audiencia', () => {
  it('aplica reglas de cliente cuando la audiencia es client', () => {
    const r = lintText('El custodio revisó el caso.', 'client')
    expect(r.findings.some(f => f.ruleId === 'GC-07-REG-001')).toBe(true)
  })

  it('no marca términos internos con audiencia internal', () => {
    const r = lintText('El custodio revisó el caso.', 'internal')
    expect(r.findings.some(f => f.ruleId === 'GC-07-REG-001')).toBe(false)
  })
})

describe('canonicalGrammar — canPublish', () => {
  // Fixture intencional: Ã es mojibake para probar bloqueo crítico
  it('bloquea publicación con hallazgos críticos', () => {
    const r = lintText('Ã rotas')
    expect(canPublish(r).allowed).toBe(false)
  })

  it('permite publicación sin hallazgos', () => {
    const r = lintText('Texto completamente correcto y canónico.')
    expect(canPublish(r).allowed).toBe(true)
  })

  it('advierte con hallazgos mayores y requiere confirmación', () => {
    const r = lintText('Arhiax DxPro opera como herramienta.')
    const check = canPublish(r)
    expect(check.allowed).toBe(true)
    expect(check.confirmRequired).toBe(true)
    expect(check.reason).toContain('Hallazgos mayores')
  })

  it('excepción en hallazgo crítico permite publicación', () => {
    const r = lintText('Ã rotas')
    const exc: GrammarException[] = [{
      findingId: 'exc-1',
      ruleId: r.findings[0].ruleId,
      detectedText: r.findings[0].detectedText,
      reason: 'Texto de prueba controlado',
      reviewer: 'Test',
      createdAt: new Date().toISOString(),
    }]
    const check = canPublish(r, exc)
    expect(check.allowed).toBe(true)
  })

  it('excepción en hallazgo mayor elimina requerimiento de confirmación', () => {
    const r = lintText('Arhiax DxPro opera como herramienta.')
    const majorFindings = r.findings.filter(f => f.severity === 'major')
    const exc: GrammarException[] = majorFindings.map((f, i) => ({
      findingId: `exc-${i}`,
      ruleId: f.ruleId,
      detectedText: f.detectedText,
      reason: 'Excepción de prueba',
      reviewer: 'Test',
      createdAt: new Date().toISOString(),
    }))
    const check = canPublish(r, exc)
    expect(check.allowed).toBe(true)
    expect(check.confirmRequired).toBeUndefined()
  })

  it('excepción vacía no permite continuar (sin razón)', () => {
    const r = lintText('Ã rotas')
    const exc: GrammarException[] = [{
      findingId: 'exc-1',
      ruleId: r.findings[0].ruleId,
      detectedText: r.findings[0].detectedText,
      reason: '',
      reviewer: 'Test',
      createdAt: new Date().toISOString(),
    }]
    const check = canPublish(r, exc)
    expect(check.allowed).toBe(false)
  })
})

describe('canonicalGrammar — compileReportText', () => {
  it('incluye score, hallazgos y sugerencia en el texto copiable', () => {
    const r = lintText('Arhiax DxPro opera como herramienta.')
    const text = compileReportText(r)
    expect(text).toContain('Revisión canónica ARHIAX')
    expect(text).toContain(String(r.score))
    expect(text).toContain('GC-02-TERM')
    expect(text).toContain('Dx Pro')
  })

  it('incluye estado de excepción cuando se proveen', () => {
    const r = lintText('Arhiax DxPro opera como herramienta.')
    const exc: GrammarException[] = [{
      findingId: 'exc-1',
      ruleId: r.findings[0].ruleId,
      detectedText: r.findings[0].detectedText,
      reason: 'Razón de prueba',
      reviewer: 'Revisor Test',
      createdAt: new Date().toISOString(),
    }]
    const text = compileReportText(r, exc)
    expect(text).toContain('Excepcionado')
    expect(text).toContain('Razón de prueba')
    expect(text).toContain('Revisor Test')
  })

  it('reporta "Sin hallazgos" para texto limpio', () => {
    const r = lintText('Texto completamente correcto y canónico.')
    const text = compileReportText(r)
    expect(text).toContain('Sin hallazgos')
  })
})
