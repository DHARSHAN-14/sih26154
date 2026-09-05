import { useNavigate } from "react-router-dom";
import {
  Upload, ShieldCheck, Settings2, Play, FileOutput,
  History, Activity, Database, Server, Lock,
  CheckCircle, Clock, AlertTriangle, Zap, ChevronRight,
  FlaskConical,
} from "lucide-react";
import { cn, formatDate, formatBytes, shortId } from "@/lib/utils";
import { useSessionStore, selectDemoMode } from "@/store/session";
import SecurityBadge from "@/components/SecurityBadge";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  Icon: React.ElementType;
}

function StatCard({ label, value, sub, color = "text-blue-400", Icon }: StatCardProps) {
  return (
    <div className="card p-4 flex items-start gap-3">
      <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
        <Icon size={16} className={color} />
      </div>
      <div>
        <div className={cn("text-2xl font-bold tabular-nums", color)}>{value}</div>
        <div className="text-xs text-slate-400 font-medium mt-0.5">{label}</div>
        {sub && <div className="text-[10px] text-slate-600 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

const SYSTEM_SERVICES = [
  { label: "API Gateway",      status: "online",  color: "bg-emerald-500" },
  { label: "Pipeline Engine",  status: "ready",   color: "bg-emerald-500" },
  { label: "Model Registry",   status: "online",  color: "bg-emerald-500" },
  { label: "Knowledge Graph",  status: "online",  color: "bg-emerald-500" },
  { label: "SOT Vault",        status: "sealed",  color: "bg-amber-500"   },
  { label: "Render Service",   status: "online",  color: "bg-emerald-500" },
];

const PIPELINE_STEPS = [
  { path: "/upload",    label: "Upload Source",     Icon: Upload,      desc: "Ingest document, image, audio or video" },
  { path: "/truth",     label: "Source of Truth",   Icon: ShieldCheck, desc: "Extract, verify and lock knowledge graph" },
  { path: "/configure", label: "Configure Outputs", Icon: Settings2,   desc: "Set type, tone, model and classification" },
  { path: "/run",       label: "Run Pipeline",      Icon: Play,        desc: "Execute 13-stage AI transformation" },
  { path: "/results",   label: "Review & Approve",  Icon: FileOutput,  desc: "Validate, approve and export artefacts" },
  { path: "/versions",  label: "Version History",   Icon: History,     desc: "Audit trail and version management" },
];

export default function Dashboard() {
  const navigate   = useNavigate();
  const session    = useSessionStore((s) => s.session);
  const demoMode   = useSessionStore(selectDemoMode);
  const seedDemo   = useSessionStore((s) => s.seedDemo);
  const reviews    = useSessionStore((s) => s.reviews);
  const currentStage = useSessionStore((s) => s.currentStage);

  const stageIndex = PIPELINE_STEPS.findIndex((s) => s.path === `/${currentStage}`);

  const approvedCount = Object.values(reviews).filter((r) => r.status === "approved").length;
  const pendingCount  = Object.values(reviews).filter((r) => r.status === "pending").length;
  const artifactCount = session?.artifacts.length ?? 0;

  function handleLoadDemo() {
    seedDemo();
    setTimeout(() => navigate("/results"), 300);
  }

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="page-title">Operator Dashboard</h2>
          <p className="text-sm text-slate-400 mt-1">
            SUTRA · Gen AI Content Transformation Platform · SIH 2026 · NTRO
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          {!demoMode && (
            <button
              onClick={handleLoadDemo}
              className="btn btn-secondary gap-2"
              title="Load full demo dataset to preview all pages without a backend"
            >
              <FlaskConical size={14} className="text-purple-400" />
              <span className="text-purple-300">Load Demo</span>
            </button>
          )}
          <button
            onClick={() => navigate("/upload")}
            className="btn btn-primary"
          >
            <Upload size={14} /> New Session
          </button>
        </div>
      </div>

      {/* ── Demo mode banner ──────────────────────────────────────────────── */}
      {demoMode && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-purple-800 bg-purple-950/30 text-purple-300 text-sm">
          <FlaskConical size={16} className="shrink-0" />
          <span>
            <strong>Demo Mode active</strong> — All pages are populated with realistic NTRO demo data. No backend required.
          </span>
          <button
            onClick={() => { useSessionStore.getState().reset(); }}
            className="ml-auto text-[11px] text-purple-400 hover:text-purple-200 transition-colors underline shrink-0"
          >
            Exit demo
          </button>
        </div>
      )}

      {/* ── Stat cards ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Active Sessions"
          value={session ? 1 : 0}
          sub={session ? shortId(session.id) : "—"}
          Icon={Activity}
          color="text-blue-400"
        />
        <StatCard
          label="Artefacts Generated"
          value={artifactCount}
          sub={artifactCount > 0 ? `${approvedCount} approved` : "—"}
          Icon={FileOutput}
          color="text-emerald-400"
        />
        <StatCard
          label="Pending Review"
          value={pendingCount}
          sub={pendingCount > 0 ? "Action required" : "All reviewed"}
          Icon={Clock}
          color={pendingCount > 0 ? "text-amber-400" : "text-slate-400"}
        />
        <StatCard
          label="SOT Status"
          value={session?.sot?.status === "locked" ? "LOCKED" : session?.sot ? "DRAFT" : "—"}
          sub={session?.sot?.lockedAt ? `Locked ${formatDate(session.sot.lockedAt)}` : undefined}
          Icon={Lock}
          color={session?.sot?.status === "locked" ? "text-amber-400" : "text-slate-500"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Current session ─────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">

          {session ? (
            <div className="card p-4 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="section-title flex items-center gap-2">
                  <Database size={14} className="text-slate-500" />
                  Current Session
                </div>
                <SecurityBadge level={session.classification} variant="pill" />
              </div>

              {/* Session meta */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
                {[
                  { label: "Session ID",  value: session.id.slice(0, 20) + "…" },
                  { label: "Operator",    value: session.operatorId },
                  { label: "Source",      value: session.source?.name ?? "—" },
                  { label: "Source Size", value: session.source ? formatBytes(session.source.sizeBytes) : "—" },
                  { label: "Created",     value: formatDate(session.createdAt) },
                  { label: "Artefacts",   value: String(artifactCount) },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">{label}</div>
                    <div className="font-mono text-slate-300 truncate">{value}</div>
                  </div>
                ))}
              </div>

              {/* Pipeline progress bar */}
              <div>
                <div className="flex justify-between text-[11px] text-slate-500 mb-1.5">
                  <span>Pipeline progress</span>
                  <span className="font-mono">{Math.round(((stageIndex + 1) / PIPELINE_STEPS.length) * 100)}%</span>
                </div>
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${Math.round(((stageIndex + 1) / PIPELINE_STEPS.length) * 100)}%` }}
                  />
                </div>
                <div className="mt-1.5 text-[11px] text-slate-500">
                  Current stage: <span className="text-blue-400 font-medium capitalize">{currentStage}</span>
                </div>
              </div>

              {/* Artefacts summary */}
              {artifactCount > 0 && (
                <div className="space-y-1.5">
                  <div className="label">Artefacts</div>
                  {session.artifacts.map((art) => {
                    const rv = reviews[art.id];
                    return (
                      <div key={art.id} className="flex items-center gap-2 text-xs">
                        {rv?.status === "approved" ? (
                          <CheckCircle size={12} className="text-emerald-400 shrink-0" />
                        ) : rv?.status === "rejected" ? (
                          <AlertTriangle size={12} className="text-red-400 shrink-0" />
                        ) : (
                          <Clock size={12} className="text-amber-400 shrink-0" />
                        )}
                        <span className="text-slate-300 truncate flex-1">{art.title}</span>
                        <SecurityBadge level={art.classification} variant="pill" className="shrink-0" />
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-1">
                <button onClick={() => navigate(`/${currentStage}`)} className="btn btn-primary btn-sm">
                  Continue <ChevronRight size={12} />
                </button>
                {artifactCount > 0 && (
                  <button onClick={() => navigate("/results")} className="btn btn-secondary btn-sm">
                    <FileOutput size={12} /> View Results
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* No session empty state */
            <div className="card p-8 flex flex-col items-center justify-center gap-4 text-center">
              <div className="w-14 h-14 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center">
                <Zap size={24} className="text-slate-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-300">No active session</p>
                <p className="text-xs text-slate-500 mt-1">
                  Start a new session by uploading a source document,<br />
                  or load the demo to explore the full interface.
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => navigate("/upload")} className="btn btn-primary">
                  <Upload size={14} /> New Session
                </button>
                <button onClick={handleLoadDemo} className="btn btn-secondary">
                  <FlaskConical size={14} className="text-purple-400" />
                  <span className="text-purple-300">Load Demo</span>
                </button>
              </div>
            </div>
          )}

          {/* ── Pipeline quick-nav ──────────────────────────────────────────── */}
          <div className="card p-4">
            <div className="section-title mb-3 flex items-center gap-2">
              <Play size={13} className="text-slate-500" />
              Pipeline Steps
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {PIPELINE_STEPS.map((step, idx) => {
                const isCurrent = `/${currentStage}` === step.path;
                const isDone    = idx < stageIndex;
                return (
                  <button
                    key={step.path}
                    onClick={() => navigate(step.path)}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border text-left transition-colors",
                      isCurrent
                        ? "border-blue-700 bg-blue-950/40"
                        : "border-slate-800 bg-slate-900 hover:border-slate-700"
                    )}
                  >
                    <div className={cn(
                      "w-7 h-7 rounded-full flex items-center justify-center shrink-0",
                      isDone    ? "bg-emerald-900/50 border border-emerald-700" :
                      isCurrent ? "bg-blue-600" : "bg-slate-800 border border-slate-700"
                    )}>
                      {isDone
                        ? <CheckCircle size={13} className="text-emerald-400" />
                        : <step.Icon size={13} className={isCurrent ? "text-white" : "text-slate-500"} />}
                    </div>
                    <div className="min-w-0">
                      <div className={cn("text-xs font-semibold truncate", isCurrent ? "text-blue-300" : isDone ? "text-emerald-400" : "text-slate-400")}>
                        {step.label}
                      </div>
                      <div className="text-[10px] text-slate-600 truncate">{step.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Right column ────────────────────────────────────────────────── */}
        <div className="space-y-4">

          {/* System status */}
          <div className="card p-4">
            <div className="section-title mb-3 flex items-center gap-2">
              <Server size={13} className="text-slate-500" />
              System Status
            </div>
            <div className="space-y-2">
              {SYSTEM_SERVICES.map((svc) => (
                <div key={svc.label} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-slate-400">
                    <span className={cn("w-1.5 h-1.5 rounded-full", svc.color)} />
                    {svc.label}
                  </div>
                  <span className={cn(
                    "font-mono text-[10px] uppercase tracking-wider",
                    svc.status === "online" || svc.status === "ready"
                      ? "text-emerald-400" : "text-amber-400"
                  )}>
                    {svc.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Platform info */}
          <div className="card p-4 space-y-3">
            <div className="section-title">Platform</div>
            <div className="space-y-2 text-xs">
              {[
                { label: "Project",    value: "SIH26154" },
                { label: "Org",        value: "NTRO" },
                { label: "Version",    value: "v0.1.0-alpha" },
                { label: "Pipeline",   value: "13 stages" },
                { label: "Models",     value: "4 supported" },
                { label: "Languages",  value: "8 supported" },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-slate-500">{label}</span>
                  <span className="font-mono text-slate-300">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Principle */}
          <div className="card p-4 border-blue-900/50 bg-blue-950/10">
            <div className="text-center space-y-1">
              <div className="text-[10px] text-blue-500 uppercase tracking-widest">Core Principle</div>
              <div className="text-sm font-semibold text-blue-200 leading-snug">
                One Source.<br />One Verified Truth.<br />Multiple Trusted Outputs.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
