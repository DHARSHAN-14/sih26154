import { CheckCircle, XCircle, Loader, Clock, SkipForward } from "lucide-react";
import { cn, formatDuration, stageStatusColors } from "@/lib/utils";
import type { PipelineStageInfo } from "@/types";

interface Props {
  stage: PipelineStageInfo;
  index: number;
  total: number;
  variant?: "compact" | "full";
}

function StatusIcon({ status }: { status: PipelineStageInfo["status"] }) {
  const cls = "shrink-0";
  switch (status) {
    case "done":    return <CheckCircle  size={15} className={cn(cls, "text-emerald-400")} />;
    case "error":   return <XCircle      size={15} className={cn(cls, "text-red-400")} />;
    case "running": return <Loader       size={15} className={cn(cls, "text-blue-400 animate-spin")} />;
    case "skipped": return <SkipForward  size={15} className={cn(cls, "text-slate-600")} />;
    default:        return <Clock        size={15} className={cn(cls, "text-slate-600")} />;
  }
}

export default function PipelineStage({ stage, index, total, variant = "full" }: Props) {
  const colors = stageStatusColors[stage.status];
  const isLast = index === total - 1;

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-2 px-2 py-1.5 rounded", colors.bg)}>
        <StatusIcon status={stage.status} />
        <span className={cn("text-xs font-medium truncate", colors.text)}>{stage.label}</span>
        {stage.durationMs != null && (
          <span className="ml-auto mono-sm shrink-0">{formatDuration(stage.durationMs)}</span>
        )}
      </div>
    );
  }

  return (
    <div className="relative flex gap-4">
      {/* Connector */}
      {!isLast && (
        <div
          className={cn(
            "absolute left-4 -translate-x-1/2 top-8 bottom-0 w-px",
            stage.status === "done" ? "bg-emerald-800" : "bg-slate-800"
          )}
        />
      )}

      {/* Step number + status */}
      <div className="relative z-10 shrink-0 flex flex-col items-center">
        <div
          className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center border text-xs font-bold",
            stage.status === "done"
              ? "bg-emerald-900/50 border-emerald-700 text-emerald-300"
              : stage.status === "running"
              ? "bg-blue-900/50 border-blue-600 text-blue-300"
              : stage.status === "error"
              ? "bg-red-900/50 border-red-700 text-red-300"
              : "bg-slate-800 border-slate-700 text-slate-500"
          )}
        >
          {stage.status === "done" ? (
            <CheckCircle size={14} />
          ) : stage.status === "running" ? (
            <Loader size={14} className="animate-spin" />
          ) : stage.status === "error" ? (
            <XCircle size={14} />
          ) : (
            index + 1
          )}
        </div>
      </div>

      {/* Content */}
      <div className={cn("flex-1 min-w-0 pb-5 pt-1", isLast ? "pb-0" : "")}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className={cn("text-sm font-semibold", colors.text)}>{stage.label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{stage.description}</div>
          </div>
          <div className="shrink-0 flex flex-col items-end gap-1">
            {stage.durationMs != null && (
              <span className="mono-sm text-slate-500">{formatDuration(stage.durationMs)}</span>
            )}
            <span
              className={cn(
                "text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded",
                colors.bg, colors.text
              )}
            >
              {stage.status}
            </span>
          </div>
        </div>

        {/* Progress bar for running stage */}
        {stage.status === "running" && stage.progress != null && (
          <div className="mt-2 h-1 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${stage.progress}%` }}
            />
          </div>
        )}

        {/* Error message */}
        {stage.status === "error" && stage.error && (
          <div className="mt-2 text-xs text-red-400 bg-red-950/30 border border-red-900 rounded px-2 py-1.5 font-mono">
            {stage.error}
          </div>
        )}
      </div>
    </div>
  );
}
