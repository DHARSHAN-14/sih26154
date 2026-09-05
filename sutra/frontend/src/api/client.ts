/**
 * api/client.ts
 * Axios instance + typed API namespaces for SUTRA backend.
 * All calls go through this file — configured via VITE_API_BASE_URL.
 */
import axios, { type AxiosProgressEvent } from "axios";
import type {
  Source,
  SourceOfTruth,
  Job,
  Artifact,
  OutputConfig,
  SessionVersion,
  Session,
  SecurityClassification,
} from "@/types";

/**
 * Resolves the API base URL from environment variables.
 * Prioritizes VITE_API_BASE_URL, then VITE_API_URL, defaulting to "/api".
 */
export function getApiBaseUrl(): string {
  const url =
    import.meta.env?.VITE_API_BASE_URL ||
    import.meta.env?.VITE_API_URL ||
    "/api";
  return url.replace(/\/+$/, "");
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Attach operator token on every request
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("sutra_token");
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  return config;
});

// Normalize errors (do not swallow)
api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

// ── Sources ───────────────────────────────────────────────────────────────────
export const sourcesApi = {
  /** Upload a file (multipart). `onProgress` receives 0-100. */
  upload(file: File, onProgress?: (pct: number) => void) {
    const form = new FormData();
    form.append("file", file);
    return api.post<Source>("/sources/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e: AxiosProgressEvent) => {
        if (onProgress && e.total)
          onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
  },
  /** Ingest from a public URL */
  uploadUrl: (url: string) =>
    api.post<Source>("/sources/url", { url }),
  /** Ingest raw text */
  uploadText: (text: string, name: string) =>
    api.post<Source>("/sources/text", { text, name }),
  /** Fetch a source by id */
  get: (id: string) => api.get<Source>(`/sources/${id}`),
  /** Poll or check source processing status */
  getStatus: (id: string) =>
    api.get<{
      id: string;
      status: "idle" | "uploading" | "processing" | "ready" | "failed";
      progress?: number;
      message?: string;
      error?: string;
    }>(`/sources/${id}/status`),
  /** Preview extracted content / text */
  getPreview: (id: string) =>
    api.get<{ id: string; text?: string; previewUrl?: string; pageCount?: number }>(
      `/sources/${id}/preview`
    ),
};

// ── Sessions ──────────────────────────────────────────────────────────────────
export const sessionsApi = {
  create: (params?: { operatorId?: string; classification?: SecurityClassification }) =>
    api.post<{ id: string; operatorId?: string; classification?: SecurityClassification }>(
      "/sessions",
      params ?? {}
    ),
  get: (id: string) => api.get<Session>(`/sessions/${id}`),
};

// ── Source of Truth ───────────────────────────────────────────────────────────
export const sotApi = {
  /** Fetch the built SOT for a source */
  get: (sourceId: string) =>
    api.get<SourceOfTruth>(`/sot/${sourceId}`),
  /** Fetch SOT by session ID */
  getBySession: (sessionId: string) =>
    api.get<SourceOfTruth>(`/sessions/${sessionId}/sot`),
  /** Lock the SOT (immutable after this) */
  lock: (sotId: string) =>
    api.post<SourceOfTruth>(`/sot/${sotId}/lock`),
  /** Unlock the SOT (operator override) */
  unlock: (sotId: string) =>
    api.post<SourceOfTruth>(`/sot/${sotId}/unlock`),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  /** Create and queue a new pipeline job */
  create: (
    sessionId: string,
    outputConfigIds: string[],
    options?: { configs?: OutputConfig[]; parameters?: Record<string, unknown> }
  ) =>
    api.post<Job>("/jobs", { sessionId, outputConfigIds, ...(options ?? {}) }),
  /** Poll job status */
  get: (id: string) => api.get<Job>(`/jobs/${id}`),
  /** Cancel a running job */
  cancel: (id: string) => api.post<void>(`/jobs/${id}/cancel`),
  /**
   * Open an SSE stream for live stage updates.
   * Caller is responsible for closing the EventSource.
   */
  stream: (id: string): EventSource =>
    new EventSource(`${getApiBaseUrl()}/jobs/${id}/stream`),
};

// ── Stream (alternative SSE route) ────────────────────────────────────────────
export const streamApi = {
  /** Direct connection to /stream/:jobId SSE endpoint */
  connect: (jobId: string): EventSource =>
    new EventSource(`${getApiBaseUrl()}/stream/${jobId}`),
};

// ── Outputs / Artifacts ───────────────────────────────────────────────────────
export const outputsApi = {
  /** List all artifacts for a completed job */
  list: (jobId: string) =>
    api.get<Artifact[]>(`/outputs/${jobId}`),
  /** List all artifacts for a session */
  listBySession: (sessionId: string) =>
    api.get<Artifact[]>(`/sessions/${sessionId}/outputs`),
  /** Fetch a single artifact with full validation + provenance */
  get: (id: string) => api.get<Artifact>(`/outputs/${id}`),
  /** Direct download URL (used as `<a href>` or window.open) */
  downloadUrl: (id: string) => `${getApiBaseUrl()}/outputs/${id}/download`,
  /** Download artifact as blob and trigger browser save */
  async downloadBlob(id: string, filename?: string): Promise<void> {
    const res = await api.get(`/outputs/${id}/download`, {
      responseType: "blob",
    });
    const blob = new Blob([res.data]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `artifact-${id}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
  /** Approve an artifact */
  approve: (id: string) =>
    api.post<void>(`/outputs/${id}/approve`),
  /** Reject an artifact with a reason */
  reject: (id: string, reason: string) =>
    api.post<void>(`/outputs/${id}/reject`, { reason }),
};

// ── Output Configs ────────────────────────────────────────────────────────────
export const configsApi = {
  list: (sessionId: string) =>
    api.get<OutputConfig[]>(`/sessions/${sessionId}/configs`),
  create: (sessionId: string, config: OutputConfig) =>
    api.post<OutputConfig>(`/sessions/${sessionId}/configs`, config),
  update: (sessionId: string, id: string, updates: Partial<OutputConfig>) =>
    api.patch<OutputConfig>(`/sessions/${sessionId}/configs/${id}`, updates),
  remove: (sessionId: string, id: string) =>
    api.delete<void>(`/sessions/${sessionId}/configs/${id}`),
};

// ── Versions ──────────────────────────────────────────────────────────────────
export const versionsApi = {
  list: (sessionId: string) =>
    api.get<SessionVersion[]>(`/versions/${sessionId}`),
  get: (sessionId: string, versionId: string) =>
    api.get<SessionVersion>(`/versions/${sessionId}/${versionId}`),
  restore: (sessionId: string, versionId: string) =>
    api.post<SessionVersion>(`/versions/${sessionId}/${versionId}/restore`),
};
