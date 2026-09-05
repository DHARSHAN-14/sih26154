/**
 * store/session.ts
 * Zustand store — single source of client-side truth.
 * All pages read from this store and dispatch actions through it.
 * Real backend APIs integrate cleanly while preserving Load Demo mode.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  MOCK_SESSION, MOCK_ARTIFACTS, MOCK_VERSIONS, DEMO,
} from "@/mock/data";
import type {
  Session,
  SessionStage,
  Source,
  SourceOfTruth,
  OutputConfig,
  Job,
  JobStatus,
  Artifact,
  StreamEvent,
  ValidationResult,
} from "@/types";

// ─── Review state per artifact ────────────────────────────────────────────────
export type ArtifactReviewStatus = "pending" | "approved" | "rejected";

export interface ArtifactReview {
  status: ArtifactReviewStatus;
  rejectionReason?: string;
  reviewedAt?: string;
  reviewedBy?: string;
}

export type SourceProcessingStatus = "idle" | "uploading" | "processing" | "ready" | "failed";

export interface SessionErrors {
  upload?: string | null;
  sot?: string | null;
  job?: string | null;
  general?: string | null;
}

// ─── Store shape ──────────────────────────────────────────────────────────────
interface SessionStore {
  // Core session
  session: Session | null;
  sessionId: string | null;
  demoMode: boolean;

  // Source & Upload
  sourceStatus: SourceProcessingStatus;
  uploadProgress: number;
  uploadError: string | null;

  // SOT
  sotLockPending: boolean;
  sotLockHash: string | null;

  // Run & Job
  activeJobId: string | null;
  jobStatus: JobStatus | "idle";
  streamLog: string[];
  pipelineEvents: StreamEvent[];
  jobPollInterval: ReturnType<typeof setInterval> | null;

  // Outputs & Validation
  outputs: Artifact[];
  validationResults: Record<string, ValidationResult>;
  reviews: Record<string, ArtifactReview>;

  // Errors
  errors: SessionErrors;

  // Navigation
  currentStage: SessionStage;

  // ── Actions ────────────────────────────────────────────────────────────────
  /** Seed the store with the complete NTRO demo dataset (no backend needed) */
  seedDemo: () => void;
  /** Bootstrap a brand-new session (call on app init or "New Session") */
  initSession: (id: string) => void;

  /** Set the uploaded source on the session */
  setSource: (source: Source) => void;
  /** Set source processing status */
  setSourceStatus: (status: SourceProcessingStatus) => void;

  /** Track file upload progress (0-100) */
  setUploadProgress: (pct: number) => void;

  /** Set the built + (optionally locked) SOT */
  setSOT: (sot: SourceOfTruth) => void;
  /** Set SOT lock hash */
  setSotLockHash: (hash: string | null) => void;
  /** Set SOT lock pending state */
  setSotLockPending: (pending: boolean) => void;

  /** Add or replace an output config */
  upsertOutputConfig: (config: OutputConfig) => void;
  /** Remove an output config by id */
  removeOutputConfig: (id: string) => void;
  /** Replace all output configs (from server sync) */
  setOutputConfigs: (configs: OutputConfig[]) => void;

  /** Set the active pipeline job */
  setActiveJob: (job: Job) => void;
  /** Update a single job's data (from SSE or poll) */
  updateJob: (id: string, updates: Partial<Job>) => void;
  /** Set current job status */
  setJobStatus: (status: JobStatus | "idle") => void;

  /** Append a log line from the SSE stream */
  appendLog: (line: string) => void;
  /** Clear stream log */
  clearLog: () => void;

  /** Add live pipeline event */
  addPipelineEvent: (event: StreamEvent) => void;
  /** Clear pipeline events */
  clearPipelineEvents: () => void;

  /** Set final artifacts / outputs */
  setArtifacts: (artifacts: Artifact[]) => void;
  /** Set outputs synonym */
  setOutputs: (outputs: Artifact[]) => void;

  /** Set validation result for an artifact */
  setValidationResult: (artifactId: string, validation: ValidationResult) => void;

  /** Set review state for an artifact */
  setReview: (artifactId: string, review: ArtifactReview) => void;

  /** Set error state */
  setError: (key: keyof SessionErrors, message: string | null) => void;
  /** Clear all errors */
  clearErrors: () => void;

  /** Navigate to a stage (also syncs session.currentStage) */
  goToStage: (stage: SessionStage) => void;

  /** Full reset (new session) */
  reset: () => void;
}

