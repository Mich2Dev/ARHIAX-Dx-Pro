/**
 * Auth helpers — token storage and axios interceptor.
 */

import { api } from "./client";

const TOKEN_KEY = "arhiax_token";
const USER_KEY  = "arhiax_user";

export interface AuthUser {
  user_id: string;
  name: string;
  role: string;
  email?: string;
}

export function saveAuth(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

export function loadAuth() {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(TOKEN_KEY);
  const raw   = localStorage.getItem(USER_KEY);
  if (!token || !raw) return null;
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  return { token, user: JSON.parse(raw) as AuthUser };
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  delete api.defaults.headers.common["Authorization"];
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
