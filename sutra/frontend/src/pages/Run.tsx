import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Play, Square, ChevronRight, Terminal, AlertTriangle, FlaskConical,
  RefreshCw, CheckCircle, Trash2,
} from "lucide-react";
import { cn, formatDuration, outputTypeMeta } from "@/lib/utils";
import {
  useSessionStore,
  selectConfigs,
  selectActiveJob,
  selectDemoMode,
  selectJobStatus,
} from "@/store/session";
import { jobsApi, outputsApi, streamApi } from "@/api/client";
import { MOCK_JOB, MOCK_ARTIFACTS } from "@/mock/data";
import PipelineStage from "@/components/PipelineStage";
import LayoutFailure from "@/components/LayoutFailure";
import type {
  PipelineStageInfo,
  StageStatus,
  StreamEvent,
  DisplayStageId,
} from "@/types";

// ─── 9 Canonical Verification Stages ───────────────────────────────────────────
export const PIPELINE_9_STAGES: {
  id: DisplayStageId;
  label: string;
  description: string;
  durationMs: number;
}[] = [
  { id: "ingest",                  label: "Ingest",                  description: "Source ingestion, OCR, ASR and text extraction",           durationMs: 1200 },
  { id: "understand",              label: "Understand",              description: "Multimodal comprehension and knowledge graph indexing",      durationMs: 1500 },
  { id: "sot",                     label: "SoT",                     description: "Source of Truth verification, conflict resolution and lock", durationMs: 1300 },
  { id: "validate",                label: "Validate",                description: "Template contracts and parameter validation",               durationMs: 1100 },
  { id: "generate",                label: "Generate",                description: "LLM content generation per output configuration",           durationMs: 2200 },
  { id: "cross_output_validation", label: "Cross-output validation", description: "Factual consistency and contradiction checks across outputs", durationMs: 1400 },
  { id: "render",                  label: "Render",                  description: "Document and asset rendering (PDF/DOCX/HTML)",             durationMs: 1200 },
  { id: "visual_validation",       label: "Visual validation",        description: "Layout integrity, typography and visual quality checks",    durationMs: 1100 },
  { id: "complete",                label: "Complete",                description: "Final artefacts packaged with provenance attestation",      durationMs: 800 },
];

export function mapToDisplayStage(stageId?: string): DisplayStageId {
  if (!stageId) return "ingest";
  const s = stageId.toLowerCase();
  if (s.startsWith("ingest") || s.startsWith("upload") || s.startsWith("ocr")) return "ingest";
  if (s.startsWith("understand") || s.startsWith("sanitize") || s.startsWith("route") || s.startsWith("retrieve") || s.startsWith("extract") || s.startsWith("build_kg")) return "understand";
  if (s.startsWith("sot") || s.startsWith("lock")) return "sot";
  if (s.startsWith("plan") || s.startsWith("template") || (s.startsWith("validate") && !s.includes("fact") && !s.includes("visual"))) return "validate";
  if (s.startsWith("generate")) return "generate";
  if (s.startsWith("cross") || s.includes("validate_facts") || s.includes("consistency")) return "cross_output_validation";
  if (s.startsWith("render")) return "render";
  if (s.includes("visual")) return "visual_validation";
  if (s.startsWith("complete") || s.startsWith("artifact") || s.startsWith("finalize")) return "complete";
  return "ingest";
}

function makePendingStages(): PipelineStageInfo[] {
  return PIPELINE_9_STAGES.map((s) => ({
    id: s.id,
    label: s.label,
    description: s.description,
    status: "pending" as StageStatus,
  }));
}

function makeCompletedStages(): PipelineStageInfo[] {
  return PIPELINE_9_STAGES.map((s) => ({
    id: s.id,
    label: s.label,
    description: s.description,
    status: "done" as StageStatus,
    progress: 100,
    durationMs: s.durationMs,
  }));
}

