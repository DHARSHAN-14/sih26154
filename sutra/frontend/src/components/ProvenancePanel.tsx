import { useState } from "react";
import { ChevronDown, ChevronRight, Link2, CheckCircle, AlertCircle } from "lucide-react";
import { cn, scorePct } from "@/lib/utils";
import type { ProvenanceClaim } from "@/types";

interface Props {
  claims: ProvenanceClaim[];
  className?: string;
}

export default function ProvenancePanel({ claims, className }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (claims.length === 0) {
    return (
      <div className={cn("text-center py-6 text-slate-600 text-sm", className)}>
        No provenance data available.
      </div>
    );
  }

  const verified   = claims.filter((c) => c.verified).length;
  const total      = claims.length;
  const avgConf    = claims.reduce((s, c) => s + c.confidence, 0) / total;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Summary bar */}
      <div className="flex items-center gap-4 px-3 py-2.5 rounded-lg bg-slate-800/50 border border-slate-700">
        <div className="flex items-center gap-1.5 text-sm">
          <CheckCircle size={14} className="text-emerald-400" />
          <span className="text-slate-300">
            <span className="font-semibold text-emerald-400">{verified}</span>
            <span className="text-slate-500">/{total}</span>
            <span className="text-slate-400 ml-1">claims verified</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <Link2 size={13} className="text-blue-400" />
          <span className="text-slate-400">
            Avg confidence: <span className="font-mono text-blue-400">{scorePct(avgConf)}</span>
          </span>
        </div>
      </div>

      {/* Claim list */}
      <div className="space-y-1.5">
        {claims.map((claim) => {
          const isOpen = expanded === claim.id;
          return (
            <div
              key={claim.id}
              className={cn(
                "rounded-lg border transition-colors overflow-hidden",
                claim.verified
                  ? "border-emerald-900/60 bg-emerald-950/20"
                  : "border-yellow-900/60 bg-yellow-950/20"
              )}
            >
              <button
                onClick={() => setExpanded(isOpen ? null : claim.id)}
                className="w-full flex items-start gap-3 px-3 py-2.5 text-left"
              >
                {/* Verified icon */}
                <div className="shrink-0 mt-0.5">
                  {claim.verified ? (
                    <CheckCircle size={14} className="text-emerald-400" />
                  ) : (
                    <AlertCircle size={14} className="text-yellow-400" />
                  )}
                </div>

                {/* Claim text */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 leading-snug">{claim.claim}</p>
                  <div className="flex items-center gap-3 mt-1">
                    {/* Confidence bar */}
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-1 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            claim.confidence >= 0.85
                              ? "bg-emerald-500"
                              : claim.confidence >= 0.65
                              ? "bg-yellow-500"
                              : "bg-red-500"
                          )}
                          style={{ width: `${Math.round(claim.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="mono-sm">{scorePct(claim.confidence)}</span>
                    </div>
                    {/* Source ref */}
                    {(claim.sourceRef.page != null) && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        p.{claim.sourceRef.page}
                        {claim.sourceRef.paragraph != null ? ` ¶${claim.sourceRef.paragraph}` : ""}
                      </span>
                    )}
                    {(claim.sourceRef.timestamp != null) && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        @{claim.sourceRef.timestamp}s
                      </span>
                    )}
                  </div>
                </div>

                {/* Expand */}
                <div className="shrink-0 text-slate-600 mt-0.5">
                  {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </div>
              </button>

              {/* Source text */}
              {isOpen && (
                <div className="px-3 pb-3 pt-0 border-t border-slate-800/50">
                  <div className="label mb-1.5">Source excerpt</div>
                  <blockquote className="text-xs text-slate-300 font-mono leading-relaxed bg-slate-900 border border-slate-800 rounded px-3 py-2 italic">
                    "{claim.sourceText}"
                  </blockquote>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
