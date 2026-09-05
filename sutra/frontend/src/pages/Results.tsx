import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle, XCircle, Eye, Download, ChevronRight,
  FileOutput, AlertTriangle, RotateCcw, Monitor, Shield,
  Loader, RefreshCw, FlaskConical,
} from "lucide-react";
import { cn, outputTypeMeta, formatDate } from "@/lib/utils";
import {
  useSessionStore,
  selectArtifacts,
  selectDemoMode,
} from "@/store/session";
import { outputsApi } from "@/api/client";
import ArtifactPreview from "@/components/ArtifactPreview";
import ValidationBadge from "@/components/ValidationBadge";
import ProvenancePanel from "@/components/ProvenancePanel";
import SecurityBadge from "@/components/SecurityBadge";
import type { Artifact, VisualValidationResult } from "@/types";
import type { ArtifactReviewStatus } from "@/store/session";

type ReviewModal = { artifact: Artifact; panel: "preview" | "provenance" | "visual" };

const REVIEW_STYLE: Record<ArtifactReviewStatus, { label: string; cls: string; Icon: React.ElementType }> = {
  pending:  { label: "Pending Review", cls: "text-slate-400 border-slate-700 bg-slate-800/50",      Icon: Eye },
  approved: { label: "Approved",       cls: "text-emerald-400 border-emerald-800 bg-emerald-950/30", Icon: CheckCircle },
  rejected: { label: "Rejected",       cls: "text-red-400 border-red-800 bg-red-950/30",             Icon: XCircle },
};

