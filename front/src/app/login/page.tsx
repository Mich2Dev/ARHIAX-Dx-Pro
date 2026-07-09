"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Spinner } from "@/components/ui/Spinner";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("expired") === "1";
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard-pro");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Credenciales inválidas";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Manrope:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
      `}</style>

      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          background: `
            linear-gradient(90deg, rgba(23, 23, 23, 0.04) 1px, transparent 1px),
            linear-gradient(rgba(23, 23, 23, 0.035) 1px, transparent 1px),
            #f4f1ea
          `,
          backgroundSize: "72px 72px",
        }}
      >
        <div style={{ width: "100%", maxWidth: "440px" }}>
          <div style={{ textAlign: "center", marginBottom: "40px" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "64px",
                height: "64px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, #9b6d4d, #78815d)",
                marginBottom: "24px",
                boxShadow: "0 4px 12px rgba(155, 109, 77, 0.2)",
              }}
            >
              <span
                style={{
                  color: "#f4f1ea",
                  fontSize: "28px",
                  fontWeight: "bold",
                  fontFamily: "IBM Plex Mono, monospace",
                }}
              >
                Dx
              </span>
            </div>
            <h1
              style={{
                margin: "0 0 12px",
                fontFamily: "Cormorant Garamond, Georgia, serif",
                fontWeight: 500,
                fontSize: "48px",
                lineHeight: 0.96,
                color: "#171717",
              }}
            >
              ARHIAX Dx
            </h1>
            <p
              style={{
                margin: 0,
                fontSize: "14px",
                color: "#706f69",
                fontFamily: "IBM Plex Mono, monospace",
              }}
            >
              Diagnósticos organizacionales gobernados
            </p>
          </div>

          <div
            style={{
              background: "rgba(244, 241, 234, 0.96)",
              border: "1px solid rgba(23, 23, 23, 0.14)",
              padding: "32px",
            }}
          >
            <p
              style={{
                margin: "0 0 24px",
                fontSize: "12px",
                color: "#706f69",
                fontFamily: "IBM Plex Mono, monospace",
              }}
            >
              Iniciar sesión
            </p>

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "20px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "IBM Plex Mono, monospace",
                    color: "#706f69",
                    marginBottom: "8px",
                  }}
                >
                  Correo electrónico
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: "#f4f1ea",
                    border: "1px solid rgba(23, 23, 23, 0.14)",
                    color: "#171717",
                    fontSize: "13px",
                    fontFamily: "Manrope, sans-serif",
                    outline: "none",
                  }}
                  placeholder="admin@arhiax.com"
                  required
                  autoFocus
                  onFocus={(e) => {
                    e.target.style.borderColor = "#9b6d4d";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(23, 23, 23, 0.14)";
                  }}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "IBM Plex Mono, monospace",
                    color: "#706f69",
                    marginBottom: "8px",
                  }}
                >
                  Contraseña
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: "#f4f1ea",
                    border: "1px solid rgba(23, 23, 23, 0.14)",
                    color: "#171717",
                    fontSize: "13px",
                    fontFamily: "Manrope, sans-serif",
                    outline: "none",
                  }}
                  placeholder="••••••••"
                  required
                  onFocus={(e) => {
                    e.target.style.borderColor = "#9b6d4d";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(23, 23, 23, 0.14)";
                  }}
                />
              </div>

              {sessionExpired && !error && (
                <div
                  style={{
                    borderLeft: "3px solid #56624b",
                    padding: "12px 14px",
                    background: "rgba(86, 98, 75, 0.1)",
                    color: "#3d4638",
                    fontSize: "12px",
                  }}
                >
                  Tu sesión expiró. Inicia sesión de nuevo para crear un caso.
                </div>
              )}

              {error && (
                <div
                  style={{
                    borderLeft: "3px solid #9b6d4d",
                    padding: "12px 14px",
                    background: "rgba(155, 109, 77, 0.1)",
                    color: "#6b3f2f",
                    fontSize: "12px",
                  }}
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
                  minHeight: "42px",
                  padding: "12px",
                  background: loading ? "rgba(23, 23, 23, 0.5)" : "#171717",
                  border: "1px solid #171717",
                  color: "#f4f1ea",
                  fontSize: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontWeight: 500,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
              >
                {loading ? (
                  <>
                    <Spinner className="w-4 h-4" />
                    Ingresando...
                  </>
                ) : (
                  "Ingresar →"
                )}
              </button>
            </form>
          </div>

          <div style={{ textAlign: "center", marginTop: "40px" }}>
            <p
              style={{
                margin: 0,
                fontSize: "12px",
                color: "#706f69",
                fontFamily: "IBM Plex Mono, monospace",
              }}
            >
              Sinergia Consulting Group S.A.S.
            </p>
            <p
              style={{
                margin: "4px 0 0",
                fontSize: "10px",
                color: "rgba(112, 111, 105, 0.6)",
                fontFamily: "IBM Plex Mono, monospace",
              }}
            >
              ARHIAX Dx · Plataforma unificada
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