// ─── Initial state ────────────────────────────────────────────────────────────
const INITIAL: Omit<
  SessionStore,
  | "seedDemo" | "initSession" | "setSource" | "setSourceStatus" | "setUploadProgress"
  | "setSOT" | "setSotLockHash" | "setSotLockPending" | "upsertOutputConfig"
  | "removeOutputConfig" | "setOutputConfigs" | "setActiveJob" | "updateJob"
  | "setJobStatus" | "appendLog" | "clearLog" | "addPipelineEvent" | "clearPipelineEvents"
  | "setArtifacts" | "setOutputs" | "setValidationResult" | "setReview"
  | "setError" | "clearErrors" | "goToStage" | "reset"
> = {
  session: null,
  sessionId: null,
  demoMode: false,
  sourceStatus: "idle",
  uploadProgress: 0,
  uploadError: null,
  sotLockPending: false,
  sotLockHash: null,
  activeJobId: null,
  jobStatus: "idle",
  streamLog: [],
  pipelineEvents: [],
  jobPollInterval: null,
  outputs: [],
  validationResults: {},
  reviews: {},
  errors: {},
  currentStage: "upload",
};

// ─── Store ────────────────────────────────────────────────────────────────────
export const useSessionStore = create<SessionStore>()(
  persist(
    (set, get) => ({
      ...INITIAL,

      seedDemo: () => {
        const valMap: Record<string, ValidationResult> = {};
        MOCK_ARTIFACTS.forEach((a) => {
          valMap[a.id] = a.validation;
        });

        set({
          demoMode:          true,
          sessionId:         DEMO.SESSION_ID,
          session:           MOCK_SESSION,
          currentStage:      "results",
          sourceStatus:      "ready",
          sotLockHash:       "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          activeJobId:       MOCK_SESSION.jobs[0]?.id ?? null,
          jobStatus:         "completed",
          uploadProgress:    100,
          uploadError:       null,
          sotLockPending:    false,
          streamLog:         ["[DEMO] Full pipeline completed successfully.", "[DEMO] 3 artefacts generated."],
          pipelineEvents:    [],
          outputs:           MOCK_ARTIFACTS,
          validationResults: valMap,
          errors:            {},
          reviews: {
            [DEMO.ART_PRESS]:    { status: "approved", reviewedAt: "2026-09-05T04:10:00.000Z", reviewedBy: "operator-001" },
            [DEMO.ART_INTEL]:    { status: "pending" },
            [DEMO.ART_BULLETIN]: { status: "pending" },
          },
        });
      },

      initSession: (id) =>
        set({
          sessionId: id,
          session: {
            id,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            operatorId: "operator",
            classification: "unclassified",
            outputConfigs: [],
            jobs: [],
            artifacts: [],
            currentStage: "upload",
          },
          currentStage:      "upload",
          sourceStatus:      "idle",
          uploadProgress:    0,
          uploadError:       null,
          sotLockPending:    false,
          sotLockHash:       null,
          activeJobId:       null,
          jobStatus:         "idle",
          streamLog:         [],
          pipelineEvents:    [],
          outputs:           [],
          validationResults: {},
          reviews:           {},
          errors:            {},
        }),

      setSource: (source) =>
        set((s) => ({
          sourceStatus: source.status ?? "ready",
          session: s.session
            ? { ...s.session, source, updatedAt: new Date().toISOString() }
            : null,
        })),

      setSourceStatus: (status) =>
        set((s) => ({
          sourceStatus: status,
          session: s.session?.source
            ? {
                ...s.session,
                source: { ...s.session.source, status },
              }
            : s.session,
        })),

      setUploadProgress: (pct) => set({ uploadProgress: pct }),

      setSOT: (sot) =>
        set((s) => ({
          sotLockHash: sot.lockHash ?? sot.hash ?? null,
          session: s.session
            ? { ...s.session, sot, updatedAt: new Date().toISOString() }
            : null,
        })),

      setSotLockHash: (hash) =>
        set((s) => ({
          sotLockHash: hash,
          session: s.session?.sot
            ? {
                ...s.session,
                sot: { ...s.session.sot, lockHash: hash ?? undefined },
              }
            : s.session,
        })),

      setSotLockPending: (pending) => set({ sotLockPending: pending }),

      upsertOutputConfig: (config) =>
        set((s) => {
          if (!s.session) return {};
          const existing = s.session.outputConfigs.findIndex(
            (c) => c.id === config.id
          );
          const configs =
            existing >= 0
              ? s.session.outputConfigs.map((c) =>
                  c.id === config.id ? config : c
                )
              : [...s.session.outputConfigs, config];
          return {
            session: {
              ...s.session,
              outputConfigs: configs,
              updatedAt: new Date().toISOString(),
            },
          };
        }),

      removeOutputConfig: (id) =>
        set((s) => ({
          session: s.session
            ? {
                ...s.session,
                outputConfigs: s.session.outputConfigs.filter(
                  (c) => c.id !== id
                ),
                updatedAt: new Date().toISOString(),
              }
            : null,
        })),

      setOutputConfigs: (configs) =>
        set((s) => ({
          session: s.session
            ? { ...s.session, outputConfigs: configs, updatedAt: new Date().toISOString() }
            : null,
        })),

      setActiveJob: (job) =>
        set((s) => ({
          activeJobId: job.id,
          jobStatus: job.status,
          session: s.session
            ? {
                ...s.session,
                jobs: [
                  ...s.session.jobs.filter((j) => j.id !== job.id),
                  job,
                ],
                updatedAt: new Date().toISOString(),
              }
            : null,
        })),

      updateJob: (id, updates) =>
        set((s) => ({
          jobStatus: updates.status ?? s.jobStatus,
          session: s.session
            ? {
                ...s.session,
                jobs: s.session.jobs.map((j) =>
                  j.id === id ? { ...j, ...updates } : j
                ),
                updatedAt: new Date().toISOString(),
              }
            : null,
        })),

      setJobStatus: (status) => set({ jobStatus: status }),

      appendLog: (line) =>
        set((s) => ({
          streamLog: [...s.streamLog.slice(-499), line],
        })),

      clearLog: () => set({ streamLog: [] }),

      addPipelineEvent: (event) =>
        set((s) => ({
          pipelineEvents: [...s.pipelineEvents.slice(-99), event],
        })),

      clearPipelineEvents: () => set({ pipelineEvents: [] }),

      setArtifacts: (artifacts) => {
        const valMap: Record<string, ValidationResult> = {};
        artifacts.forEach((a) => {
          if (a.validation) valMap[a.id] = a.validation;
        });
        set((s) => ({
          outputs: artifacts,
          validationResults: { ...s.validationResults, ...valMap },
          session: s.session
            ? {
                ...s.session,
                artifacts,
                updatedAt: new Date().toISOString(),
              }
            : null,
        }));
      },

      setOutputs: (outputs) => get().setArtifacts(outputs),

      setValidationResult: (artifactId, validation) =>
        set((s) => ({
          validationResults: { ...s.validationResults, [artifactId]: validation },
        })),

      setReview: (artifactId, review) =>
        set((s) => ({
          reviews: { ...s.reviews, [artifactId]: review },
        })),

      setError: (key, message) =>
        set((s) => ({
          errors: { ...s.errors, [key]: message },
        })),

      clearErrors: () => set({ errors: {} }),

      goToStage: (stage) =>
        set((s) => ({
          currentStage: stage,
          session: s.session
            ? {
                ...s.session,
                currentStage: stage,
                updatedAt: new Date().toISOString(),
              }
            : null,
        })),

      reset: () =>
        set({
          ...INITIAL,
        }),
    }),
    {
      name: "sutra-session",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({
        sessionId:    s.sessionId,
        session:      s.session,
        currentStage: s.currentStage,
        reviews:      s.reviews,
        sotLockHash:  s.sotLockHash,
      }),
    }
  )
);

