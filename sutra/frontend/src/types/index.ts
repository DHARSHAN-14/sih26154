// ─────────────────────────────────────────────────────────────────────────────
// Source
// ─────────────────────────────────────────────────────────────────────────────
export type SourceType = "document" | "image" | "audio" | "video" | "text" | "url";

export interface Source {
  id: string;
  name: string;
  type: SourceType;
  mimeType: string;
  sizeBytes: number;
  uploadedAt: string;
  checksum: string;
  status?: "idle" | "uploading" | "processing" | "ready" | "failed";
  language?: string;
  durationSeconds?: number;
  pageCount?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Source of Truth (SOT)
// ─────────────────────────────────────────────────────────────────────────────
export type SOTStatus = "draft" | "verified" | "locked";

export type EntityType =
  | "person"
  | "organization"
  | "location"
  | "date"
  | "event"
  | "claim"
  | "fact"
  | "numeric"
  | "technical";

export interface SourceRef {
  page?: number;
  paragraph?: number;
  startOffset?: number;
  endOffset?: number;
  timestamp?: number;
}

export interface SOTEntity {
  id: string;
  text: string;
  type: EntityType;
  confidence: number;
  sourceRef: SourceRef;
  normalized?: string;
}

export interface SOTRelation {
  id: string;
  fromId: string;
  toId: string;
  label: string;
  confidence: number;
  evidence?: string;
  sourceRef?: SourceRef;
}

export interface SourceOfTruth {
  id: string;
  sourceId: string;
  status: SOTStatus;
  createdAt: string;
  lockedAt?: string;
  lockedBy?: string;
  hash?: string;
  lockHash?: string;
  entities: SOTEntity[];
  relations: SOTRelation[];
  rawText: string;
  extractedText?: string;
  pages?: { page: number; text: string }[];
  summary: string;
  language: string;
  wordCount: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Output Configuration
// ─────────────────────────────────────────────────────────────────────────────
export type OutputType =
  | "advisory"
  | "executive_summary"
  | "presentation"
  | "infographic"
  | "linkedin"
  | "twitter_x"
  | "video_package"
  | "press_release"
  | "social_post"
  | "executive_brief"
  | "technical_report"
  | "intelligence_summary"
  | "operational_bulletin";

export type SecurityClassification = "unclassified" | "restricted" | "confidential" | "secret";

export type ToneType = "formal" | "neutral" | "urgent" | "analytical";

export type LanguageCode = "en" | "hi" | "ta" | "te" | "mr" | "bn" | "gu" | "pa";

/** How much depth/length the output should have */
export type DetailLevel = "brief" | "standard" | "comprehensive" | "exhaustive";

/** Primary communicative goal of the output */
export type Objective = "inform" | "alert" | "persuade" | "summarize" | "brief";

/** Intended recipient of the output */
export type AudienceType =
  | "public"
  | "internal"
  | "executive"
  | "technical"
  | "field_operator"
  | "media";

/** Output document structure / presentation style */
export type StyleType = "narrative" | "bullet_points" | "table" | "mixed";

export interface OutputConfig {
  id: string;
  type: OutputType;
  templateId: string;
  language: LanguageCode;
  tone: ToneType;
  classification: SecurityClassification;
  model: string;
  maxTokens: number;
  enabled: boolean;
  // Extended configuration (operator responsibilities #4)
  detailLevel?: DetailLevel;
  objective?: Objective;
  audience?: AudienceType;
  style?: StyleType;
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline
// ─────────────────────────────────────────────────────────────────────────────
// ─── Pipeline Stages ─────────────────────────────────────────────────────────
// Granular backend stages
export type GranularStageId =
  | "upload"
  | "multimodal"
  | "ocr_asr_nlp"
  | "rag_kg"
  | "sot_build"
  | "sot_lock"
  | "planner"
  | "template"
  | "generation"
  | "validation"
  | "rendering"
  | "visual_validation"
  | "artifacts";

// High-level display stages
export type DisplayStageId =
  | "ingest"
  | "understand"
  | "sot"
  | "validate"
  | "generate"
  | "cross_output_validation"
  | "render"
  | "visual_validation"
  | "complete";

export type PipelineStageId = GranularStageId | DisplayStageId;

export type StageStatus = "pending" | "running" | "done" | "error" | "skipped";

export interface PipelineStageInfo {
  id: PipelineStageId;
  label: string;
  description: string;
  status: StageStatus;
  progress?: number;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  error?: string;
  metadata?: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Job / Run
// ─────────────────────────────────────────────────────────────────────────────
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  sessionId: string;
  status: JobStatus;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  stages: PipelineStageInfo[];
  outputCount: number;
  outputConfigIds: string[];
  progress: number;
}

export interface StreamEvent {
  type: "stage_start" | "stage_progress" | "stage_done" | "stage_error" | "job_done" | "log";
  stageId?: PipelineStageId;
  progress?: number;
  message?: string;
  data?: unknown;
  timestamp: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Validation
// ─────────────────────────────────────────────────────────────────────────────
export type IssueSeverity = "critical" | "warning" | "info";

export interface ValidationIssue {
  id: string;
  severity: IssueSeverity;
  claim: string;
  expected?: string;
  actual?: string;
  sourceRef?: string;
  entityId?: string;
}

export interface ValidationResult {
  factScore: number;
  consistencyScore: number;
  hallucination: number;
  issues: ValidationIssue[];
  passed: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Provenance
// ─────────────────────────────────────────────────────────────────────────────
export interface ProvenanceClaim {
  id: string;
  claim: string;
  sourceEntityId: string;
  sourceText: string;
  sourceRef: SourceRef;
  confidence: number;
  verified: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Visual Validation  (operator responsibility #9)
// ─────────────────────────────────────────────────────────────────────────────
export interface VisualValidationCheck {
  id: string;
  label: string;
  passed: boolean;
  detail?: string;
}

export interface VisualValidationResult {
  score: number;           // 0-1
  passed: boolean;
  layoutCompliant: boolean;
  templateAdherence: boolean;
  fontCompliant: boolean;
  imageQuality: boolean;
  checks: VisualValidationCheck[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Artifact
// ─────────────────────────────────────────────────────────────────────────────
export type ArtifactFormat = "pdf" | "docx" | "html" | "txt" | "json" | "png" | "md";

export interface Artifact {
  id: string;
  jobId: string;
  outputConfigId: string;
  type: OutputType;
  format: ArtifactFormat;
  title: string;
  previewText?: string;
  previewUrl?: string;
  downloadUrl: string;
  sizeBytes: number;
  createdAt: string;
  validation: ValidationResult;
  visualValidation?: VisualValidationResult;
  provenance: ProvenanceClaim[];
  classification: SecurityClassification;
  version: number;
  language: LanguageCode;
}

// ─────────────────────────────────────────────────────────────────────────────
// Session
// ─────────────────────────────────────────────────────────────────────────────
export type SessionStage = "upload" | "truth" | "configure" | "run" | "results" | "versions";

export interface SessionVersion {
  id: string;
  sessionId: string;
  version: number;
  createdAt: string;
  createdBy: string;
  sourceId: string;
  sourceName: string;
  artifactCount: number;
  status: "active" | "archived";
  notes?: string;
}

export interface Session {
  id: string;
  createdAt: string;
  updatedAt: string;
  operatorId: string;
  classification: SecurityClassification;
  source?: Source;
  sot?: SourceOfTruth;
  outputConfigs: OutputConfig[];
  jobs: Job[];
  artifacts: Artifact[];
  currentStage: SessionStage;
}
