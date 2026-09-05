import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  title?: string;
  message: string;
  detail?: string;
  stageLabel?: string;
  onRetry?: () => void;
  className?: string;
}

export default function LayoutFailure({
  title = "Stage Failed",
  message,
  detail,
  stageLabel,
  onRetry,
  className,
}: Props) {
  const [showDetail, setShowDetail] = useState(false);

  return (
    <div
      className={cn(
        "rounded-xl border border-red-900/60 bg-red-950/20 px-5 py-4",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-red-900/40 border border-red-800 flex items-center justify-center shrink-0">
          <AlertTriangle size={16} className="text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-red-300">{title}</h3>
            {stageLabel && (
              <span className="text-[10px] font-mono text-red-500 bg-red-950/50 border border-red-900 px-1.5 py-0.5 rounded uppercase tracking-wider">
                {stageLabel}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-300 mt-1 leading-snug">{message}</p>

          {detail && (
            <div className="mt-2">
              <button
                onClick={() => setShowDetail(!showDetail)}
                className="flex items-center gap-1 text-[11px] text-red-400 hover:text-red-300 transition-colors"
              >
                {showDetail ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                {showDetail ? "Hide" : "Show"} technical detail
              </button>
              {showDetail && (
                <pre className="mt-2 text-[11px] font-mono text-red-300 bg-slate-950 border border-red-900/50 rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {detail}
                </pre>
              )}
            </div>
          )}

          {onRetry && (
            <button onClick={onRetry} className="btn btn-danger btn-sm mt-3">
              <RefreshCw size={12} />
              Retry Stage
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
