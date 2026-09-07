import { useState, useMemo } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Search,
  X,
  Shield,
  Layers,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SOTEntity, SOTRelation } from "@/types";

interface Props {
  entities: SOTEntity[];
  relations: SOTRelation[];
  className?: string;
}

const ENTITY_COLORS: Record<string, { fill: string; stroke: string; text: string; label: string }> = {
  organization: { fill: "#132d3e", stroke: "#06b6d4", text: "#67e8f9", label: "Organization" },
  technical:    { fill: "#2d1616", stroke: "#f87171", text: "#fca5a5", label: "Technical" },
  event:        { fill: "#2b1842", stroke: "#a855f7", text: "#d8b4fe", label: "Event / Directive" },
  location:     { fill: "#132d20", stroke: "#10b981", text: "#6ee7b7", label: "Location" },
  numeric:      { fill: "#1a1a36", stroke: "#818cf8", text: "#c7d2fe", label: "Metric" },
  date:         { fill: "#362908", stroke: "#f59e0b", text: "#fcd34d", label: "Date" },
  person:       { fill: "#172d4a", stroke: "#3b82f6", text: "#93c5fd", label: "Person" },
  claim:        { fill: "#1a1e24", stroke: "#94a3b8", text: "#cbd5e1", label: "Claim" },
  fact:         { fill: "#142914", stroke: "#4ade80", text: "#86efac", label: "Fact" },
};

const W = 760;
const H = 460;

// Hierarchical / Radial Multi-Ring Layout for optimal readability without overlap
function layoutNodes(entities: SOTEntity[], relations: SOTRelation[], W: number, H: number) {
  const cx = W / 2;
  const cy = H / 2;
  const n = entities.length;
  if (n === 0) return [];

  // Compute degree of each node to place central hubs in the inner ring
  const degrees: Record<string, number> = {};
  for (const e of entities) degrees[e.id] = 0;
  for (const r of relations) {
    if (degrees[r.fromId] !== undefined) degrees[r.fromId]++;
    if (degrees[r.toId] !== undefined) degrees[r.toId]++;
  }

  // Sort: highest degree first
  const sorted = [...entities].sort((a, b) => (degrees[b.id] || 0) - (degrees[a.id] || 0));

  // Small graph (<= 7 nodes): single spacious circle
  if (n <= 7) {
    const rx = 180;
    const ry = 140;
    return sorted.map((e, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      return {
        id: e.id,
        entity: e,
        x: cx + rx * Math.cos(angle),
        y: cy + ry * Math.sin(angle),
        degree: degrees[e.id] || 0,
      };
    });
  }

  // Multi-ring layout: Top 3-5 hubs in inner ring, remainder in outer ring
  const innerCount = Math.min(Math.max(2, Math.floor(n * 0.28)), 5);
  const outerCount = n - innerCount;

  const innerR = 105;
  const outerRx = 260;
  const outerRy = 175;

  return sorted.map((e, i) => {
    if (i < innerCount) {
      const angle = (2 * Math.PI * i) / innerCount - Math.PI / 2;
      return {
        id: e.id,
        entity: e,
        x: cx + innerR * Math.cos(angle),
        y: cy + innerR * Math.sin(angle) * 0.85,
        degree: degrees[e.id] || 0,
      };
    } else {
      const outIdx = i - innerCount;
      const angle = (2 * Math.PI * outIdx) / outerCount - Math.PI / 2;
      return {
        id: e.id,
        entity: e,
        x: cx + outerRx * Math.cos(angle),
        y: cy + outerRy * Math.sin(angle),
        degree: degrees[e.id] || 0,
      };
    }
  });
}

