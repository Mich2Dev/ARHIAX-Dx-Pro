"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Spinner } from "@/components/ui/Spinner";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<"standard" | "pro" | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedVersion) {
      setError("Selecciona una versión primero");
      return;
    }

    setError("");
    setLoading(true);
    try {
      await login(email, password);
      if (selectedVersion === "pro") {
        router.push("/dashboard-pro");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message ?? "Credenciales inválidas");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Manrope:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: `
          linear-gradient(90deg, rgba(23, 23, 23, 0.04) 1px, transparent 1px),
          linear-gradient(rgba(23, 23, 23, 0.035) 1px, transparent 1px),
          #f4f1ea
        `,
        backgroundSize: '72px 72px',
      }}>
        <div style={{ width: '100%', maxWidth: '1200px' }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #9b6d4d, #78815d)',
              marginBottom: '24px',
              boxShadow: '0 4px 12px rgba(155, 109, 77, 0.2)',
            }}>
              <span style={{
                color: '#f4f1ea',
                fontSize: '28px',
                fontWeight: 'bold',
                fontFamily: 'IBM Plex Mono, monospace',
              }}>Dx</span>
            </div>
            <h1 style={{
              margin: '0 0 12px',
              fontFamily: 'Cormorant Garamond, Georgia, serif',
              fontWeight: 500,
              fontSize: '56px',
              lineHeight: 0.96,
              color: '#171717',
            }}>ARHIAX Dx</h1>
            <p style={{
              margin: 0,
              fontSize: '14px',
              color: '#706f69',
              fontFamily: 'IBM Plex Mono, monospace',
            }}>Plataforma de Diagnósticos Organizacionales</p>
          </div>

          {/* Version selector or Login form */}
          {!selectedVersion ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1px',
              maxWidth: '900px',
              margin: '0 auto',
              background: 'rgba(23, 23, 23, 0.14)',
            }}>
              {/* Standard */}
              <button
                onClick={() => setSelectedVersion("standard")}
                style={{
                  background: 'rgba(244, 241, 234, 0.96)',
                  padding: '32px',
                  textAlign: 'left',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(244, 241, 234, 1)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(244, 241, 234, 0.96)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div style={{
                  display: 'inline-block',
                  padding: '4px 10px',
                  background: 'rgba(36, 60, 79, 0.1)',
                  border: '1px solid rgba(36, 60, 79, 0.3)',
                  fontSize: '10px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontWeight: 500,
                  color: '#243c4f',
                  marginBottom: '16px',
                }}>STANDARD</div>
                
                <h3 style={{
                  margin: '0 0 8px',
                  fontFamily: 'Cormorant Garamond, Georgia, serif',
                  fontSize: '28px',
                  fontWeight: 500,
                  color: '#171717',
                }}>Dx Standard</h3>
                <p style={{
                  margin: '0 0 20px',
                  fontSize: '13px',
                  color: '#706f69',
                }}>Versión completa con todas las funcionalidades</p>

                <div style={{ display: 'grid', gap: '8px', marginBottom: '20px' }}>
                  {[
                    '18 agentes especializados',
                    'Pipeline completo de diagnóstico',
                    'Sistema de encuestas multi-rater',
                    'Reportes PDF/DOCX',
                  ].map((feature) => (
                    <div key={feature} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '4px',
                        height: '4px',
                        borderRadius: '50%',
                        background: '#243c4f',
                      }} />
                      <span style={{
                        fontSize: '12px',
                        color: '#706f69',
                        fontFamily: 'IBM Plex Mono, monospace',
                      }}>{feature}</span>
                    </div>
                  ))}
                </div>

                <div style={{
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#243c4f',
                  fontWeight: 500,
                }}>Seleccionar →</div>
              </button>

              {/* Pro — redirige al frontend standalone */}
              <button
                onClick={() => setSelectedVersion("pro")}
                style={{
                  background: '#1a1c1a',
                  padding: '32px',
                  textAlign: 'left',
                  position: 'relative',
                  cursor: 'pointer',
                  border: 'none',
                  width: '100%',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#222422'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#1a1c1a'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                {/* Badge "Integrado" */}
                <div style={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                  padding: '3px 10px',
                  background: 'rgba(120, 129, 93, 0.18)',
                  border: '1px solid rgba(120, 129, 93, 0.35)',
                  fontSize: '9px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontWeight: 500,
                  color: '#78815d',
                  letterSpacing: '0.08em',
                }}>INTEGRADO</div>

                <div style={{
                  display: 'inline-block',
                  padding: '4px 10px',
                  background: 'linear-gradient(135deg, #9b6d4d, #78815d)',
                  fontSize: '10px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontWeight: 500,
                  color: '#f4f1ea',
                  marginBottom: '16px',
                }}>PRO</div>

                <h3 style={{
                  margin: '0 0 8px',
                  fontFamily: 'Cormorant Garamond, Georgia, serif',
                  fontSize: '28px',
                  fontWeight: 500,
                  color: '#f4f1ea',
                }}>Dx Pro</h3>
                <p style={{
                  margin: '0 0 20px',
                  fontSize: '13px',
                  color: 'rgba(244, 241, 234, 0.7)',
                }}>Runtime avanzado con gobernanza PMEL/ATK</p>

                <div style={{ display: 'grid', gap: '8px', marginBottom: '20px' }}>
                  {[
                    'Fusion cycle inteligente',
                    'Evidence ledger HMAC',
                    '92 tests automatizados',
                    'Sin dependencias externas',
                  ].map((feature) => (
                    <div key={feature} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '4px',
                        height: '4px',
                        borderRadius: '50%',
                        background: '#78815d',
                      }} />
                      <span style={{
                        fontSize: '12px',
                        color: 'rgba(244, 241, 234, 0.7)',
                        fontFamily: 'IBM Plex Mono, monospace',
                      }}>{feature}</span>
                    </div>
                  ))}
                </div>

                <div style={{
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#78815d',
                  fontWeight: 500,
                }}>Seleccionar →</div>
              </button>
            </div>
          ) : (
            /* Login form */
            <div style={{ maxWidth: '420px', margin: '0 auto' }}>
              <button
                onClick={() => setSelectedVersion(null)}
                style={{
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#706f69',
                  marginBottom: '24px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                ← Cambiar versión
              </button>

              <div style={{
                background: 'rgba(244, 241, 234, 0.96)',
                border: '1px solid rgba(23, 23, 23, 0.14)',
                padding: '32px',
              }}>
                <div style={{ marginBottom: '24px' }}>
                  <div style={{
                    display: 'inline-block',
                    padding: '4px 10px',
                    background: selectedVersion === "standard" 
                      ? 'rgba(36, 60, 79, 0.1)' 
                      : 'linear-gradient(135deg, #9b6d4d, #78815d)',
                    border: selectedVersion === "standard" ? '1px solid rgba(36, 60, 79, 0.3)' : 'none',
                    fontSize: '10px',
                    fontFamily: 'IBM Plex Mono, monospace',
                    fontWeight: 500,
                    color: selectedVersion === "standard" ? '#243c4f' : '#f4f1ea',
                    marginBottom: '12px',
                  }}>
                    {selectedVersion === "standard" ? "STANDARD" : "PRO"}
                  </div>
                  <h2 style={{
                    margin: '0 0 4px',
                    fontFamily: 'Cormorant Garamond, Georgia, serif',
                    fontSize: '32px',
                    fontWeight: 500,
                    color: '#171717',
                  }}>
                    {selectedVersion === "standard" ? "Dx Standard" : "Dx Pro"}
                  </h2>
                  <p style={{
                    margin: 0,
                    fontSize: '12px',
                    color: '#706f69',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>Iniciar sesión</p>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '20px' }}>
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '11px',
                      fontFamily: 'IBM Plex Mono, monospace',
                      color: '#706f69',
                      marginBottom: '8px',
                    }}>
                      Correo electrónico
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '12px',
                        background: '#f4f1ea',
                        border: '1px solid rgba(23, 23, 23, 0.14)',
                        color: '#171717',
                        fontSize: '13px',
                        fontFamily: 'Manrope, sans-serif',
                        outline: 'none',
                      }}
                      placeholder="admin@sinergia.co"
                      required
                      autoFocus
                      onFocus={(e) => e.target.style.borderColor = '#9b6d4d'}
                      onBlur={(e) => e.target.style.borderColor = 'rgba(23, 23, 23, 0.14)'}
                    />
                  </div>

                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '11px',
                      fontFamily: 'IBM Plex Mono, monospace',
                      color: '#706f69',
                      marginBottom: '8px',
                    }}>
                      Contraseña
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '12px',
                        background: '#f4f1ea',
                        border: '1px solid rgba(23, 23, 23, 0.14)',
                        color: '#171717',
                        fontSize: '13px',
                        fontFamily: 'Manrope, sans-serif',
                        outline: 'none',
                      }}
                      placeholder="••••••••"
                      required
                      onFocus={(e) => e.target.style.borderColor = '#9b6d4d'}
                      onBlur={(e) => e.target.style.borderColor = 'rgba(23, 23, 23, 0.14)'}
                    />
                  </div>

                  {error && (
                    <div style={{
                      borderLeft: '3px solid #9b6d4d',
                      padding: '12px 14px',
                      background: 'rgba(155, 109, 77, 0.1)',
                      color: '#6b3f2f',
                      fontSize: '12px',
                    }}>
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    style={{
                      width: '100%',
                      minHeight: '42px',
                      padding: '12px',
                      background: loading ? 'rgba(23, 23, 23, 0.5)' : '#171717',
                      border: '1px solid #171717',
                      color: '#f4f1ea',
                      fontSize: '12px',
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontWeight: 500,
                      cursor: loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                    }}
                  >
                    {loading ? (
                      <>
                        <Spinner className="w-4 h-4" />
                        Ingresando...
                      </>
                    ) : (
                      <>
                        Ingresar →
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* Footer */}
          <div style={{ textAlign: 'center', marginTop: '48px' }}>
            <p style={{
              margin: 0,
              fontSize: '12px',
              color: '#706f69',
              fontFamily: 'IBM Plex Mono, monospace',
            }}>
              Sinergia Consulting Group S.A.S.
            </p>
            <p style={{
              margin: '4px 0 0',
              fontSize: '10px',
              color: 'rgba(112, 111, 105, 0.6)',
              fontFamily: 'IBM Plex Mono, monospace',
            }}>
              Dx Platform v5.1 · Dual Runtime
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
