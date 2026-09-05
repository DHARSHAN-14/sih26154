import { useState } from "react";
import { AlertTriangle, CheckCircle, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn, scorePct, scoreColor } from "@/lib/utils";
import type { ValidationResult } from "@/types";

interface Props {
  validation: ValidationResult;
  className?: string;
}

const severityIcon = { critical: XCircle, warning: AlertTriangle, info: CheckCircle };
const severityColor = {
  critical: "text-red-400 bg-red-900/30 border-red-800",
  warning:  "text-yellow-400 bg-yellow-900/30 border-yellow-800",
  info:     "text-blue-400 bg-blue-900/30 border-blue-800",
};

export default function ValidationBadge({ validation, className }: Props) {
  const [open, setOpen] = useState(false);
  const { factScore, consistencyScore, hallucination, passed, issues } = validation;

  const criticalCount = issues.filter((i) => i.severity === "critical").length;
  const warnCount     = issues.filter((i) => i.severity === "warning").length;

  return (
    <div className={cn("rounded-lg border overflow-hidden", passed ? "border-emerald-800 bg-emerald-950/30" : "border-red-800 bg-red-950/30", className)}>
      {/* Summary row */}
      <button
        onClick={() => issues.length > 0 && setOpen(!open)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
      >
        {/* Pass/fail icon */}
        <div className={cn("shrink-0", passed ? "text-emerald-400" : "text-red-400")}>
          {passed ? <CheckCircle size={16} /> : <XCircle size={16} />}
        </div>

        {/* Scores */}
        <div className="flex-1 grid grid-cols-3 gap-2">
          {[
            { label: "Fact",    value: factScore },
            { label: "Consist", value: consistencyScore },
            { label: "Halluc", value: 1 - hallucination, invert: true },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className={cn("text-sm font-bold tabular-nums", scoreColor(value))}>{scorePct(value)}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</div>
            </div>
          ))}
        </div>

        {/* Issue count + expand */}
        {issues.length > 0 && (
          <div className="flex items-center gap-1.5 shrink-0">
            {criticalCount > 0 && (
              <span className="text-[10px] bg-red-900/50 text-red-400 px-1.5 py-0.5 rounded">
                {criticalCount} crit
              </span>
            )}
            {warnCount > 0 && (
              <span className="text-[10px] bg-yellow-900/50 text-yellow-400 px-1.5 py-0.5 rounded">
                {warnCount} warn
              </span>
            )}
            {open ? <ChevronUp size={12} className="text-slate-500" /> : <ChevronDown size={12} className="text-slate-500" />}
          </div>
        )}
      </button>

      {/* Score bars */}
      <div className="px-3 pb-2 grid grid-cols-3 gap-2">
        {[factScore, consistencyScore, 1 - hallucination].map((v, i) => (
          <div key={i} className="h-1 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", v >= 0.85 ? "bg-emerald-500" : v >= 0.65 ? "bg-yellow-500" : "bg-red-500")}
              style={{ width: `${Math.round(v * 100)}%` }}
            />
          </div>
        ))}
      </div>

      {/* Issues list */}
      {open && issues.length > 0 && (
        <div className="border-t border-slate-800 divide-y divide-slate-800/50 max-h-48 overflow-y-auto">
          {issues.map((issue) => {
            const Icon = severityIcon[issue.severity];
            return (
              <div key={issue.id} className={cn("flex gap-2 px-3 py-2 text-xs", severityColor[issue.severity])}>
                <Icon size={12} className="shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="font-medium truncate">{issue.claim}</p>
                  {issue.expected && (
                    <p className="text-slate-400 mt-0.5">
                      Expected: <span className="font-mono">{issue.expected}</span>
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
