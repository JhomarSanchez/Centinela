import type {
  AIProviderTest,
  AISettings,
  AISettingsUpdate,
  Check,
  DashboardSummary,
  Incident,
  IncidentContext,
  IncidentDetail,
  Service,
  ServiceCreate,
  ServiceRead,
  ServiceUpdate,
  SessionRead,
  Timeline,
} from "./types";

let csrfToken: string | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP status text when a proxy returned non-JSON.
    }
    if (response.status === 401) window.dispatchEvent(new Event("centinela:logout"));
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  async session() {
    const value = await request<SessionRead>("/auth/session");
    csrfToken = value.csrf_token;
    return value;
  },
  async login(apiKey: string) {
    const value = await request<SessionRead>("/auth/session", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    });
    csrfToken = value.csrf_token;
    return value;
  },
  async logout() {
    await request<void>("/auth/session", { method: "DELETE" });
    csrfToken = null;
  },
  dashboard: () => request<DashboardSummary>("/dashboard/summary"),
  services: () => request<Service[]>("/services"),
  service: (id: number) => request<ServiceRead>(`/services/${id}`),
  createService: (payload: ServiceCreate) =>
    request<ServiceRead>("/services", { method: "POST", body: JSON.stringify(payload) }),
  updateService: (id: number, payload: ServiceUpdate) =>
    request<ServiceRead>(`/services/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteService: (id: number) => request<void>(`/services/${id}`, { method: "DELETE" }),
  runCheck: (id: number) =>
    request<Check>(`/services/${id}/checks/run`, { method: "POST" }),
  checks: (id: number, limit = 50) => request<Check[]>(`/services/${id}/checks?limit=${limit}`),
  timeline: (id: number, hours: 24 | 168 | 720) => {
    const to = new Date();
    const from = new Date(to.getTime() - hours * 60 * 60 * 1000);
    const bucket = hours <= 24 ? "5m" : hours <= 168 ? "1h" : "1d";
    const query = new URLSearchParams({
      from: from.toISOString(),
      to: to.toISOString(),
      bucket,
    });
    return request<Timeline>(`/services/${id}/timeline?${query}`);
  },
  incidents: (active?: boolean) =>
    request<Incident[]>(`/incidents${active === undefined ? "" : `?active=${active}`}`),
  incident: (id: number) => request<IncidentDetail>(`/incidents/${id}`),
  incidentContext: (id: number) => request<IncidentContext>(`/incidents/${id}/context`),
  retryIncident: (id: number) =>
    request<Incident>(`/incidents/${id}/ai/retry`, { method: "POST" }),
  aiSettings: () => request<AISettings>("/ai/config"),
  saveAISettings: (payload: AISettingsUpdate) =>
    request<AISettings>("/ai/config", { method: "PUT", body: JSON.stringify(payload) }),
  testAISettings: () => request<AIProviderTest>("/ai/config/test", { method: "POST" }),
  deleteAICredential: () =>
    request<AISettings>("/ai/config/credential", { method: "DELETE" }),
};
