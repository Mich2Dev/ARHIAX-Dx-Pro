"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  code?: string;
  showBack?: boolean;
  backUrl?: string;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  code = "§ 01",
  showBack = false,
  backUrl,
  actions,
}: PageHeaderProps) {
  const router = useRouter();

  const handleBack = () => {
    if (backUrl) {
      router.push(backUrl);
    } else {
      router.back();
    }
  };

  return (
    <div style={{
      minHeight: '92px',
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: '24px',
      borderBottom: '1px solid rgba(23, 23, 23, 0.14)',
      paddingBottom: '20px',
      marginBottom: '28px',
    }}>
      <div style={{ flex: 1 }}>
        {showBack && (
          <button
            onClick={handleBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '12px',
              padding: '6px 12px',
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
            <ArrowLeft size={12} />
            Volver
          </button>
        )}
        <p style={{
          margin: 0,
          color: '#9b6d4d',
          fontSize: '12px',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>
          {code} · {subtitle || 'sección'}
        </p>
        <h1 style={{
          margin: '8px 0 0',
          fontFamily: 'Cormorant Garamond, Georgia, serif',
          fontWeight: 500,
          fontSize: '52px',
          lineHeight: 0.96,
          color: '#171717',
        }}>{title}</h1>
      </div>
      {actions && (
        <div style={{ flexShrink: 0 }}>
          {actions}
        </div>
      )}
    </div>
  );
}