// ─── Visual Validation Panel ──────────────────────────────────────────────────
function VisualValidationPanel({ vv }: { vv: VisualValidationResult }) {
  const scoreColor = vv.score >= 0.9 ? "text-emerald-400" : vv.score >= 0.7 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-xl border",
        vv.passed ? "bg-emerald-950/20 border-emerald-800" : "bg-red-950/20 border-red-800"
      )}>
        <div className={cn("shrink-0", vv.passed ? "text-emerald-400" : "text-red-400")}>
          {vv.passed ? <CheckCircle size={18} /> : <XCircle size={18} />}
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-slate-200">
            Visual Validation {vv.passed ? "Passed" : "Failed"}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Score: <span className={cn("font-mono font-semibold", scoreColor)}>{Math.round(vv.score * 100)}%</span>
          </div>
        </div>
        {/* Score bars */}
        <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
          {[
            { label: "Layout",   ok: vv.layoutCompliant },
            { label: "Template", ok: vv.templateAdherence },
            { label: "Font",     ok: vv.fontCompliant },
            { label: "Image",    ok: vv.imageQuality },
          ].map(({ label, ok }) => (
            <div key={label}>
              <div className={ok ? "text-emerald-400" : "text-red-400"}>{ok ? "✓" : "✗"}</div>
              <div className="text-slate-500">{label}</div>
            </div>
          ))}
        </div>
      </div>
      {/* Checks list */}
      <div className="space-y-1.5">
        <div className="label">Individual Checks</div>
        {vv.checks.map((check) => (
          <div key={check.id} className={cn(
            "flex items-start gap-2.5 px-3 py-2 rounded-lg border text-xs",
            check.passed
              ? "border-emerald-900/50 bg-emerald-950/20 text-emerald-300"
              : "border-yellow-900/50 bg-yellow-950/20 text-yellow-300"
          )}>
            {check.passed ? <CheckCircle size={13} className="shrink-0 mt-0.5" /> : <AlertTriangle size={13} className="shrink-0 mt-0.5" />}
            <div>
              <div className="font-medium">{check.label}</div>
              {check.detail && <div className="text-[11px] mt-0.5 opacity-75">{check.detail}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Mini visual validation badge ─────────────────────────────────────────────
function VisualBadge({ vv }: { vv?: VisualValidationResult }) {
  if (!vv) return null;
  return (
    <div className={cn(
      "flex items-center gap-1.5 text-[10px] font-medium px-2 py-1 rounded-md border",
      vv.passed ? "border-emerald-800 bg-emerald-950/30 text-emerald-400" : "border-yellow-800 bg-yellow-950/30 text-yellow-400"
    )}>
      <Monitor size={10} />
      Visual {vv.passed ? "✓" : "!"}
      <span className="font-mono">{Math.round(vv.score * 100)}%</span>
    </div>
  );
}

export default function Results() {
  const navigate   = useNavigate();
  const artifacts  = useSessionStore(selectArtifacts);
  const reviews    = useSessionStore((s) => s.reviews);
  const demoMode   = useSessionStore(selectDemoMode);
  const activeJobId= useSessionStore((s) => s.activeJobId);
  const sessionId  = useSessionStore((s) => s.sessionId);
  const { setReview, setArtifacts, goToStage, seedDemo } = useSessionStore();

  const [loading, setLoading]           = useState(false);
  const [fetchError, setFetchError]     = useState<string | null>(null);
  const [modal, setModal]               = useState<ReviewModal | null>(null);
  const [rejectTarget, setRejectTarget] = useState<Artifact | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Fetch real outputs from backend if not yet in store
  useEffect(() => {
    if (artifacts.length > 0 || demoMode || (!activeJobId && !sessionId)) return;

    let mounted = true;
    async function loadOutputs() {
      setLoading(true);
      setFetchError(null);
      try {
        let res;
        if (activeJobId) {
          res = await outputsApi.list(activeJobId);
        } else if (sessionId) {
          res = await outputsApi.listBySession(sessionId);
        }
        if (mounted && res?.data && res.data.length > 0) {
          setArtifacts(res.data);
        }
      } catch (err: unknown) {
        if (mounted) {
          setFetchError(
            err instanceof Error ? err.message : "Failed to load generated outputs from backend."
          );
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadOutputs();
    return () => { mounted = false; };
  }, [artifacts.length, activeJobId, sessionId, demoMode, setArtifacts]);

  const approvedCount = Object.values(reviews).filter((r) => r.status === "approved").length;
  const rejectedCount = Object.values(reviews).filter((r) => r.status === "rejected").length;
  const pendingCount  = Object.values(reviews).filter((r) => r.status === "pending").length;

  function approve(artifact: Artifact) {
    outputsApi.approve(artifact.id).catch(() => {});
    setReview(artifact.id, {
      status: "approved",
      reviewedAt: new Date().toISOString(),
      reviewedBy: "operator",
    });
  }

  function submitReject() {
    if (!rejectTarget) return;
    outputsApi.reject(rejectTarget.id, rejectReason).catch(() => {});
    setReview(rejectTarget.id, {
      status: "rejected",
      rejectionReason: rejectReason.trim() || "No reason provided",
      reviewedAt: new Date().toISOString(),
      reviewedBy: "operator",
    });
    setRejectTarget(null);
    setRejectReason("");
  }

  async function handleDownload(artifact: Artifact) {
    try {
      await outputsApi.downloadBlob(artifact.id, `${artifact.title}.${artifact.format}`);
    } catch {
      window.open(outputsApi.downloadUrl(artifact.id), "_blank");
    }
  }

  function approveAll() {
    artifacts.filter((a) => (reviews[a.id]?.status ?? "pending") !== "rejected").forEach(approve);
  }

  function downloadApproved() {
    artifacts
      .filter((a) => reviews[a.id]?.status === "approved")
      .forEach(handleDownload);
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-400">
        <Loader size={28} className="animate-spin text-blue-500" />
        <p className="text-sm font-medium text-slate-200">Loading generated output artefacts from backend…</p>
        <p className="mono-sm text-slate-500">Job ID: {activeJobId || "current"}</p>
      </div>
    );
  }

  // Error fetching outputs
  if (artifacts.length === 0 && fetchError) {
    return (
      <div className="max-w-xl mx-auto space-y-4 p-5 rounded-xl bg-red-950/20 border border-red-900 text-slate-200">
        <div className="flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-red-300">Could Not Retrieve Outputs</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{fetchError}</p>
            <p className="text-xs text-slate-500 mt-2">
              If the backend job is still executing or routes_outputs.py is pending, you can retry or inspect demo data.
            </p>
          </div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button
            onClick={() => {
              if (activeJobId) {
                setLoading(true);
                outputsApi.list(activeJobId)
                  .then((r) => setArtifacts(r.data))
                  .catch((e) => setFetchError(e.message))
                  .finally(() => setLoading(false));
              }
            }}
            className="btn btn-secondary btn-sm gap-1"
          >
            <RefreshCw size={12} /> Retry Fetch
          </button>
          <button
            onClick={() => { seedDemo(); }}
            className="btn btn-primary btn-sm gap-1.5 text-purple-100 bg-purple-700 hover:bg-purple-600"
          >
            <FlaskConical size={13} /> Load Demo Outputs
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-600">
        <FileOutput size={32} className="text-slate-700" />
        <p className="text-sm">No artefacts yet. <a href="/run" className="text-blue-400 hover:underline">Run the pipeline</a> first.</p>
        <button
          onClick={() => { seedDemo(); }}
          className="btn btn-secondary btn-sm gap-1.5 text-purple-300 border-purple-800"
        >
          <FlaskConical size={13} className="text-purple-400" /> Load Demo Outputs
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="page-title">Review & Approve Artefacts</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            {artifacts.length} artefact{artifacts.length !== 1 ? "s" : ""} ·{" "}
            <span className="text-emerald-400">{approvedCount} approved</span> ·{" "}
            <span className="text-amber-400">{pendingCount} pending</span> ·{" "}
            <span className="text-red-400">{rejectedCount} rejected</span>
          </p>
        </div>
        <div className="flex gap-2 shrink-0 flex-wrap">
          {pendingCount > 0 && (
            <button onClick={approveAll} className="btn btn-success btn-sm">
              <CheckCircle size={12} /> Approve All Pending
            </button>
          )}
          {approvedCount > 0 && (
            <button onClick={downloadApproved} className="btn btn-primary">
              <Download size={14} /> Export Approved ({approvedCount})
            </button>
          )}
          <button onClick={() => { goToStage("versions"); navigate("/versions"); }} className="btn btn-secondary">
            History <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Artefact grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {artifacts.map((artifact) => {
          const review     = reviews[artifact.id];
          const status     = review?.status ?? "pending";
          const styleCfg   = REVIEW_STYLE[status];
          const StatusIcon = styleCfg.Icon;
          const meta       = outputTypeMeta[artifact.type];
          const vv         = artifact.visualValidation;

          return (
            <div key={artifact.id} className={cn("rounded-xl border overflow-hidden transition-colors", styleCfg.cls)}>
              {/* Header */}
              <div className="flex items-start gap-3 px-4 py-3 border-b border-slate-800/50">
                <span className="text-xl shrink-0 mt-0.5">{meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-200">{artifact.title}</span>
                    <SecurityBadge level={artifact.classification} variant="pill" />
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono flex-wrap">
                    <span>{meta.label}</span>
                    <span>·</span>
                    <span>{formatDate(artifact.createdAt)}</span>
                    <span>·</span>
                    <span>v{artifact.version}</span>
                    <span>·</span>
                    <span>{artifact.language.toUpperCase()}</span>
                  </div>
                </div>
                <div className={cn("flex items-center gap-1.5 text-xs font-medium shrink-0 px-2 py-1 rounded-lg border", styleCfg.cls)}>
                  <StatusIcon size={12} />
                  {styleCfg.label}
                </div>
              </div>

              {/* Fact Validation */}
              <div className="px-4 py-3 border-b border-slate-800/50">
                <div className="label mb-1.5 flex items-center gap-1.5"><Shield size={11} /> Fact Validation</div>
                <ValidationBadge validation={artifact.validation} />
              </div>

              {/* Visual Validation summary */}
              {vv && (
                <div className="px-4 py-2.5 border-b border-slate-800/50 flex items-center gap-3">
                  <div className="label flex items-center gap-1.5 shrink-0"><Monitor size={11} /> Visual</div>
                  <VisualBadge vv={vv} />
                  {vv.checks.some((c) => !c.passed) && (
                    <span className="text-[10px] text-yellow-500">
                      {vv.checks.filter((c) => !c.passed).length} issue{vv.checks.filter((c) => !c.passed).length !== 1 ? "s" : ""}
                    </span>
                  )}
                  <button onClick={() => setModal({ artifact, panel: "visual" })} className="ml-auto text-[11px] text-slate-500 hover:text-blue-400 transition-colors">
                    Details →
                  </button>
                </div>
              )}

              {/* Preview text */}
              {artifact.previewText && (
                <div className="px-4 py-2 border-b border-slate-800/50">
                  <p className="text-xs text-slate-400 font-mono leading-relaxed line-clamp-3">{artifact.previewText}</p>
                </div>
              )}

              {/* Rejection reason */}
              {status === "rejected" && review?.rejectionReason && (
                <div className="px-4 py-2 border-b border-red-900/30">
                  <div className="flex items-start gap-2 text-xs text-red-400">
                    <AlertTriangle size={11} className="shrink-0 mt-0.5" />
                    <span><strong>Rejection:</strong> {review.rejectionReason}</span>
                  </div>
                </div>
              )}

              {/* Provenance count */}
              <div className="px-4 py-2 border-b border-slate-800/50">
                <span className="text-[11px] text-slate-500">
                  {artifact.provenance.length} provenance claim{artifact.provenance.length !== 1 ? "s" : ""} ·{" "}
                  {artifact.provenance.filter((p) => p.verified).length} verified
                </span>
              </div>

              {/* Action row */}
              <div className="flex items-center gap-2 px-4 py-2.5 flex-wrap">
                <button onClick={() => setModal({ artifact, panel: "preview" })} className="btn btn-secondary btn-sm"><Eye size={12} /> Preview</button>
                <button onClick={() => setModal({ artifact, panel: "provenance" })} className="btn btn-secondary btn-sm">Provenance</button>
                {vv && <button onClick={() => setModal({ artifact, panel: "visual" })} className="btn btn-secondary btn-sm"><Monitor size={12} /> Visual</button>}
                <div className="flex-1" />
                {status !== "approved" && (
                  <button onClick={() => approve(artifact)} className="btn btn-success btn-sm"><CheckCircle size={12} /> Approve</button>
                )}
                {status !== "rejected" && (
                  <button onClick={() => { setRejectTarget(artifact); setRejectReason(""); }} className="btn btn-danger btn-sm"><XCircle size={12} /> Reject</button>
                )}
                {status === "rejected" && (
                  <button onClick={() => setReview(artifact.id, { status: "pending" })} className="btn btn-secondary btn-sm"><RotateCcw size={12} /> Reset</button>
                )}
                {status === "approved" && (
                  <button onClick={() => handleDownload(artifact)} className="btn btn-primary btn-sm"><Download size={12} /> Download</button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Detail modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/80 backdrop-blur-sm overflow-y-auto py-8 px-4" onClick={() => setModal(null)}>
          <div className="card-raised w-full max-w-2xl animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-700">
              <span className="text-sm font-semibold text-white truncate flex-1">{modal.artifact.title}</span>
              <div className="flex gap-1">
                {(["preview", "provenance", "visual"] as const).filter((p) => p !== "visual" || !!modal.artifact.visualValidation).map((p) => (
                  <button key={p} onClick={() => setModal({ ...modal, panel: p })}
                    className={cn("btn btn-sm capitalize", modal.panel === p ? "btn-primary" : "btn-secondary")}>
                    {p === "visual" ? <><Monitor size={11} /> Visual</> : p}
                  </button>
                ))}
                <button onClick={() => setModal(null)} className="btn btn-ghost btn-sm ml-2">✕</button>
              </div>
            </div>
            <div className="p-5">
              {modal.panel === "preview"    && <ArtifactPreview artifact={modal.artifact} onDownload={handleDownload} />}
              {modal.panel === "provenance" && <ProvenancePanel claims={modal.artifact.provenance} />}
              {modal.panel === "visual"     && modal.artifact.visualValidation && <VisualValidationPanel vv={modal.artifact.visualValidation} />}
            </div>
          </div>
        </div>
      )}

      {/* Reject modal */}
      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm px-4">
          <div className="card-raised w-full max-w-md p-5 space-y-4 animate-fade-in">
            <h3 className="text-base font-semibold text-white">Reject Artefact</h3>
            <p className="text-sm text-slate-400">{rejectTarget.title}</p>
            <div className="space-y-1.5">
              <label className="label">Rejection Reason</label>
              <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} rows={3} placeholder="Describe the issue…" className="textarea" />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setRejectTarget(null)} className="btn btn-secondary">Cancel</button>
              <button onClick={submitReject} className="btn btn-danger"><XCircle size={14} /> Confirm Reject</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
