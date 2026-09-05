import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { SecurityClassification, OutputType, StageStatus, ArtifactFormat } from "@/types";

/** Merge Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format bytes to human-readable string */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/** Format duration in ms to human-readable */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}

/** Format ISO date string */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Truncate string to max length */
export function truncate(s: string, max = 80): string {
  return s.length > max ? s.slice(0, max) + "…" : s;
}

/** Short hex ID for display */
export function shortId(id: string): string {
  return id.slice(0, 8).toUpperCase();
}

/** Classification colors */
export const classifyColors: Record<SecurityClassification, { bg: string; text: string; border: string; label: string }> = {
  unclassified: { bg: "bg-green-900/30", text: "text-green-400", border: "border-green-700", label: "UNCLASSIFIED" },
  restricted:   { bg: "bg-yellow-900/30", text: "text-yellow-400", border: "border-yellow-700", label: "RESTRICTED" },
  confidential: { bg: "bg-orange-900/30", text: "text-orange-400", border: "border-orange-700", label: "CONFIDENTIAL" },
  secret:       { bg: "bg-red-900/30", text: "text-red-400", border: "border-red-700", label: "SECRET" },
};

/** Stage status colors */
export const stageStatusColors: Record<StageStatus, { dot: string; text: string; bg: string }> = {
  pending: { dot: "bg-slate-600",  text: "text-slate-400",  bg: "bg-slate-800/50" },
  running: { dot: "bg-blue-500",   text: "text-blue-400",   bg: "bg-blue-900/20" },
  done:    { dot: "bg-emerald-500", text: "text-emerald-400", bg: "bg-emerald-900/20" },
  error:   { dot: "bg-red-500",    text: "text-red-400",    bg: "bg-red-900/20" },
  skipped: { dot: "bg-slate-600",  text: "text-slate-500",  bg: "bg-slate-800/30" },
};

/** Output type metadata */
export const outputTypeMeta: Record<OutputType, { label: string; icon: string; description: string }> = {
  press_release:        { label: "Press Release",         icon: "📰", description: "Formal public communication for media" },
  social_post:          { label: "Social Media Post",      icon: "📣", description: "Short-form content for social channels" },
  executive_brief:      { label: "Executive Brief",        icon: "📋", description: "Concise summary for leadership" },
  technical_report:     { label: "Technical Report",       icon: "🔬", description: "Detailed technical documentation" },
  intelligence_summary: { label: "Intelligence Summary",   icon: "🔍", description: "Classified analytical summary" },
  operational_bulletin: { label: "Operational Bulletin",   icon: "📡", description: "Operational field communication" },
};

/** Artifact format extensions */
export const artifactFormatLabel: Record<ArtifactFormat, string> = {
  pdf:  "PDF",
  docx: "Word",
  html: "HTML",
  txt:  "Text",
  json: "JSON",
  png:  "Image",
  md:   "Markdown",
};

/** Score to color */
export function scoreColor(score: number): string {
  if (score >= 0.85) return "text-emerald-400";
  if (score >= 0.65) return "text-yellow-400";
  return "text-red-400";
}

/** Score percentage string */
export function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}
