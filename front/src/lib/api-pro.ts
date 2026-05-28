/**
 * Cliente HTTP para el backend Pro.
 * Apunta al back-api en /pro/* — completamente separado de Standard.
 */
import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiPro = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Inyectar token JWT en cada request
apiPro.interceptors.request.use((config) => {
  const token = typeof window !== "undefined"
    ? (localStorage.getItem("arhiax_token") || localStorage.getItem("token"))
    : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
