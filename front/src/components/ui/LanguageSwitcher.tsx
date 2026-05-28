"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export function LanguageSwitcher() {
  const router = useRouter();
  const [locale, setLocale] = useState("es");

  useEffect(() => {
    const saved = document.cookie.match(/locale=([^;]+)/)?.[1] ?? "es";
    setLocale(saved);
  }, []);

  function toggle() {
    const next = locale === "es" ? "en" : "es";
    document.cookie = `locale=${next}; path=/; max-age=31536000`;
    setLocale(next);
    router.refresh();
  }

  return (
    <button
      onClick={toggle}
      className="text-xs font-medium text-gray-500 hover:text-gray-800 border border-gray-200 rounded px-2 py-1 transition-colors"
    >
      {locale === "es" ? "EN" : "ES"}
    </button>
  );
}
