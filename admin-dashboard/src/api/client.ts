import { useAuth } from "@rfdtech/oidc-client/react";
import { API_BASE } from "../lib/env";

type RequestResult<T> = { data: T; status: number };

export function useApi() {
  const { get_access_token } = useAuth();

  async function authHeaders(): Promise<Record<string, string>> {
    const token = await get_access_token();
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async function get<T>(path: string): Promise<RequestResult<T>> {
    const resp = await fetch(`${API_BASE}${path}`, {
      headers: await authHeaders(),
    });
    return { data: await resp.json().catch(() => ({})), status: resp.status };
  }

  async function post<T>(path: string, body?: unknown): Promise<RequestResult<T>> {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: await authHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return { data: await resp.json().catch(() => ({})), status: resp.status };
  }

  async function del<T>(path: string): Promise<RequestResult<T>> {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: await authHeaders(),
    });
    return { data: await resp.json().catch(() => ({})), status: resp.status };
  }

  return { get, post, del };
}