// ─── Selectors ────────────────────────────────────────────────────────────────
export const selectSource          = (s: SessionStore) => s.session?.source;
export const selectSourceStatus    = (s: SessionStore) => s.sourceStatus;
export const selectSOT             = (s: SessionStore) => s.session?.sot;
export const selectSotLockHash     = (s: SessionStore) => s.sotLockHash;
export const selectConfigs         = (s: SessionStore) => s.session?.outputConfigs ?? [];
export const selectJobs            = (s: SessionStore) => s.session?.jobs ?? [];
export const selectArtifacts       = (s: SessionStore) => s.outputs.length > 0 ? s.outputs : (s.session?.artifacts ?? []);
export const selectOutputs         = selectArtifacts;
export const selectActiveJob       = (s: SessionStore) =>
  s.session?.jobs.find((j) => j.id === s.activeJobId);
export const selectJobStatus       = (s: SessionStore) => s.jobStatus;
export const selectPipelineEvents  = (s: SessionStore) => s.pipelineEvents;
export const selectValidationResults=(s: SessionStore) => s.validationResults;
export const selectErrors          = (s: SessionStore) => s.errors;
export const selectDemoMode        = (s: SessionStore) => s.demoMode;

// Re-export mock versions so Versions page can use them in demo mode
export { MOCK_VERSIONS } from "@/mock/data";
