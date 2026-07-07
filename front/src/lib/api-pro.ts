/**
 * Cliente HTTP para el backend Pro.
 * Apunta al back-api en /pro/* — completamente separado de Standard.
 */
import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiPro = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
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
    const msg =
      err.response?.data?.detail ??
      err.response?.data?.message ??
      err.message ??
      "Error desconocido";
    return Promise.reject(new Error(typeof msg === "string" ? msg : JSON.stringify(msg)));
  }
);
