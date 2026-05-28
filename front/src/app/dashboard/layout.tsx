"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard, Plus, Bell,
  BookOpen, ShieldCheck, Settings, Building2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { key: "dashboard",  href: "/dashboard",                 icon: LayoutDashboard, label: "Panel" },
  { key: "new",        href: "/dashboard/diagnostics/new", icon: Plus, label: "Nuevo" },
  { key: "clients",    href: "/dashboard/clients",         icon: Building2, label: "Clientes" },
  { key: "reviews",    href: "/dashboard/reviews",         icon: Bell, label: "Revisiones" },
  { key: "ledger",     href: "/dashboard/ledger",          icon: BookOpen, label: "Ledger" },
  { key: "compliance", href: "/dashboard/compliance",      icon: ShieldCheck, label: "Compliance" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <AuthGuard>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500&family=Manrope:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
      
      <div style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: '268px minmax(0, 1fr)',
        background: `
          linear-gradient(90deg, rgba(23, 23, 23, 0.04) 1px, transparent 1px),
          linear-gradient(rgba(23, 23, 23, 0.035) 1px, transparent 1px),
          #f4f1ea
        `,
        backgroundSize: '72px 72px',
      }}>
        {/* Rail */}
        <aside style={{
          position: 'sticky',
          top: 0,
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          gap: '38px',
          borderRight: '1px solid rgba(23, 23, 23, 0.14)',
          padding: '28px 24px',
          background: 'rgba(244, 241, 234, 0.86)',
          backdropFilter: 'blur(18px)',
        }}>
          <Link href="/dashboard" style={{
            display: 'flex',
            gap: '14px',
            alignItems: 'center',
            color: 'inherit',
            textDecoration: 'none',
          }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #9b6d4d, #78815d)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#f4f1ea',
              fontWeight: 'bold',
              fontSize: '18px',
            }}>Dx</div>
            <span style={{
              display: 'grid',
              gap: '2px',
              borderLeft: '1px solid rgba(155, 109, 77, 0.48)',
              paddingLeft: '12px',
            }}>
              <strong style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px' }}>ARHIAX</strong>
              <em style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px', fontStyle: 'normal', color: '#706f69' }}>Standard</em>
            </span>
          </Link>
          
          <nav style={{ display: 'grid', gap: '2px' }}>
            {navItems.map(({ key, href, icon: Icon, label }) => {
              const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
              return (
                <Link
                  key={key}
                  href={href}
                  style={{
                    minHeight: '42px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    borderTop: '1px solid rgba(23, 23, 23, 0.14)',
                    color: active ? '#171717' : '#222522',
                    fontSize: '12px',
                    textDecoration: 'none',
                    fontFamily: 'IBM Plex Mono, monospace',
                    fontWeight: active ? 500 : 400,
                    background: active ? 'rgba(155, 109, 77, 0.08)' : 'transparent',
                    padding: '0 8px',
                    borderRadius: '4px',
                  }}
                >
                  <Icon size={14} />
                  {label}
                </Link>
              );
            })}
            
            {user?.role === "admin" && (
              <Link
                href="/dashboard/admin"
                style={{
                  minHeight: '42px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  borderTop: '1px solid rgba(23, 23, 23, 0.14)',
                  color: pathname.startsWith("/dashboard/admin") ? '#171717' : '#222522',
                  fontSize: '12px',
                  textDecoration: 'none',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontWeight: pathname.startsWith("/dashboard/admin") ? 500 : 400,
                  background: pathname.startsWith("/dashboard/admin") ? 'rgba(155, 109, 77, 0.08)' : 'transparent',
                  padding: '0 8px',
                  borderRadius: '4px',
                }}
              >
                <Settings size={14} />
                Admin
              </Link>
            )}
          </nav>
          
          <div style={{
            marginTop: 'auto',
            borderTop: '1px solid rgba(23, 23, 23, 0.14)',
            paddingTop: '18px',
          }}>
            {/* Switcher a Pro */}
            <Link
              href="/dashboard-pro"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                marginBottom: '12px',
                fontSize: '11px',
                fontFamily: 'IBM Plex Mono, monospace',
                color: '#706f69',
                textDecoration: 'none',
                border: '1px solid rgba(23, 23, 23, 0.1)',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#56624b'; e.currentTarget.style.color = '#56624b'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(23,23,23,0.1)'; e.currentTarget.style.color = '#706f69'; }}
            >
              <span>Dx Pro</span>
              <span style={{ fontSize: '10px', opacity: 0.5 }}>→</span>
            </Link>
            <div style={{ marginBottom: '12px' }}>
              <span style={{ display: 'block', color: '#706f69', fontSize: '12px' }}>{user?.name}</span>
              <strong style={{
                display: 'block',
                marginTop: '5px',
                color: '#56624b',
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '12px',
              }}>{user?.role}</strong>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem('token');
                window.location.href = '/login';
              }}
              style={{
                width: '100%',
                minHeight: '36px',
                padding: '8px 12px',
                background: 'transparent',
                border: '1px solid rgba(23, 23, 23, 0.14)',
                color: '#706f69',
                fontSize: '11px',
                fontFamily: 'IBM Plex Mono, monospace',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(155, 109, 77, 0.08)';
                e.currentTarget.style.borderColor = '#9b6d4d';
                e.currentTarget.style.color = '#9b6d4d';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.borderColor = 'rgba(23, 23, 23, 0.14)';
                e.currentTarget.style.color = '#706f69';
              }}
            >
              Cerrar sesión
            </button>
          </div>
        </aside>

        {/* Workspace */}
        <main style={{
          minWidth: 0,
          padding: '30px clamp(22px, 4vw, 54px) 54px',
          fontFamily: 'Manrope, sans-serif',
        }}>
          {/* Breadcrumb */}
          <div style={{
            marginBottom: '20px',
            paddingBottom: '12px',
            borderBottom: '1px solid rgba(23, 23, 23, 0.08)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Link
                href="/dashboard"
                style={{
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#706f69',
                  textDecoration: 'none',
                }}
              >
                Dashboard
              </Link>
              {pathname !== '/dashboard' && (
                <>
                  <span style={{ color: '#706f69', fontSize: '11px' }}>→</span>
                  <span style={{
                    fontSize: '11px',
                    fontFamily: 'IBM Plex Mono, monospace',
                    color: '#171717',
                    fontWeight: 500,
                  }}>
                    {pathname.includes('/diagnostics/new') ? 'Nuevo Diagnóstico' :
                     pathname.includes('/diagnostics/') ? 'Diagnóstico' :
                     pathname.includes('/clients') ? 'Clientes' :
                     pathname.includes('/reviews') ? 'Revisiones' :
                     pathname.includes('/ledger') ? 'Ledger' :
                     pathname.includes('/compliance') ? 'Compliance' :
                     pathname.includes('/admin') ? 'Admin' : 'Página'}
                  </span>
                </>
              )}
            </div>
          </div>
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
