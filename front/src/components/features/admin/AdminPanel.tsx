"use client";

// Imports from React and React Query
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

// Imports from lib API and utilities
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

// Imports from UI components
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";

// Imports from context
import { useAuth } from "@/context/AuthContext";

// Imports from icons
import { Plus, Trash2, Edit2, X, Check } from "lucide-react";

// Imports from config constants
import { ROLE_LABELS, ROLE_COLORS } from "@/config/constants";

export function AdminPanel() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get("/v2/users").then(r => r.data),
  });

  const deleteUser = useMutation({
    mutationFn: (id: string) => api.delete(`/v2/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const users = data?.items ?? [];

  if (me?.role !== "admin") {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <p className="text-gray-400">Solo los administradores pueden acceder a este panel.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Administración</h1>
          <p className="text-sm text-gray-500 mt-1">Gestión de usuarios del equipo.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} /> Nuevo usuario
        </button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ["users"] }); }}
        />
      )}

      {/* Users table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="px-6 py-3 font-semibold">Usuario</th>
                <th className="px-6 py-3 font-semibold">Email</th>
                <th className="px-6 py-3 font-semibold">Rol</th>
                <th className="px-6 py-3 font-semibold">Creado</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {users.map((u: any) => (
                <tr key={u.id} className="hover:bg-gray-50 group">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center text-xs font-bold">
                        {u.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-900">{u.name}</span>
                      {u.id === me?.user_id && (
                        <span className="text-xs text-gray-400">(tú)</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-3.5 text-gray-500">{u.email}</td>
                  <td className="px-6 py-3.5">
                    <Badge variant={ROLE_COLORS[u.role] ?? "gray"}>
                      {ROLE_LABELS[u.role] ?? u.role}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-gray-400 text-xs">{formatDate(u.created_at)}</td>
                  <td className="px-6 py-3.5">
                    {u.id !== me?.user_id && (
                      <button
                        onClick={() => {
                          if (confirm(`¿Eliminar a ${u.name}?`)) deleteUser.mutate(u.id);
                        }}
                        className="text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* BBR Metrics */}
      <BBRMetrics />
    </div>
  );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "operator" });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: () => api.post("/v2/users", form).then(r => r.data),
    onSuccess: onCreated,
    onError: (e: any) => setError(e.message),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-gray-900">Nuevo usuario</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
        </div>

        <div className="space-y-3">
          <Field label="Nombre completo">
            <input value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} className="input" placeholder="Juan Pérez" />
          </Field>
          <Field label="Correo electrónico">
            <input type="email" value={form.email} onChange={e => setForm(p => ({...p, email: e.target.value}))} className="input" placeholder="juan@sinergia.co" />
          </Field>
          <Field label="Contraseña">
            <input type="password" value={form.password} onChange={e => setForm(p => ({...p, password: e.target.value}))} className="input" placeholder="Mínimo 8 caracteres" />
          </Field>
          <Field label="Rol">
            <select value={form.role} onChange={e => setForm(p => ({...p, role: e.target.value}))} className="input">
              <option value="operator">Consultor</option>
              <option value="reviewer">Revisor</option>
              <option value="admin">Administrador</option>
            </select>
          </Field>
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
          <button
            onClick={() => create.mutate()}
            disabled={create.isPending || !form.email || !form.name || !form.password}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {create.isPending ? <Spinner className="w-4 h-4" /> : <Check size={16} />}
            Crear usuario
          </button>
        </div>
      </div>
    </div>
  );
}

function BBRMetrics() {
  const { data } = useQuery({
    queryKey: ["bbr-stats"],
    queryFn: () => api.get("/v2/diagnostics/stats").then(r => r.data),
    refetchInterval: 30000,
  });

  const metrics = [
    { label: "Completados",     value: data?.completed ?? 0,       color: "text-green-600" },
    { label: "En ejecución",    value: data?.running ?? 0,         color: "text-blue-600" },
    { label: "En revisión",     value: data?.awaiting_review ?? 0, color: "text-orange-600" },
    { label: "Denegados",       value: data?.denied ?? 0,          color: "text-red-600" },
    { label: "Pendientes",      value: data?.pending ?? 0,         color: "text-gray-600" },
  ];

  const total = metrics.reduce((a, m) => a + (m.value as number), 0);
  const escalation_ratio = total > 0
    ? ((data?.awaiting_review ?? 0) / total).toFixed(2)
    : "0.00";
  const deny_ratio = total > 0
    ? ((data?.denied ?? 0) / total).toFixed(2)
    : "0.00";

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
      <h3 className="font-semibold text-gray-800 mb-4">Métricas BBR (Behavioral Baseline)</h3>
      <div className="grid grid-cols-5 gap-3 mb-4">
        {metrics.map(m => (
          <div key={m.label} className="text-center">
            <p className={`text-2xl font-black ${m.color}`}>{m.value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>
      <div className="border-t border-gray-100 pt-3 grid grid-cols-3 gap-3 text-center text-sm">
        <div>
          <p className="font-semibold text-gray-700">{total}</p>
          <p className="text-xs text-gray-400">Total diagnósticos</p>
        </div>
        <div>
          <p className={`font-semibold ${parseFloat(escalation_ratio) > 0.10 ? "text-orange-600" : "text-green-600"}`}>
            {escalation_ratio}
          </p>
          <p className="text-xs text-gray-400">Ratio escalado (máx 0.10)</p>
        </div>
        <div>
          <p className={`font-semibold ${parseFloat(deny_ratio) > 0.05 ? "text-red-600" : "text-green-600"}`}>
            {deny_ratio}
          </p>
          <p className="text-xs text-gray-400">Ratio denegado (máx 0.05)</p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
    </div>
  );
}
