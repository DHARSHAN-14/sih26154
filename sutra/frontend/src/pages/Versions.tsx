import { useEffect, useState } from "react";
import { History, Archive, ChevronDown, ChevronRight, RotateCcw } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { useSessionStore, selectDemoMode, MOCK_VERSIONS } from "@/store/session";
import { versionsApi } from "@/api/client";
import type { SessionVersion } from "@/types";

export default function Versions() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const demoMode  = useSessionStore(selectDemoMode);
  const [versions, setVersions] = useState<SessionVersion[]>([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    if (demoMode) {
      setVersions(MOCK_VERSIONS);
      return;
    }
    if (!sessionId) return;
    setLoading(true);
    versionsApi
      .list(sessionId)
      .then((res) => setVersions(res.data))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load version history.");
      })
      .finally(() => setLoading(false));
  }, [sessionId, demoMode]);

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-600">
        <History size={32} className="text-slate-700" />
        <p className="text-sm">No active session. <a href="/upload" className="text-blue-400 hover:underline">Start a new session</a>.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">Version History</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Complete audit trail for session <span className="font-mono">{sessionId.slice(0, 12)}…</span>
          </p>
        </div>
        {versions.length > 0 && (
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-400">{versions.length}</div>
            <div className="text-xs text-slate-500">version{versions.length !== 1 ? "s" : ""}</div>
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-sm text-slate-500 flex items-center gap-2 py-8 justify-center">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          Loading version history…
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-4 py-3 rounded-lg border border-red-900 bg-red-950/20 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && versions.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-600 border border-dashed border-slate-800 rounded-xl">
          <Archive size={28} className="text-slate-700" />
          <p className="text-sm">No versions recorded yet. Complete a pipeline run to create a version.</p>
        </div>
      )}

      {/* Version list */}
      {versions.length > 0 && (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[19px] top-4 bottom-4 w-px bg-slate-800" />

          <div className="space-y-3">
            {versions.map((version, idx) => {
              const isExpanded = expandedId === version.id;
              const isLatest   = idx === 0;

              return (
                <div key={version.id} className="relative flex gap-4">
                  {/* Timeline dot */}
                  <div
                    className={cn(
                      "relative z-10 w-10 h-10 rounded-full shrink-0 flex items-center justify-center",
                      "border text-xs font-bold",
                      version.status === "active"
                        ? isLatest
                          ? "bg-blue-900 border-blue-600 text-blue-300"
                          : "bg-slate-800 border-slate-700 text-slate-400"
                        : "bg-slate-900 border-slate-800 text-slate-600"
                    )}
                  >
                    v{version.version}
                  </div>

                  {/* Card */}
                  <div className={cn(
                    "flex-1 rounded-xl border overflow-hidden mb-2",
                    version.status === "archived"
                      ? "border-slate-800 bg-slate-900/50 opacity-70"
                      : "border-slate-700 bg-slate-900"
                  )}>
                    {/* Row header */}
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : version.id)}
                      className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-slate-800/40 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-slate-200 truncate">
                            {version.sourceName}
                          </span>
                          {isLatest && version.status === "active" && (
                            <span className="text-[9px] font-bold tracking-widest text-blue-400 bg-blue-950/50 border border-blue-800 px-1.5 py-0.5 rounded uppercase">
                              LATEST
                            </span>
                          )}
                          {version.status === "archived" && (
                            <span className="text-[9px] font-bold tracking-widest text-slate-500 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded uppercase">
                              ARCHIVED
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500 font-mono flex-wrap">
                          <span>{formatDate(version.createdAt)}</span>
                          <span>·</span>
                          <span>by {version.createdBy}</span>
                          <span>·</span>
                          <span>{version.artifactCount} artefact{version.artifactCount !== 1 ? "s" : ""}</span>
                        </div>
                      </div>
                      <div className="shrink-0 text-slate-600 mt-1">
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </div>
                    </button>

                    {/* Expanded detail */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-1 border-t border-slate-800 space-y-3">
                        {/* Metadata grid */}
                        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
                          {[
                            { label: "Version ID",  value: version.id.slice(0, 16) + "…" },
                            { label: "Session ID",  value: version.sessionId.slice(0, 16) + "…" },
                            { label: "Source ID",   value: version.sourceId.slice(0, 16) + "…" },
                            { label: "Artefacts",   value: String(version.artifactCount) },
                            { label: "Created",     value: formatDate(version.createdAt) },
                            { label: "Operator",    value: version.createdBy },
                          ].map(({ label, value }) => (
                            <div key={label} className="flex flex-col gap-0.5">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
                              <span className="font-mono text-slate-300 truncate">{value}</span>
                            </div>
                          ))}
                        </div>

                        {version.notes && (
                          <div className="text-xs text-slate-400 italic border-l-2 border-slate-700 pl-3">
                            {version.notes}
                          </div>
                        )}

                        {/* Actions */}
                        {version.status === "active" && !isLatest && (
                          <div className="flex gap-2 pt-1">
                            <button
                              onClick={() => {
                                if (sessionId) {
                                  versionsApi.restore(sessionId, version.id)
                                    .then(() => versionsApi.list(sessionId))
                                    .then((r) => setVersions(r.data))
                                    .catch(() => {});
                                }
                              }}
                              className="btn btn-secondary btn-sm"
                            >
                              <RotateCcw size={12} /> Restore this version
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
