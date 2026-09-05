import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck, Lock, AlertTriangle, Loader,
  ChevronRight, Tag, FileSearch, RefreshCw, FlaskConical,
} from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { useSessionStore, selectSOT, selectSource, selectSotLockHash, selectDemoMode } from "@/store/session";
import { sotApi } from "@/api/client";
import GraphView from "@/components/GraphView";
import type { EntityType } from "@/types";

const ENTITY_TYPE_COLORS: Record<EntityType, string> = {
  person:       "bg-blue-900/40 text-blue-300 border-blue-800",
  organization: "bg-cyan-900/40 text-cyan-300 border-cyan-800",
  location:     "bg-emerald-900/40 text-emerald-300 border-emerald-800",
  date:         "bg-amber-900/40 text-amber-300 border-amber-800",
  event:        "bg-purple-900/40 text-purple-300 border-purple-800",
  claim:        "bg-slate-700/40 text-slate-300 border-slate-700",
  fact:         "bg-green-900/40 text-green-300 border-green-800",
  numeric:      "bg-indigo-900/40 text-indigo-300 border-indigo-800",
  technical:    "bg-rose-900/40 text-rose-300 border-rose-800",
};

export default function Truth() {
  const navigate = useNavigate();
  const sot         = useSessionStore(selectSOT);
  const source      = useSessionStore(selectSource);
  const lockHash    = useSessionStore(selectSotLockHash);
  const demoMode    = useSessionStore(selectDemoMode);
  const sessionId   = useSessionStore((s) => s.sessionId);
  const { setSOT, setSotLockPending, setSotLockHash, goToStage, seedDemo } = useSessionStore();

  const [loading, setLoading]       = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [lockModal, setLockModal]   = useState(false);
  const [locking, setLocking]       = useState(false);
  const [lockError, setLockError]   = useState<string | null>(null);
  const [activeTab, setActiveTab]   = useState<"entities" | "graph" | "raw">("entities");
  const [filterType, setFilterType] = useState<EntityType | "all">("all");

  // Fetch real SoT from backend if source exists but SoT is not yet in store
  useEffect(() => {
    if (sot || !source || demoMode) return;

    let mounted = true;
    async function fetchSot() {
      setLoading(true);
      setFetchError(null);
      try {
        let res;
        try {
          res = await sotApi.get(source!.id);
        } catch (err: unknown) {
          if (sessionId) {
            res = await sotApi.getBySession(sessionId);
          } else {
            throw err;
          }
        }
        if (mounted && res?.data) {
          setSOT(res.data);
          if (res.data.lockHash || res.data.hash) {
            setSotLockHash(res.data.lockHash || res.data.hash || null);
          }
        }
      } catch (err: unknown) {
        if (mounted) {
          const msg = err instanceof Error ? err.message : "Failed to load Source of Truth from backend.";
          setFetchError(msg);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchSot();
    return () => { mounted = false; };
  }, [source, sot, sessionId, demoMode, setSOT, setSotLockHash]);

  // Guard: no source uploaded yet
  if (!source) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500">
        <FileSearch size={32} className="text-slate-700" />
        <p className="text-sm">No source uploaded yet. <a href="/upload" className="text-blue-400 hover:underline">Upload a source</a> first.</p>
        <button onClick={() => { seedDemo(); navigate("/truth"); }} className="btn btn-secondary btn-sm gap-1.5 text-purple-300 border-purple-800">
          <FlaskConical size={13} className="text-purple-400" /> Load Demo Data
        </button>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-400">
        <Loader size={28} className="animate-spin text-blue-500" />
        <p className="text-sm font-medium text-slate-200">Retrieving Source of Truth from backend…</p>
        <p className="mono-sm text-slate-500">Source: {source.name}</p>
      </div>
    );
  }

  // Error fetching SOT
  if (!sot && fetchError) {
    return (
      <div className="max-w-xl mx-auto space-y-4 p-5 rounded-xl bg-red-950/20 border border-red-900 text-slate-200">
        <div className="flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-red-300">Source of Truth Not Ready</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{fetchError}</p>
            <p className="text-xs text-slate-500 mt-2">
              The backend may still be processing this source or routes_sot.py is not yet responding.
            </p>
          </div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button
            onClick={() => {
              setLoading(true);
              setFetchError(null);
              sotApi.get(source.id)
                .then((r) => setSOT(r.data))
                .catch((e) => setFetchError(e instanceof Error ? e.message : "Retry failed"))
                .finally(() => setLoading(false));
            }}
            className="btn btn-secondary btn-sm gap-1"
          >
            <RefreshCw size={12} /> Retry Fetch
          </button>
          <button
            onClick={() => { seedDemo(); navigate("/truth"); }}
            className="btn btn-primary btn-sm gap-1.5 text-purple-100 bg-purple-700 hover:bg-purple-600"
          >
            <FlaskConical size={13} /> Use Demo SOT
          </button>
        </div>
      </div>
    );
  }

  if (!sot) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500">
        <Loader size={28} className="animate-spin text-blue-500" />
        <p className="text-sm">Analysing source — extracting entities and building knowledge graph…</p>
        <p className="mono-sm text-slate-600">{source.name}</p>
      </div>
    );
  }

  const isLocked = sot.status === "locked";
  const displayHash = lockHash || sot.lockHash || sot.hash;
  const filteredEntities = filterType === "all"
    ? sot.entities
    : sot.entities.filter((e) => e.type === filterType);
  const entityTypes = [...new Set(sot.entities.map((e) => e.type))];

  async function handleLock() {
    setLocking(true);
    setLockError(null);
    setSotLockPending(true);
    try {
      const res = await sotApi.lock(sot!.id);
      setSOT(res.data);
      if (res.data.lockHash || res.data.hash) {
        setSotLockHash(res.data.lockHash || res.data.hash || null);
      }
      setLockModal(false);
      goToStage("configure");
      setTimeout(() => navigate("/configure"), 600);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to lock SOT on the backend.";
      setLockError(msg);
    } finally {
      setLocking(false);
      setSotLockPending(false);
    }
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Status banner */}
      <div className={cn(
        "flex items-center justify-between gap-4 px-4 py-3 rounded-xl border",
        isLocked
          ? "bg-amber-950/20 border-amber-800"
          : "bg-slate-900 border-slate-800"
      )}>
        <div className="flex items-center gap-3">
          {isLocked
            ? <Lock size={18} className="text-amber-400 shrink-0" />
            : <ShieldCheck size={18} className="text-blue-400 shrink-0" />}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-200">
                {isLocked ? "Source of Truth — LOCKED" : "Source of Truth — DRAFT"}
              </span>
              {displayHash && (
                <span className="text-[10px] font-mono text-amber-300 bg-amber-950/60 border border-amber-800 px-1.5 py-0.5 rounded">
                  HASH: {displayHash.slice(0, 16)}…
                </span>
              )}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              {sot.wordCount} words · {sot.entities.length} entities · {sot.relations.length} relations
              {isLocked && sot.lockedAt && ` · Sealed ${formatDate(sot.lockedAt)}`}
            </div>
          </div>
        </div>
        {!isLocked && (
          <button onClick={() => setLockModal(true)} className="btn btn-lock shrink-0">
            <Lock size={14} /> Lock SOT
          </button>
        )}
        {isLocked && (
          <span className="text-xs text-amber-400 font-semibold px-2 py-1 rounded bg-amber-900/30 border border-amber-800 shrink-0">
            IMMUTABLE
          </span>
        )}
      </div>

      {/* Summary card */}
      <div className="card p-4">
        <div className="label mb-2">Verified AI Knowledge Summary</div>
        <p className="text-sm text-slate-200 leading-relaxed">{sot.summary}</p>
        <div className="flex gap-4 mt-3 text-[11px] text-slate-500 font-mono">
          <span>Source: {source.name}</span>
          <span>Lang: {sot.language.toUpperCase()}</span>
          <span>Words: {sot.wordCount.toLocaleString()}</span>
          {displayHash && <span className="text-slate-400">LockHash: {displayHash.slice(0, 12)}…</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900 border border-slate-800 rounded-xl w-fit">
        {(["entities", "graph", "raw"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors",
              activeTab === tab ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"
            )}
          >
            {tab === "entities" ? `Entities (${sot.entities.length})` :
             tab === "graph"    ? `Knowledge Graph (${sot.relations.length})` : "Raw Text"}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "entities" && (
        <div className="space-y-3">
          {/* Type filter */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setFilterType("all")}
              className={cn("btn btn-sm", filterType === "all" ? "btn-primary" : "btn-secondary")}
            >
              All ({sot.entities.length})
            </button>
            {entityTypes.map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={cn(
                  "btn btn-sm capitalize",
                  filterType === t ? "btn-primary" : "btn-secondary"
                )}
              >
                {t} ({sot.entities.filter((e) => e.type === t).length})
              </button>
            ))}
          </div>

          {/* Entity list */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {filteredEntities.map((entity) => (
              <div
                key={entity.id}
                className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-900 border border-slate-800"
              >
                <Tag size={13} className="text-slate-500 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-slate-100 font-medium">{entity.text}</span>
                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded border capitalize", ENTITY_TYPE_COLORS[entity.type])}>
                      {entity.type}
                    </span>
                  </div>
                  {entity.normalized && entity.normalized !== entity.text && (
                    <div className="text-[11px] text-slate-500 mt-0.5 font-mono">{entity.normalized}</div>
                  )}
                  <div className="flex items-center gap-2 mt-1.5">
                    <div className="w-16 h-1 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${Math.round(entity.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">
                      {Math.round(entity.confidence * 100)}%
                    </span>
                    {entity.sourceRef.page != null && (
                      <span className="text-[10px] text-slate-600 font-mono ml-auto">p.{entity.sourceRef.page}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "graph" && (
        <GraphView entities={sot.entities} relations={sot.relations} />
      )}

      {activeTab === "raw" && (
        <div className="card p-4">
          <div className="label mb-2">Extracted Raw Text</div>
          <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto scrollbar-none">
            {sot.rawText}
          </pre>
        </div>
      )}

      {/* Navigation footer */}
      {!isLocked && (
        <div className="flex justify-end pt-2">
          <button onClick={() => setLockModal(true)} className="btn btn-lock btn-lg">
            <Lock size={16} /> Lock & Proceed to Configure
          </button>
        </div>
      )}
      {isLocked && (
        <div className="flex justify-end pt-2">
          <button
            onClick={() => { goToStage("configure"); navigate("/configure"); }}
            className="btn btn-primary btn-lg"
          >
            Continue to Configure <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Lock confirmation modal */}
      {lockModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="card-raised w-full max-w-md mx-4 p-6 space-y-4 animate-fade-in">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-900/40 border border-amber-800 flex items-center justify-center shrink-0">
                <AlertTriangle size={18} className="text-amber-400" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Lock Source of Truth?</h3>
                <p className="text-sm text-slate-400 mt-1 leading-relaxed">
                  Locking is <strong className="text-amber-400">irreversible</strong>. The SOT will be sealed
                  with a cryptographic lock hash on the backend and become the immutable baseline for all generated outputs.
                </p>
              </div>
            </div>

            {lockError && (
              <div className="flex items-center gap-2 text-xs text-red-400 bg-red-950/30 border border-red-900 rounded-lg px-3 py-2">
                <AlertTriangle size={13} className="shrink-0" />
                <span>{lockError}</span>
              </div>
            )}

            <div className="flex gap-2 justify-end pt-1">
              <button
                onClick={() => { setLockModal(false); setLockError(null); }}
                className="btn btn-secondary"
                disabled={locking}
              >
                Cancel
              </button>
              <button onClick={handleLock} className="btn btn-lock" disabled={locking}>
                {locking ? <><Loader size={14} className="animate-spin" /> Locking…</> : <><Lock size={14} /> Confirm Lock</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
