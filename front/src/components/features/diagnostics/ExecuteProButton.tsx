/**
 * Botón para ejecutar diagnóstico con motor Dx Pro
 * Importa desde: @/components/features/diagnostics/ExecuteProButton
 */

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Zap } from "lucide-react";

interface ExecuteProButtonProps {
  diagnosticId: string;
  onSuccess?: () => void;
}

export function ExecuteProButton({ diagnosticId, onSuccess }: ExecuteProButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleExecute() {
    setLoading(true);
    setError("");
    
    try {
      const response = await api.post(`/v2/diagnostics/${diagnosticId}/execute-pro`);
      
      if (response.data.success) {
        alert(`✅ Diagnóstico ejecutado con Dx Pro\n\nCase ID: ${response.data.pro_case_id}\nTrace ID: ${response.data.trace_id}`);
        onSuccess?.();
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al ejecutar con Dx Pro";
      setError(message);
      alert(`❌ ${message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleExecute}
      disabled={loading}
      className="flex items-center gap-1.5 text-xs bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-3 py-1.5 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
      title="Ejecutar con motor Dx Pro (Fusion Cycle)"
    >
      {loading ? (
        <>
          <Spinner className="w-3 h-3" />
          Ejecutando...
        </>
      ) : (
        <>
          <Zap size={12} />
          Pro
        </>
      )}
    </button>
  );
}
