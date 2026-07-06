"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Plus, Building2,
  BookOpen, ShieldCheck, Bell,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { href: "/dashboard-pro",            icon: LayoutDashboard, label: "Casos" },
  { href: "/dashboard-pro/new",        icon: Plus,            label: "Nuevo caso" },
  { href: "/dashboard-pro/clients",    icon: Building2,       label: "Clientes" },
  { href: "/dashboard-pro/reviews",    icon: Bell,            label: "Revisiones" },
  { href: "/dashboard-pro/evidence",   icon: BookOpen,        label: "Evidencia" },
  { href: "/dashboard-pro/compliance", icon: ShieldCheck,     label: "Compliance" },
];

/* Paleta rail — contraste explícito entre zonas */
const C = {
  rail: "#1a1b19",
  railHeader: "#222420",
  railFooter: "#1e201c",
  border: "rgba(244, 241, 234, 0.14)",
  borderSoft: "rgba(244, 241, 234, 0.08)",
  textPrimary: "#f4f1ea",
  textSecondary: "rgba(244, 241, 234, 0.72)",
  textMuted: "rgba(244, 241, 234, 0.48)",
  textLabel: "rgba(155, 109, 77, 0.95)",
  accent: "#78815d",
  accentBright: "#9b6d4d",
  navActiveBg: "rgba(120, 129, 93, 0.22)",
  navHoverBg: "rgba(244, 241, 234, 0.06)",
};

export default function DashboardProLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();

  const breadcrumb =
    pathname.includes("/new")        ? "Nuevo caso" :
    pathname.includes("/clients")    ? "Clientes" :
    pathname.includes("/reviews")    ? "Revisiones" :
    pathname.includes("/cases/")     ? "Caso" :
    pathname.includes("/evidence")   ? "Evidencia" :
    pathname.includes("/compliance") ? "Compliance" : null;

  return (
    <AuthGuard>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Manrope:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

      <div style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "248px minmax(0, 1fr)",
        background: "#f4f1ea",
      }}>

        <aside style={{
          position: "sticky", top: 0, height: "100vh",
          display: "flex", flexDirection: "column",
          borderRight: `1px solid ${C.border}`,
          background: C.rail,
          boxShadow: "4px 0 24px rgba(23, 23, 23, 0.06)",
          overflow: "hidden",
        }}>
          {/* Brand — zona más clara */}
          <div style={{
            padding: "22px 18px 18px",
            background: C.railHeader,
            borderBottom: `1px solid ${C.border}`,
          }}>
            <Link href="/dashboard-pro" style={{ display: "flex", gap: "12px", alignItems: "center", textDecoration: "none" }}>
              <div style={{
                width: "38px", height: "38px",
                background: "linear-gradient(145deg, #78815d, #9b6d4d)",
                boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: C.textPrimary, fontFamily: "IBM Plex Mono, monospace",
                fontSize: "13px", fontWeight: 500, letterSpacing: "0.02em",
              }}>Dx</div>
              <div>
                <p style={{
                  margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                  color: C.textPrimary, fontWeight: 500, letterSpacing: "0.1em",
                }}>ARHIAX</p>
                <p style={{
                  margin: "3px 0 0", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace",
                  color: C.textSecondary, letterSpacing: "0.04em",
                }}>Diagnósticos</p>
              </div>
            </Link>
          </div>

          {/* Nav */}
          <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: "4px" }}>
            <p style={{
              margin: "0 0 8px 10px",
              fontSize: "9px",
              fontFamily: "IBM Plex Mono, monospace",
              color: C.textLabel,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
            }}>
              Menú
            </p>
            {navItems.map(({ href, icon: Icon, label }) => {
              const active = pathname === href || (href !== "/dashboard-pro" && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  style={{
                    display: "flex", alignItems: "center", gap: "10px",
                    minHeight: "40px", padding: "0 12px",
                    borderRadius: "4px",
                    fontSize: "12px", fontFamily: "IBM Plex Mono, monospace",
                    textDecoration: "none",
                    color: active ? C.textPrimary : C.textSecondary,
                    background: active ? C.navActiveBg : "transparent",
                    borderLeft: active ? `3px solid ${C.accentBright}` : "3px solid transparent",
                    fontWeight: active ? 500 : 400,
                    transition: "background 0.15s, color 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = C.navHoverBg;
                      e.currentTarget.style.color = C.textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.color = C.textSecondary;
                    }
                  }}
                >
                  <Icon size={14} strokeWidth={active ? 2.25 : 1.75} color={active ? C.accent : C.textMuted} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Usuario — tarjeta separada del nav */}
          <div style={{
            margin: "12px",
            padding: "14px",
            background: C.railFooter,
            border: `1px solid ${C.border}`,
            borderRadius: "6px",
          }}>
            <p style={{
              margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace",
              color: C.textMuted, letterSpacing: "0.08em", textTransform: "uppercase",
            }}>
              Sesión
            </p>
            <p style={{
              margin: "6px 0 0", fontSize: "12px", color: C.textPrimary,
              fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
            }}>
              {user?.name}
            </p>
            <p style={{
              margin: "2px 0 12px", fontSize: "10px", color: C.accent,
              fontFamily: "IBM Plex Mono, monospace",
            }}>
              {user?.role ?? "consultor"}
            </p>
            <button
              onClick={() => { localStorage.removeItem("token"); window.location.href = "/login"; }}
              style={{
                width: "100%", padding: "8px 10px", fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                background: "rgba(244, 241, 234, 0.04)",
                border: `1px solid ${C.border}`,
                color: C.textSecondary,
                cursor: "pointer",
                borderRadius: "4px",
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(155, 109, 77, 0.55)";
                e.currentTarget.style.color = C.textPrimary;
                e.currentTarget.style.background = "rgba(155, 109, 77, 0.12)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = C.border;
                e.currentTarget.style.color = C.textSecondary;
                e.currentTarget.style.background = "rgba(244, 241, 234, 0.04)";
              }}
            >
              Cerrar sesión
            </button>
          </div>
        </aside>

        <div style={{
          display: "flex", flexDirection: "column", minHeight: "100vh",
          background: `
            linear-gradient(90deg, rgba(23,23,23,0.04) 1px, transparent 1px),
            linear-gradient(rgba(23,23,23,0.035) 1px, transparent 1px),
            #f4f1ea
          `,
          backgroundSize: "72px 72px",
        }}>
          <div style={{
            height: "48px", display: "flex", alignItems: "center",
            padding: "0 32px", gap: "8px",
            borderBottom: "1px solid rgba(23,23,23,0.12)",
            background: "rgba(244,241,234,0.95)",
            backdropFilter: "blur(12px)",
            position: "sticky", top: 0, zIndex: 10,
            justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Link href="/dashboard-pro" style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", textDecoration: "none" }}>
                ARHIAX Dx
              </Link>
              {breadcrumb && (
                <>
                  <span style={{ color: "rgba(23,23,23,0.25)", fontSize: "11px" }}>›</span>
                  <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#171717", fontWeight: 500 }}>
                    {breadcrumb}
                  </span>
                </>
              )}
            </div>
            <span style={{
              fontSize: "9px", fontFamily: "IBM Plex Mono, monospace",
              color: "#56624b", letterSpacing: "0.08em",
              padding: "4px 10px",
              border: "1px solid rgba(86,98,75,0.3)",
              background: "rgba(86,98,75,0.08)",
              borderRadius: "3px",
            }}>
              Gobernanza PMEL/ATK
            </span>
          </div>

          <main style={{ flex: 1, padding: "32px clamp(20px,4vw,64px) 64px", fontFamily: "Manrope, sans-serif" }}>
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