export default function GraphView({ entities, relations, className }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [zoom, setZoom] = useState<number>(1.0);
  const [showAll, setShowAll] = useState<boolean>(false);

  // Available entity types in dataset
  const availableTypes = useMemo(() => {
    const types = new Set<string>();
    entities.forEach((e) => types.add(e.type));
    return Array.from(types);
  }, [entities]);

  // Filter entities according to criteria
  const filteredEntities = useMemo(() => {
    let list = entities.filter((e) => {
      if (filterType !== "all" && e.type !== filterType) return false;
      if (e.confidence < minConfidence) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return e.text.toLowerCase().includes(q) || e.type.toLowerCase().includes(q);
      }
      return true;
    });

    // If there are many nodes and user hasn't expanded, keep most relevant top 18
    if (!showAll && list.length > 18 && !searchQuery.trim() && filterType === "all") {
      list = list.slice(0, 18);
    }
    return list;
  }, [entities, filterType, minConfidence, searchQuery, showAll]);

  const activeEntityIds = useMemo(() => new Set(filteredEntities.map((e) => e.id)), [filteredEntities]);

  // Filter relations to only active nodes
  const activeRelations = useMemo(() => {
    const seen = new Set<string>();
    const rels: SOTRelation[] = [];
    for (const r of relations) {
      if (activeEntityIds.has(r.fromId) && activeEntityIds.has(r.toId)) {
        const key = `${r.fromId}->${r.toId}:${r.label}`;
        if (!seen.has(key)) {
          seen.add(key);
          rels.push(r);
        }
      }
    }
    return rels;
  }, [relations, activeEntityIds]);

  // Layout node coordinates
  const nodes = useMemo(() => layoutNodes(filteredEntities, activeRelations, W, H), [filteredEntities, activeRelations]);
  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  // Selected node relationships and details
  const selectedNode = useMemo(() => {
    if (!selectedId) return null;
    return entities.find((e) => e.id === selectedId) || null;
  }, [selectedId, entities]);

  const neighborIds = useMemo(() => {
    if (!selectedId) return new Set<string>();
    const set = new Set<string>([selectedId]);
    for (const r of relations) {
      if (r.fromId === selectedId) set.add(r.toId);
      if (r.toId === selectedId) set.add(r.fromId);
    }
    return set;
  }, [selectedId, relations]);

  const selectedRelations = useMemo(() => {
    if (!selectedId) return [];
    return relations.filter((r) => r.fromId === selectedId || r.toId === selectedId);
  }, [selectedId, relations]);

  if (entities.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-52 text-slate-500 rounded-xl bg-slate-950 border border-slate-800", className)}>
        <Shield size={28} className="text-slate-700 mb-2" />
        <p className="text-sm font-medium text-slate-400">No Knowledge Graph entities extracted yet.</p>
        <p className="text-xs text-slate-600 mt-1">Upload a document to extract semantic entities and verified relations.</p>
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl border border-slate-800 bg-slate-950 flex flex-col overflow-hidden shadow-lg", className)}>
      {/* ── Top Interactive Toolbar ───────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 px-3 py-2 border-b border-slate-800/80 bg-slate-900/70 text-xs">
        {/* Search */}
        <div className="relative flex items-center min-w-[160px] max-w-[220px]">
          <Search size={13} className="absolute left-2.5 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search entity..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-7 pr-6 py-1 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 text-xs"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-2 text-slate-500 hover:text-slate-300">
              <X size={12} />
            </button>
          )}
        </div>

        {/* Entity Type Filter */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none py-0.5">
          <button
            onClick={() => setFilterType("all")}
            className={cn(
              "px-2 py-0.5 rounded text-[11px] font-medium transition-colors",
              filterType === "all"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            )}
          >
            All ({entities.length})
          </button>
          {availableTypes.map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={cn(
                "px-2 py-0.5 rounded text-[11px] font-medium capitalize transition-colors flex items-center gap-1",
                filterType === t
                  ? "bg-slate-700 text-white border border-slate-600"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              )}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: ENTITY_COLORS[t]?.stroke || "#94a3b8" }}
              />
              {t}
            </button>
          ))}
        </div>

        {/* Confidence & Zoom Controls */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Confidence Filter */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[10px]">
            <button
              onClick={() => setMinConfidence(0)}
              className={cn("px-1.5 py-0.5 rounded", minConfidence === 0 ? "bg-slate-800 text-blue-400 font-semibold" : "text-slate-500")}
            >
              All
            </button>
            <button
              onClick={() => setMinConfidence(0.85)}
              className={cn("px-1.5 py-0.5 rounded", minConfidence === 0.85 ? "bg-slate-800 text-emerald-400 font-semibold" : "text-slate-500")}
            >
              ≥85%
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-slate-400">
            <button
              onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
              className="p-1 hover:text-slate-200 hover:bg-slate-800 rounded"
              title="Zoom out"
            >
              <ZoomOut size={13} />
            </button>
            <span className="text-[10px] mono-sm px-1 text-slate-400">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(2.2, z + 0.15))}
              className="p-1 hover:text-slate-200 hover:bg-slate-800 rounded"
              title="Zoom in"
            >
              <ZoomIn size={13} />
            </button>
            <button
              onClick={() => { setZoom(1.0); setSelectedId(null); }}
              className="p-1 hover:text-slate-200 hover:bg-slate-800 rounded ml-0.5"
              title="Reset view"
            >
              <RotateCcw size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Main SVG Canvas ──────────────────────────────────────────────── */}
      <div className="relative w-full overflow-hidden bg-slate-950 select-none cursor-default" style={{ height: 420 }}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-full"
          onClick={() => setSelectedId(null)}
        >
          {/* Background Grid Pattern */}
          <defs>
            <pattern id="graph-grid" width="28" height="28" patternUnits="userSpaceOnUse">
              <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#172233" strokeWidth="0.5" />
            </pattern>
            <marker id="arrow-active" markerWidth="7" markerHeight="7" refX="21" refY="3.5" orient="auto">
              <polygon points="0 0, 7 3.5, 0 7" fill="#60a5fa" />
            </marker>
            <marker id="arrow-default" markerWidth="6" markerHeight="6" refX="19" refY="3" orient="auto">
              <polygon points="0 0, 6 3, 0 6" fill="#334155" />
            </marker>
          </defs>
          <rect width={W} height={H} fill="url(#graph-grid)" />

          {/* Scalable & Zoomable Group */}
          <g transform={`translate(${(W * (1 - zoom)) / 2}, ${(H * (1 - zoom)) / 2}) scale(${zoom})`}>
            {/* Concentric subtle guide rings */}
            <circle cx={W / 2} cy={H / 2} r={105} fill="none" stroke="#1e293b" strokeWidth="0.8" strokeDasharray="3 3" />
            <circle cx={W / 2} cy={H / 2} r={220} fill="none" stroke="#172033" strokeWidth="0.8" strokeDasharray="4 4" />

            {/* Relations (Edges) */}
            {activeRelations.map((rel) => {
              const from = nodeMap[rel.fromId];
              const to   = nodeMap[rel.toId];
              if (!from || !to) return null;

              const isIncident = selectedId ? rel.fromId === selectedId || rel.toId === selectedId : true;
              const edgeColor = selectedId
                ? (isIncident ? "#60a5fa" : "#1e293b")
                : "#334155";
              const strokeWidth = isIncident && selectedId ? 1.8 : 1.1;
              const textColor = isIncident && selectedId ? "#93c5fd" : "#475569";

              const mx = (from.x + to.x) / 2;
              const my = (from.y + to.y) / 2;

              return (
                <g key={rel.id} className="transition-opacity duration-150">
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={edgeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={isIncident && selectedId ? undefined : "4 2"}
                    markerEnd={isIncident && selectedId ? "url(#arrow-active)" : "url(#arrow-default)"}
                  />
                  <rect
                    x={mx - (rel.label.length * 2.8 + 4)}
                    y={my - 8}
                    width={rel.label.length * 5.6 + 8}
                    height={12}
                    fill="#020617"
                    rx={3}
                  />
                  <text
                    x={mx}
                    y={my + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="8.5"
                    fontFamily="system-ui"
                    fill={textColor}
                    fontWeight={isIncident && selectedId ? "600" : "400"}
                  >
                    {rel.label}
                  </text>
                </g>
              );
            })}

            {/* Entity Nodes */}
            {nodes.map((node) => {
              const c = ENTITY_COLORS[node.entity.type] ?? ENTITY_COLORS.fact;
              const isSelected = selectedId === node.id;
              const isNeighbor = neighborIds.has(node.id);
              const isDimmed = selectedId !== null && !isNeighbor;

              const r = isSelected ? 24 : 20;
              const labelText = node.entity.text.length > 15
                ? node.entity.text.slice(0, 13) + "…"
                : node.entity.text;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedId(isSelected ? null : node.id);
                  }}
                  className="cursor-pointer transition-transform duration-150 group"
                  opacity={isDimmed ? 0.25 : 1.0}
                >
                  <title>{`${node.entity.text} (${c.label}) — Confidence: ${Math.round(node.entity.confidence * 100)}%`}</title>

                  {/* Selection glow ring */}
                  {isSelected && (
                    <circle
                      r={r + 6}
                      fill="none"
                      stroke="#60a5fa"
                      strokeWidth="2.5"
                      strokeDasharray="4 2"
                      className="animate-spin-slow"
                    />
                  )}

                  {/* Node Circle */}
                  <circle
                    r={r}
                    fill={c.fill}
                    stroke={isSelected ? "#93c5fd" : c.stroke}
                    strokeWidth={isSelected ? 2.5 : 1.6}
                    className="transition-all duration-150 group-hover:stroke-white"
                  />

                  {/* Node Label Text */}
                  <text
                    y={-2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="9.5"
                    fontFamily="JetBrains Mono, monospace"
                    fill={isSelected ? "#ffffff" : c.text}
                    fontWeight={isSelected ? "700" : "500"}
                  >
                    {labelText}
                  </text>

                  {/* Entity Type Label */}
                  <text
                    y={10}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="7"
                    fontFamily="system-ui"
                    fill="#64748b"
                    fontWeight="500"
                    className="capitalize"
                  >
                    {node.entity.type}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Floating Expansion Banner if nodes are limited */}
        {!showAll && entities.length > 18 && (
          <div className="absolute bottom-3 left-3">
            <button
              onClick={() => setShowAll(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-700 text-blue-400 text-xs hover:bg-slate-800 transition-colors shadow-md"
            >
              <Layers size={12} />
              <span>Showing top 18 core entities · View all ({entities.length})</span>
            </button>
          </div>
        )}
      </div>

      {/* ── Selected Entity Inspector Drawer ──────────────────────────────── */}
      {selectedNode && (
        <div className="p-3 border-t border-slate-800 bg-slate-900/95 flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{ background: ENTITY_COLORS[selectedNode.type]?.stroke || "#3b82f6" }}
              />
              <span className="text-sm font-semibold text-white tracking-wide">
                {selectedNode.text}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono capitalize bg-slate-800 text-slate-300 border border-slate-700">
                {selectedNode.type}
              </span>
              <span className="text-xs text-emerald-400 font-mono">
                {Math.round(selectedNode.confidence * 100)}% verified
              </span>
            </div>
            <button
              onClick={() => setSelectedId(null)}
              className="text-slate-400 hover:text-white p-0.5 rounded hover:bg-slate-800"
              title="Close inspector"
            >
              <X size={14} />
            </button>
          </div>

          {/* Evidence / Source Reference */}
          {selectedNode.sourceRef && (
            <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-950/70 p-2 rounded-lg border border-slate-800/80">
              <Info size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-semibold text-slate-300 mr-1.5">
                  Source Evidence {selectedNode.sourceRef.page ? `(Page ${selectedNode.sourceRef.page}):` : ":"}
                </span>
                <span className="italic text-slate-400">
                  "{((selectedNode.sourceRef as any).snippet) || "Directly verified against source document."}"
                </span>
              </div>
            </div>
          )}

          {/* Connected Relationships list */}
          {selectedRelations.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span className="text-[11px] text-slate-500 font-medium mr-1">Semantic Triples:</span>
              {selectedRelations.map((r) => {
                const fromEnt = entities.find((e) => e.id === r.fromId);
                const toEnt = entities.find((e) => e.id === r.toId);
                return (
                  <span
                    key={r.id}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/90 text-slate-300 border border-slate-700/80 text-[11px]"
                  >
                    <span className="text-blue-300 font-medium">{fromEnt?.text || r.fromId}</span>
                    <span className="text-slate-500 italic">--[{r.label}]--&gt;</span>
                    <span className="text-purple-300 font-medium">{toEnt?.text || r.toId}</span>
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Footer Legend ─────────────────────────────────────────────────── */}
      <div className="px-3 py-2 border-t border-slate-800/60 bg-slate-950 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500">
        <div className="flex flex-wrap items-center gap-3">
          {Object.entries(ENTITY_COLORS).slice(0, 6).map(([type, c]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: c.stroke }} />
              <span className="capitalize text-slate-400">{type}</span>
            </div>
          ))}
        </div>
        <div className="mono-sm text-slate-600 text-[10px]">
          {activeRelations.length} verified relationships · {filteredEntities.length} canonical nodes
        </div>
      </div>
    </div>
  );
}

