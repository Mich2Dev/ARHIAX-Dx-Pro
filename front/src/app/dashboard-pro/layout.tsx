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
        gridTemplateColumns: "240px minmax(0,1fr)",
        background: "#0e0f0e",
      }}>

        {/* ── Rail oscuro ── */}
        <aside style={{
          position: "sticky", top: 0, height: "100vh",
          display: "flex", flexDirection: "column",
          borderRight: "1px solid rgba(244,241,234,0.08)",
          background: "#111311",
          overflow: "hidden",
        }}>
          {/* Brand */}
          <div style={{ padding: "24px 20px 20px", borderBottom: "1px solid rgba(244,241,234,0.06)" }}>
            <Link href="/dashboard-pro" style={{ display: "flex", gap: "12px", alignItems: "center", textDecoration: "none" }}>
              <div style={{
                width: "36px", height: "36px",
                background: "linear-gradient(135deg, #56624b, #9b6d4d)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#f4f1ea", fontFamily: "IBM Plex Mono, monospace",
                fontSize: "13px", fontWeight: 500, letterSpacing: "0.02em",
              }}>Pro</div>
              <div>
                <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "rgba(244,241,234,0.9)", fontWeight: 500, letterSpacing: "0.08em" }}>ARHIAX</p>
                <p style={{ margin: "2px 0 0", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.04em" }}>DxPro · PMEL/ATK</p>
              </div>
            </Link>
          </div>

          {/* Nav */}
          <nav style={{ flex: 1, padding: "12px 12px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {navItems.map(({ href, icon: Icon, label }) => {
              const active = pathname === href || (href !== "/dashboard-pro" && pathname.startsWith(href));
              return (
                <Link key={href} href={href} style={{
                  display: "flex", alignItems: "center", gap: "10px",
                  minHeight: "38px", padding: "0 10px",
                  fontSize: "12px", fontFamily: "IBM Plex Mono, monospace",
                  textDecoration: "none",
                  color: active ? "#f4f1ea" : "rgba(244,241,234,0.4)",
                  background: active ? "rgba(86,98,75,0.25)" : "transparent",
                  borderLeft: active ? "2px solid #56624b" : "2px solid transparent",
                  fontWeight: active ? 500 : 400,
                  transition: "all 0.15s",
                }}>
                  <Icon size={13} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Switcher de sistema */}
          <div style={{ padding: "12px", borderTop: "1px solid rgba(244,241,234,0.06)" }}>
            <Link href="/dashboard" style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 10px", fontSize: "11px",
              fontFamily: "IBM Plex Mono, monospace",
              color: "rgba(244,241,234,0.3)", textDecoration: "none",
              border: "1px solid rgba(244,241,234,0.07)",
              transition: "all 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.color = "rgba(244,241,234,0.6)"; e.currentTarget.style.borderColor = "rgba(244,241,234,0.15)"; }}
            onMouseLeave={e => { e.currentTarget.style.color = "rgba(244,241,234,0.3)"; e.currentTarget.style.borderColor = "rgba(244,241,234,0.07)"; }}
            >
              <span>Dx Standard</span>
              <span style={{ fontSize: "10px", opacity: 0.5 }}>→</span>
            </Link>
          </div>

          {/* Footer usuario */}
          <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(244,241,234,0.06)" }}>
            <p style={{ margin: 0, fontSize: "11px", color: "rgba(244,241,234,0.5)", fontFamily: "IBM Plex Mono, monospace" }}>{user?.name}</p>
            <p style={{ margin: "3px 0 8px", fontSize: "10px", color: "#56624b", fontFamily: "IBM Plex Mono, monospace" }}>operador técnico</p>
            <button
              onClick={() => { localStorage.removeItem("token"); window.location.href = "/login"; }}
              style={{
                width: "100%", padding: "7px 10px", fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                background: "transparent", border: "1px solid rgba(244,241,234,0.1)",
                color: "rgba(244,241,234,0.3)", cursor: "pointer",
                transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(139,58,58,0.5)"; e.currentTarget.style.color = "#f4a0a0"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(244,241,234,0.1)"; e.currentTarget.style.color = "rgba(244,241,234,0.3)"; }}
            >
              Cerrar sesión
            </button>
          </div>
        </aside>

        {/* ── Workspace ── */}
        <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh",
          background: `
            linear-gradient(90deg, rgba(23,23,23,0.04) 1px, transparent 1px),
            linear-gradient(rgba(23,23,23,0.035) 1px, transparent 1px),
            #f4f1ea
          `,
          backgroundSize: "72px 72px",
        }}>
          {/* Topbar */}
          <div style={{
            height: "48px", display: "flex", alignItems: "center",
            padding: "0 32px", gap: "8px",
            borderBottom: "1px solid rgba(23,23,23,0.1)",
            background: "rgba(244,241,234,0.92)",
            backdropFilter: "blur(12px)",
            position: "sticky", top: 0, zIndex: 10,
            justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Link href="/dashboard-pro" style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", textDecoration: "none" }}>
                DxPro
              </Link>
              {breadcrumb && (
                <>
                  <span style={{ color: "rgba(23,23,23,0.2)", fontSize: "11px" }}>›</span>
                  <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#171717", fontWeight: 500 }}>
                    {breadcrumb}
                  </span>
                </>
              )}
            </div>
            {/* Badge de sistema */}
            <span style={{
              fontSize: "9px", fontFamily: "IBM Plex Mono, monospace",
              color: "#56624b", letterSpacing: "0.08em",
              padding: "3px 8px",
              border: "1px solid rgba(86,98,75,0.25)",
              background: "rgba(86,98,75,0.06)",
            }}>
              PMEL/ATK · v1
            </span>
          </div>

          {/* Content */}
          <main style={{ flex: 1, padding: "32px clamp(20px,4vw,64px) 64px", fontFamily: "Manrope, sans-serif" }}>
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
