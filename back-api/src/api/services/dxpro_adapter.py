"""
Adaptador para integrar Dx Pro con Dx Standard
Convierte datos de PostgreSQL al formato que espera Dx Pro
"""
import httpx
import os
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models import Diagnostic, SurveyResponse


class DxProAdapter:
    """Adaptador para ejecutar diagnósticos con motor Dx Pro"""
    
    def __init__(self, dxpro_url: str = None):
        # En Docker usa el nombre del servicio, en local usa localhost
        self.dxpro_url = dxpro_url or os.getenv("DXPRO_URL", "http://dxpro:8310")
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout
    
    async def convert_diagnostic_to_pro_format(
        self, 
        diagnostic: Diagnostic,
        responses: List[SurveyResponse]
    ) -> Dict[str, Any]:
        """
        Convierte un diagnóstico de Standard a formato Pro
        """
        # Extraer roles únicos
        roles = list(set(r.role for r in responses if r.role))
        
        # Extraer dimensiones únicas
        dimensions = list(set(r.dimension for r in responses if r.dimension))
        
        # Convertir respuestas
        response_list = [
            {
                "role": r.role,
                "dimension": r.dimension,
                "item_id": r.item_id or f"{r.dimension}-{r.id}",
                "score": r.score
            }
            for r in responses
        ]
        
        # Crear matriz de respuestas (simplificada)
        # En producción, esto debería ser más sofisticado
        response_matrix = []
        for role in roles:
            role_scores = [
                r.score for r in responses 
                if r.role == role
            ]
            if role_scores:
                response_matrix.append(role_scores[:len(dimensions)])
        
        # Payload para Dx Pro
        payload = {
            "consent": {
                "action": "ingest_to_llm",
                "consents": {"T1": True, "T3": True}
            },
            "engagement_id": f"eng-{diagnostic.id}",
            "client": {
                "legal_name": diagnostic.organization_name,
                "name": diagnostic.organization_name
            },
            "domain": diagnostic.domain or "organizational diagnostic",
            "roles": roles,
            "dimensions": dimensions,
            "responses": response_list,
            "response_matrix": response_matrix,
            "diagnostic_hypotheses": [
                {
                    "id": "DH1",
                    "statement": f"Análisis de {diagnostic.domain}",
                    "prior": 0.5
                }
            ],
            "evidence_signals": [],
            "hypothesis_pack": {
                "hypothesis_pack_version": "1.0",
                "engagement_id": f"eng-{diagnostic.id}",
                "domain": diagnostic.domain or "organizational diagnostic",
                "hypotheses": []
            },
            "grey_sources": [],
            "bpmn_model": {
                "nodes": [],
                "edges": []
            },
            "targets": ["markdown", "docx", "pdf"]
        }
        
        return payload
    
    async def execute_diagnostic(
        self,
        diagnostic: Diagnostic,
        responses: List[SurveyResponse]
    ) -> Dict[str, Any]:
        """
        Ejecuta un diagnóstico usando el motor Dx Pro
        """
        # Convertir a formato Pro
        payload = await self.convert_diagnostic_to_pro_format(diagnostic, responses)
        
        # Llamar a Dx Pro
        response = await self.client.post(
            f"{self.dxpro_url}/v1/agents/cases/run",
            json=payload
        )
        response.raise_for_status()
        
        return response.json()
    
    async def get_case_status(self, case_id: str) -> Dict[str, Any]:
        """Obtiene el estado de un caso en Dx Pro"""
        response = await self.client.get(
            f"{self.dxpro_url}/v1/cases/{case_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Cierra el cliente HTTP"""
        await self.client.aclose()
