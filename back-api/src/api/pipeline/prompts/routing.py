"""Model routing config per agent — based on ARHIAX Dx Briefing v5.1."""
from __future__ import annotations

MODEL_ROUTING: dict[str, dict] = {
    # Intake — fast, low cost
    "g01_receptor":      {"model": "gemini-2.5-flash", "max_tokens": 4096,  "temperature": 0.2},
    "g02_configurador":  {"model": "gemini-2.5-flash", "max_tokens": 4096,  "temperature": 0.2},
    "g09b_ramificacion": {"model": "gemini-2.5-flash", "max_tokens": 4096,  "temperature": 0.2},
    "g10b_psicometria":  {"model": "gemini-2.5-flash", "max_tokens": 4096,  "temperature": 0.2},
    # Brechas e hipótesis
    "g05_brechas":       {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.2},
    # Scoring
    "g10a_scoring":      {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.2},
    # Research & design
    "g03_cienciometro":   {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "g04_cartografo":     {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "g06_bpmn_architect": {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "g07_cuellos":        {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "g08_optimizador":    {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "academic_search":    {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "web_search":         {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    "bpmn_generator":     {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.3},
    # Survey & NLP
    "g09a_preguntas":  {"model": "gemini-2.5-flash", "max_tokens": 16384, "temperature": 0.3},
    "g09c_validacion": {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.3},
    "g11b_nlp":        {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.3},
    "g12_hallazgos":   {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.3},
    "irr_calculator":  {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.3},
    "scoring_engine":  {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.3},
    # Bayesian — low temp, max precision
    "g11a_bayesiano": {"model": "gemini-2.5-flash", "max_tokens": 8192,  "temperature": 0.1},
    # Executive writing
    "g13_redactor":   {"model": "gemini-2.5-flash", "max_tokens": 16384, "temperature": 0.7},
    # QA & assembly
    "g14_qa_control":  {"model": "gemini-2.5-flash", "max_tokens": 16384, "temperature": 0.2},
    "docx_generator":  {"model": "gemini-2.5-flash", "max_tokens": 16384, "temperature": 0.2},
}


def get_model_config(tool_name: str) -> dict:
    return MODEL_ROUTING.get(
        tool_name,
        {"model": "gemini-2.5-flash", "max_tokens": 8192, "temperature": 0.2},
    )
