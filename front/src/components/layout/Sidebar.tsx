"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard, Plus, Bell,
  BookOpen, ShieldCheck, Settings, Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { key: "dashboard",  href: "/dashboard",                 icon: LayoutDashboard },
  { key: "new",        href: "/dashboard/diagnostics/new", icon: Plus },
  { key: "clients",    href: "/dashboard/clients",         icon: Building2 },
  { key: "reviews",    href: "/dashboard/reviews",         icon: Bell },
  { key: "ledger",     href: "/dashboard/ledger",          icon: BookOpen },
  { key: "compliance", href: "/dashboard/compliance",      icon: ShieldCheck },
];

export function Sidebar() {
  const pathname  = usePathname();
  const t         = useTranslations("nav");
  const { user }  = useAuth();

  return (
    <aside className="w-56 bg-navy-900 flex flex-col shrink-0" style={{ backgroundColor: "#071628" }}>
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <span className="text-white font-bold text-lg tracking-tight">ARHIAX Dx</span>
        <span className="block text-white/40 text-xs mt-0.5">v5.1 · Governed</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ key, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={key}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-brand-500 text-white"
                  : "text-white/60 hover:text-white hover:bg-white/10"
              )}
            >
              <Icon size={16} />
              {t(key as any)}
            </Link>
          );
        })}

        {/* Admin — solo para admins */}
        {user?.role === "admin" && (
          <Link
            href="/dashboard/admin"
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith("/dashboard/admin")
                ? "bg-brand-500 text-white"
                : "text-white/60 hover:text-white hover:bg-white/10"
            )}
          >
            <Settings size={16} />
            Administración
          </Link>
        )}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/10">
        <span className="text-white/30 text-xs">Sinergia Consulting</span>
      </div>
    </aside>
  );
}
