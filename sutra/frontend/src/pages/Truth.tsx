import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck, Lock, AlertTriangle, Loader,
  ChevronRight, Tag, FileSearch, RefreshCw, FlaskConical,
  Search, Database, Cpu, Sparkles,
} from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { useSessionStore, selectSOT, selectSource, selectSotLockHash, selectDemoMode } from "@/store/session";
import { sotApi, retrievalApi, type RetrievalResult, type RetrievalStatus } from "@/api/client";
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
  const [activeTab, setActiveTab]   = useState<"entities" | "graph" | "raw" | "retrieval">("entities");
  const [filterType, setFilterType] = useState<EntityType | "all">("all");
  const [ragQuery, setRagQuery]     = useState("");
  const [ragLoading, setRagLoading] = useState(false);
  const [ragResults, setRagResults] = useState<RetrievalResult[] | null>(null);
  const [ragStatus, setRagStatus]   = useState<RetrievalStatus | null>(null);
  const [ragError, setRagError]     = useState<string | null>(null);

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

  // Fetch RAG status when retrieval tab is active
  useEffect(() => {
    if (activeTab === "retrieval" && sessionId && !ragStatus && !demoMode) {
      retrievalApi.getStatus(sessionId)
        .then((res) => setRagStatus(res.data))
        .catch(() => {});
    }
  }, [activeTab, sessionId, ragStatus, demoMode]);

  async function handleRagSearch(q?: string) {
    const queryText = (q || ragQuery).trim();
    if (!queryText) return;
    setRagLoading(true);
    setRagError(null);
    try {
      if (demoMode) {
        setRagResults([
          {
            chunk_id: "demo-chk-01",
            text: "State-sponsored actor APT-X41 conducted coordinated intrusions across 47 industrial control systems belonging to NPGC.",
            page: 2,
            paragraph: 1,
            doc_id: "demo-doc-01",
            dense_score: 0.88,
            sparse_score: 4.12,
            rrf_score: 0.0325,
            rerank_score: 0.94,
            matched_terms: queryText.toLowerCase().split(" ").filter((w) => w.length > 3),
          },
          {
            chunk_id: "demo-chk-02",
            text: "Zero-day vulnerability CVE-2026-7381 (CVSS 9.9) in SCADA middleware exploited with Cobalt Strike beacon persistence.",
            page: 3,
            paragraph: 3,
            doc_id: "demo-doc-01",
            dense_score: 0.84,
            sparse_score: 3.85,
            rrf_score: 0.0318,
            rerank_score: 0.91,
            matched_terms: queryText.toLowerCase().split(" ").filter((w) => w.length > 3),
          },
        ]);
      } else if (sessionId) {
        const res = await retrievalApi.query(sessionId, queryText, 5);
        setRagResults(res.data.results);
      }
    } catch (err: unknown) {
      setRagError(err instanceof Error ? err.message : "Failed to query RAG vector store");
    } finally {
      setRagLoading(false);
    }
  }

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
        {(["entities", "graph", "raw", "retrieval"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors flex items-center gap-1.5",
              activeTab === tab ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"
            )}
          >
            {tab === "entities"  ? `Entities (${sot.entities.length})` :
             tab === "graph"     ? `Knowledge Graph (${sot.relations.length})` :
             tab === "raw"       ? "Raw Text" : "RAG Explorer"}
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
        <div className="card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="label">Extracted Document Text</div>
            {sot.pages && sot.pages.length > 1 && (
              <span className="text-xs text-blue-400 font-mono">
                {sot.pages.length} Pages Extracted
              </span>
            )}
          </div>
          {sot.pages && sot.pages.length > 0 ? (
            <div className="space-y-3 max-h-[480px] overflow-y-auto scrollbar-none pr-1">
              {sot.pages.map((p) => (
                <div key={p.page} className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800/80">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-[11px] font-mono text-slate-400">
                    <span className="text-blue-400 font-semibold">Page {p.page}</span>
                    <span>{p.text.split(/\s+/).filter(Boolean).length} words</span>
                  </div>
                  <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {p.text}
                  </pre>
                </div>
              ))}
            </div>
          ) : (
            <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto scrollbar-none">
              {sot.rawText}
            </pre>
          )}
        </div>
      )}

      {/* RAG / Retrieval Explorer */}
      {activeTab === "retrieval" && (
        <div className="space-y-4">
          {/* Header & Status Banner */}
          <div className="card p-4 bg-slate-900/90 border border-slate-800">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Database size={18} className="text-blue-400" />
                <span className="text-sm font-semibold text-white">Hybrid Retrieval Engine</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-900/40 text-blue-300 border border-blue-800">
                  Dense Cosine + Sparse BM25 + RRF + Reranker
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "text-xs px-2.5 py-1 rounded-md font-mono font-medium border",
                    ragStatus?.route === "B"
                      ? "bg-purple-950/60 text-purple-300 border-purple-800"
                      : "bg-emerald-950/60 text-emerald-300 border-emerald-800"
                  )}
                >
                  {ragStatus?.route === "B" ? "ROUTE B: HYBRID RAG" : "ROUTE A: IN-CONTEXT"}
                </span>
                {ragStatus && (
                  <span className="text-xs text-slate-400 font-mono bg-slate-800 px-2 py-1 rounded">
                    {ragStatus.indexed_chunks} Chunks Indexed
                  </span>
                )}
              </div>
            </div>

            {/* Query Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleRagSearch();
              }}
              className="flex gap-2 mt-4"
            >
              <div className="relative flex-1">
                <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  placeholder="Ask a question or search passages (e.g. CVE vulnerability, threat actor, mitigation port)..."
                  className="w-full pl-10 pr-4 py-2 bg-slate-950/80 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
              <button
                type="submit"
                disabled={ragLoading || !ragQuery.trim()}
                className="btn btn-primary px-5 py-2 text-sm flex items-center gap-1.5"
              >
                {ragLoading ? <Loader size={15} className="animate-spin" /> : <Search size={15} />}
                <span>Retrieve</span>
              </button>
            </form>

            {/* Quick suggestions */}
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-2 text-xs text-slate-400">
              <span className="text-slate-500">Suggestions:</span>
              {[
                "Vulnerability CVE and CVSS rating",
                "Attributed threat actor and targets",
                "Mitigation port and containment actions",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => {
                    setRagQuery(suggestion);
                    handleRagSearch(suggestion);
                  }}
                  className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Error Message */}
          {ragError && (
            <div className="p-3 bg-red-950/30 border border-red-900 rounded-lg text-xs text-red-300">
              {ragError}
            </div>
          )}

          {/* Results List */}
          {ragResults && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono px-1">
                <span>Retrieved {ragResults.length} Relevant Passages</span>
                <span>Sorted by Cross-Encoder Rerank Score</span>
              </div>

              {ragResults.length === 0 ? (
                <div className="p-8 text-center text-sm text-slate-500 card">
                  No matching passages found. Try a different query or keyword.
                </div>
              ) : (
                ragResults.map((res, idx) => (
                  <div key={res.chunk_id || idx} className="card p-4 space-y-3 bg-slate-900/70 border border-slate-800">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono font-bold">
                          #{idx + 1}
                        </span>
                        <span className="font-mono text-slate-400">
                          Chunk: <span className="text-slate-200">{res.chunk_id}</span>
                        </span>
                        {res.page > 0 && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                            Page {res.page}
                          </span>
                        )}
                      </div>

                      {/* Scores Breakdown */}
                      <div className="flex items-center gap-2 text-[11px] font-mono">
                        <span className="px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300 font-semibold">
                          Rerank: {res.rerank_score}
                        </span>
                        <span className="text-slate-400">Dense: {res.dense_score}</span>
                        <span className="text-slate-400">BM25: {res.sparse_score}</span>
                      </div>
                    </div>

                    {/* Matched Keywords */}
                    {res.matched_terms && res.matched_terms.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] text-slate-500 font-mono">Matched:</span>
                        {res.matched_terms.map((t) => (
                          <span
                            key={t}
                            className="px-1.5 py-0.5 rounded bg-amber-950/40 border border-amber-800/80 text-amber-300 font-mono text-[11px]"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Passage text */}
                    <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap border border-slate-800/60">
                      {res.text}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
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