export default function Run() {
  const navigate      = useNavigate();
  const configs       = useSessionStore(selectConfigs);
  const activeJob     = useSessionStore(selectActiveJob);
  const demoMode      = useSessionStore(selectDemoMode);
  const jobStatus     = useSessionStore(selectJobStatus);
  const storeLog      = useSessionStore((s) => s.streamLog);
  const {
    sessionId,
    setActiveJob,
    updateJob,
    setJobStatus,
    appendLog,
    clearLog,
    addPipelineEvent,
    clearPipelineEvents,
    setArtifacts,
    goToStage,
  } = useSessionStore();

  const isCompletedOnMount = jobStatus === "completed" || activeJob?.status === "completed";

  const [stages, setStages]         = useState<PipelineStageInfo[]>(() =>
    isCompletedOnMount ? makeCompletedStages() : makePendingStages()
  );
  const [running, setRunning]       = useState(false);
  const [done, setDone]             = useState(isCompletedOnMount);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [log, setLog]               = useState<string[]>(() => {
    if (storeLog && storeLog.length > 0) return storeLog;
    return [];
  });

  const esRef     = useRef<EventSource | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const logRef    = useRef<HTMLDivElement>(null);

  const totalStages = stages.length;
  const doneCount   = stages.filter((s) => s.status === "done").length;
  const overallPct  = totalStages > 0 ? Math.round((doneCount / totalStages) * 100) : 0;

  const enabledConfigs = configs.filter((c) => c.enabled);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
      timersRef.current.forEach(clearTimeout);
    };
  }, []);

  function addLog(line: string) {
    setLog((prev) => [...prev.slice(-499), line]);
    appendLog(line);
  }

  function updateStage(id: DisplayStageId, updates: Partial<PipelineStageInfo>) {
    setStages((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  }

  // ── Existing 9-Stage Demo Simulation ───────────────────────────────────────
  function runDemo() {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    esRef.current?.close();

    setRunning(true);
    setDone(false);
    setFatalError(null);
    clearLog();
    setLog([]);
    clearPipelineEvents();
    setStages(makePendingStages());

    const fakejob = { ...MOCK_JOB, status: "running" as const, completedAt: undefined };
    setActiveJob(fakejob as never);
    setJobStatus("running");
    addLog("[DEMO] Starting simulated NTRO pipeline across 9 verification stages…");

    let elapsed = 0;
    PIPELINE_9_STAGES.forEach((stage, idx) => {
      const delay = elapsed;
      const dur   = stage.durationMs;

      timersRef.current.push(
        setTimeout(() => {
          updateStage(stage.id, {
            status: "running",
            startedAt: new Date().toISOString(),
          });
          addLog(`[STAGE START ${idx + 1}/9] ${stage.label}: ${stage.description}`);
          addPipelineEvent({
            type: "stage_start",
            stageId: stage.id,
            timestamp: new Date().toISOString(),
          });
        }, delay),
        setTimeout(() => {
          updateStage(stage.id, {
            status: "done",
            completedAt: new Date().toISOString(),
            durationMs: dur,
            progress: 100,
          });
          addLog(`[STAGE DONE ${idx + 1}/9] ${stage.label} completed (${formatDuration(dur)})`);
          addPipelineEvent({
            type: "stage_done",
            stageId: stage.id,
            timestamp: new Date().toISOString(),
          });

          if (idx === PIPELINE_9_STAGES.length - 1) {
            setRunning(false);
            setDone(true);
            setJobStatus("completed");
            setArtifacts(MOCK_ARTIFACTS);
            goToStage("results");
            addLog("[PIPELINE COMPLETE] All 9 stages verified. 3 trusted artefacts generated.");
          }
        }, delay + dur)
      );
      elapsed += dur;
    });
  }

  // ── Real Backend Execution ─────────────────────────────────────────────────
  async function startPipeline() {
    if (!sessionId || enabledConfigs.length === 0) return;
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    setRunning(true);
    setDone(false);
    setFatalError(null);
    clearLog();
    setLog([]);
    clearPipelineEvents();
    setStages(makePendingStages());

    try {
      addLog(`[INIT] Creating pipeline job for session ${sessionId.slice(0, 12)}…`);
      const jobRes = await jobsApi.create(
        sessionId,
        enabledConfigs.map((c) => c.id),
        { configs: enabledConfigs }
      );
      const job = jobRes.data;
      setActiveJob(job);
      setJobStatus("running");
      addLog(`[JOB CREATED] Job ID: ${job.id}`);

      // Open SSE stream
      let es: EventSource;
      try {
        es = jobsApi.stream(job.id);
      } catch {
        es = streamApi.connect(job.id);
      }
      esRef.current = es;

      es.onmessage = (ev: MessageEvent) => {
        try {
          const event = JSON.parse(ev.data) as StreamEvent;
          addPipelineEvent(event);

          const displayStageId = mapToDisplayStage(event.stageId);

          switch (event.type) {
            case "stage_start":
              updateStage(displayStageId, {
                status: "running",
                startedAt: event.timestamp,
              });
              addLog(`[STAGE START] ${event.stageId ?? displayStageId}`);
              break;

            case "stage_progress":
              if (event.progress != null) {
                updateStage(displayStageId, { progress: event.progress });
              }
              break;

            case "stage_done":
              updateStage(displayStageId, {
                status: "done",
                completedAt: event.timestamp,
                progress: 100,
              });
              addLog(`[STAGE DONE] ${event.stageId ?? displayStageId}`);
              break;

            case "stage_error":
              updateStage(displayStageId, {
                status: "error",
                error: event.message || "Stage failed on backend",
              });
              addLog(`[STAGE ERROR] ${event.stageId ?? displayStageId}: ${event.message}`);
              break;

            case "log":
              if (event.message) addLog(event.message);
              break;

            case "job_done": {
              es.close();
              setRunning(false);
              setDone(true);
              setJobStatus("completed");
              addLog("[JOB COMPLETE] Fetching generated output artefacts…");

              outputsApi
                .list(job.id)
                .catch(() => outputsApi.listBySession(sessionId))
                .then((res) => {
                  if (res?.data) {
                    setArtifacts(res.data);
                  }
                  goToStage("results");
                })
                .catch((err) => {
                  addLog(`[WARN] Could not retrieve outputs: ${err?.message}`);
                });
              break;
            }
          }

          updateJob(job.id, { progress: overallPct });
        } catch {
          // Ignore raw stream heartbeats
        }
      };

      es.onerror = () => {
        es.close();
        setRunning(false);
        setFatalError(
          "Real-time event stream connection lost. The backend job may still be running in the background. You can check results or retry the pipeline."
        );
      };
    } catch (err: unknown) {
      setRunning(false);
      setFatalError(
        err instanceof Error
          ? err.message
          : "Failed to connect to backend /jobs endpoint. Verify backend is running."
      );
    }
  }

  function cancelRun() {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    esRef.current?.close();
    if (activeJob) jobsApi.cancel(activeJob.id).catch(() => {});
    setRunning(false);
    setJobStatus("cancelled");
    setStages((prev) =>
      prev.map((s) =>
        s.status === "running" ? { ...s, status: "error", error: "Cancelled by operator" } : s
      )
    );
    addLog("[PIPELINE CANCELLED] Stopped by operator.");
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="page-title">Live Pipeline Execution</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            {done
              ? "All 9 pipeline stages verified · Outputs ready for review"
              : demoMode
              ? "Simulated 9-stage verified content transformation pipeline"
              : enabledConfigs.length > 0
              ? `${enabledConfigs.length} output${enabledConfigs.length !== 1 ? "s" : ""} · ${enabledConfigs.map((c) => outputTypeMeta[c.type].label).join(", ")}`
              : "No outputs configured"}
          </p>
        </div>

        {/* Action Button Controls — always visible without scrolling */}
        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {running && (
            <button onClick={cancelRun} className="btn btn-danger">
              <Square size={13} /> Cancel Run
            </button>
          )}

          {/* Run Demo Simulation Button — clearly visible near View Results */}
          {!running && (
            <button
              onClick={runDemo}
              className="btn btn-secondary btn-lg gap-2 text-purple-300 border-purple-700 bg-purple-950/40 hover:bg-purple-900/60 hover:border-purple-500 shadow-sm"
              title="Run the 9-stage demo simulation"
            >
              <FlaskConical size={16} className="text-purple-400" />
              <span>Run Demo Simulation</span>
            </button>
          )}

          {/* Real Pipeline Execution (when not in pure demo mode and not running) */}
          {!running && !demoMode && (
            <button
              onClick={startPipeline}
              disabled={enabledConfigs.length === 0 || !sessionId}
              className="btn btn-primary btn-lg"
            >
              <Play size={16} /> Start Real Pipeline
            </button>
          )}

          {/* View Results Button */}
          {done && (
            <button
              onClick={() => { goToStage("results"); navigate("/results"); }}
              className="btn btn-success btn-lg"
            >
              <CheckCircle size={16} /> View Results
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar Card */}
      {(running || done) && (
        <div className="card p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-300 font-medium">
              {done ? "All 9 stages verified" : "Transforming content…"}
            </span>
            <span className="font-mono text-blue-400 font-semibold">{overallPct}%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                done ? "bg-emerald-500" : "bg-blue-500"
              )}
              style={{ width: `${overallPct}%` }}
            />
          </div>
          <div className="text-xs text-slate-500 flex justify-between items-center">
            <span>{doneCount} of {totalStages} stages complete</span>
            <span className="font-mono text-[11px] text-slate-400">
              One Source → One Verified Truth → Multiple Trusted Outputs
            </span>
          </div>
        </div>
      )}

      {/* Fatal Error Notice */}
      {fatalError && (
        <div className="space-y-3">
          <LayoutFailure
            title="Pipeline Connection Notice"
            message={fatalError}
            stageLabel="backend-stream"
            onRetry={demoMode ? runDemo : startPipeline}
          />
          {!demoMode && (
            <div className="flex justify-end">
              <button
                onClick={() => { setFatalError(null); runDemo(); }}
                className="btn btn-secondary btn-sm gap-1.5 text-purple-300 border-purple-800"
              >
                <FlaskConical size={12} className="text-purple-400" />
                <span>Simulate Run in Demo Mode</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* No configs warning */}
      {!demoMode && enabledConfigs.length === 0 && (
        <div className="flex items-center gap-3 p-4 rounded-xl border border-yellow-900 bg-yellow-950/20 text-yellow-400 text-sm">
          <AlertTriangle size={16} className="shrink-0" />
          <span>
            No output configurations enabled.{" "}
            <a href="/configure" className="underline ml-1 hover:text-yellow-200">
              Configure target outputs first
            </a>
          </span>
        </div>
      )}

      {/* Main Grid: Stages on Left, Live Log on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Stage List Card */}
        <div className="lg:col-span-2 card p-5 space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <div className="label">Pipeline Execution Stages (9 Verification Phases)</div>
            <div className="text-xs text-slate-500 mt-0.5">
              Automated multimodal transformation and provenance validation
            </div>
          </div>

          <div className="space-y-0 pt-1">
            {stages.map((stage, idx) => (
              <PipelineStage
                key={stage.id}
                stage={stage}
                index={idx}
                total={stages.length}
                variant="full"
              />
            ))}
          </div>
        </div>

        {/* Live Monospace Log Card */}
        <div className="card flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
            <Terminal size={14} className="text-slate-400" />
            <span className="label">Live Stream Log</span>
            <span className="text-[10px] text-slate-500 font-mono ml-auto">
              {log.length} events
            </span>
            {log.length > 0 && (
              <button
                onClick={() => { setLog([]); clearLog(); }}
                className="btn-ghost btn-sm p-1 text-slate-500 hover:text-slate-300"
                title="Clear log"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
          <div
            ref={logRef}
            className="flex-1 overflow-y-auto p-3 font-mono text-[11px] text-slate-400 leading-relaxed scrollbar-none"
            style={{ maxHeight: 520, minHeight: 320 }}
          >
            {log.length === 0 ? (
              <div className="text-slate-700 italic">
                Click &quot;Run Demo Simulation&quot; to begin simulated execution…
              </div>
            ) : (
              log.map((line, i) => (
                <div
                  key={i}
                  className={cn(
                    line.includes("[ERROR]") || line.includes("failed")
                      ? "text-red-400 font-semibold"
                      : line.includes("[STAGE DONE") || line.includes("COMPLETE")
                      ? "text-emerald-400"
                      : line.includes("[STAGE START") || line.includes("[INIT]")
                      ? "text-blue-400"
                      : line.includes("[DEMO]")
                      ? "text-purple-400"
                      : "text-slate-500"
                  )}
                >
                  {line}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
