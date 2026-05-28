"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { LanguageSwitcher } from "@/components/ui/LanguageSwitcher";

export function Header() {
  const { user, logout } = useAuth();

  const { data } = useQuery({
    queryKey: ["pending-reviews-count"],
    queryFn: () => api.get("/v2/reviews/pending/count").then((r) => r.data),
    refetchInterval: 15000,
    enabled: !!user,
  });

  const count: number = data?.count ?? 0;

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      {/* Left — breadcrumb placeholder */}
      <div />

      {/* Right */}
      <div className="flex items-center gap-4">
        {/* Alerts bell — links to /dashboard/reviews */}
        <a href="/dashboard/reviews" className="relative text-gray-400 hover:text-gray-700 transition-colors">
          <Bell size={18} />
          {count > 0 && (
            <span className="absolute -top-1 -right-1 bg-amber-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </a>

        <LanguageSwitcher />

        {/* User */}
        {user && (
          <div className="flex items-center gap-2 pl-3 border-l border-gray-100">
            <div className="w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center text-white text-xs font-bold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-sm font-medium text-gray-700 hidden sm:block">
              {user.name}
            </span>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-red-500 transition-colors ml-1"
              title="Cerrar sesión"
            >
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
