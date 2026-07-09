import axios from "axios";
import { clearAuth } from "./auth";

function resolveBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return "/api/backend";
  return "http://localhost:8000";
}

export const api = axios.create({
  baseURL: resolveBaseUrl(),
  headers: { "Content-Type": "application/json" },
  timeout: 60_000,
});

// Attach the stored JWT on every request so the header is always fresh,
// even if loadAuth() hasn't been called yet (e.g. on first render).
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("arhiax_token");
    if (token) {
      config.headers = config.headers ?? {};
      config.headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
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
    return Promise.reject(new Error(msg));
  }
);
