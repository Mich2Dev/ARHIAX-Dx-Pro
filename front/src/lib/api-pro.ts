/**
 * Cliente HTTP para el backend Pro.
 * Apunta al back-api en /pro/* — completamente separado de Standard.
 */
import axios from "axios";
import { clearAuth } from "@/lib/api/auth";

function resolveBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return "/api/backend";
  return "http://localhost:8000";
}

const BASE_URL = resolveBaseUrl();

export const apiPro = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 60_000,
});

apiPro.interceptors.request.use((config) => {
  const token = typeof window !== "undefined"
    ? (localStorage.getItem("arhiax_token") || localStorage.getItem("token"))
    : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiPro.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      clearAuth();
      window.location.href = "/login?expired=1";
    }
    const msg =
      err.response?.data?.detail ??
      err.response?.data?.message ??
      err.message ??
      "Error desconocido";
    return Promise.reject(new Error(typeof msg === "string" ? msg : JSON.stringify(msg)));
  }
);
