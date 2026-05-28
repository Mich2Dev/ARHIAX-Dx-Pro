"""
Router para ejecutar diagnósticos con motor Dx Pro
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.db import get_db
from api.models import Diagnostic, SurveyResponse, User
from api.auth import get_current_user
from api.services.dxpro_adapter import DxProAdapter
from typing import Dict, Any

router = APIRouter(prefix="/v2/diagnostics", tags=["dxpro"])


@router.post("/{diagnostic_id}/execute-pro")
async def execute_with_pro_engine(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Ejecuta un diagnóstico usando el motor Dx Pro (fusion cycle)
    
    Requiere que el diagnóstico tenga al menos 5 respuestas de encuesta.
    """
    # Obtener diagnóstico
    result = await db.execute(
        select(Diagnostic).where(Diagnostic.id == diagnostic_id)
    )
    diagnostic = result.scalar_one_or_none()
    
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    
    # Verificar que tenga respuestas
    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.diagnostic_id == diagnostic_id)
    )
    responses = result.scalars().all()
    
    if len(responses) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Se requieren al menos 5 respuestas. Actualmente: {len(responses)}"
        )
    
    # Ejecutar con Dx Pro
    adapter = DxProAdapter()
    try:
        result = await adapter.execute_diagnostic(diagnostic, responses)
        
        # Actualizar estado del diagnóstico
        diagnostic.status = "running"
        diagnostic.decision = "ALLOW"
        await db.commit()
        
        return {
            "success": True,
            "message": "Diagnóstico ejecutado con motor Dx Pro",
            "diagnostic_id": diagnostic_id,
            "pro_case_id": result.get("artifact", {}).get("case_id"),
            "trace_id": result.get("trace_id"),
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al ejecutar con Dx Pro: {str(e)}"
        )
    finally:
        await adapter.close()


@router.get("/{diagnostic_id}/pro-status")
async def get_pro_status(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene el estado de un diagnóstico ejecutado con Dx Pro
    """
    # Verificar que el diagnóstico existe
    result = await db.execute(
        select(Diagnostic).where(Diagnostic.id == diagnostic_id)
    )
    diagnostic = result.scalar_one_or_none()
    
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    
    # Aquí podrías guardar el case_id de Pro en la DB
    # Por ahora retornamos info básica
    return {
        "diagnostic_id": diagnostic_id,
        "status": diagnostic.status,
        "message": "Consulta el caso en Dx Pro usando el case_id"
    }
