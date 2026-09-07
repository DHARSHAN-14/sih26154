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

// Attach operator token and session ID on every request
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("sutra_token");
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  const sid = sessionStorage.getItem("sutra_session_id");
  if (sid) {
    config.headers["X-Session-ID"] = sid;
  }
  // Let the browser/Axios compute the multipart boundary delimiter automatically
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

// Normalize errors (do not swallow, extract backend detail)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.data) {
      const detail = err.response.data.detail || err.response.data.message || err.response.data.error;
      if (detail && typeof detail === "string") {
        err.message = detail;
      }
    }
    return Promise.reject(err);
  }
);

// ── Sources ───────────────────────────────────────────────────────────────────
export const sourcesApi = {
  /** Upload a file (multipart). `onProgress` receives 0-100. */
  upload(file: File, onProgress?: (pct: number) => void, sessionId?: string) {
    const form = new FormData();
    form.append("file", file);
    const sid = sessionId || sessionStorage.getItem("sutra_session_id") || "";
    const endpoint = sid ? `/sources/upload?session_id=${encodeURIComponent(sid)}` : "/sources/upload";
    return api.post<Source>(endpoint, form, {
      onUploadProgress: (e: AxiosProgressEvent) => {
        if (onProgress && e.total)
          onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
  },
  /** Ingest from a public URL */
  uploadUrl: (url: string, sessionId?: string) => {
    const sid = sessionId || sessionStorage.getItem("sutra_session_id") || "";
    const endpoint = sid ? `/sources/url?session_id=${encodeURIComponent(sid)}` : "/sources/url";
    return api.post<Source>(endpoint, { url });
  },
  /** Ingest raw text */
  uploadText: (text: string, name: string, sessionId?: string) => {
    const sid = sessionId || sessionStorage.getItem("sutra_session_id") || "";
    const endpoint = sid ? `/sources/text?session_id=${encodeURIComponent(sid)}` : "/sources/text";
    return api.post<Source>(endpoint, { text, name });
  },
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

// ── RAG / Retrieval ───────────────────────────────────────────────────────────
export interface RetrievalResult {
  chunk_id: string;
  text: string;
  page: number;
  paragraph: number;
  doc_id: string;
  dense_score: number;
  sparse_score: number;
  rrf_score: number;
  rerank_score: number;
  matched_terms: string[];
}

export interface RetrievalStatus {
  session_id: string;
  indexed_chunks: number;
  route: string;
  route_reason: string;
  token_count: number;
  token_threshold: number;
  hybrid_ready: boolean;
  components: Record<string, string>;
}

export interface RetrievalQueryResponse {
  session_id: string;
  query: string;
  route: string;
  total_indexed_chunks: number;
  results: RetrievalResult[];
}

export const retrievalApi = {
  query: (sessionId: string, query: string, topK: number = 5) =>
    api.post<RetrievalQueryResponse>(`/sessions/${sessionId}/retrieval/query`, { query, top_k: topK }),
  getStatus: (sessionId: string) =>
    api.get<RetrievalStatus>(`/sessions/${sessionId}/retrieval/status`),
};

