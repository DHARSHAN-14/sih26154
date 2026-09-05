import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { SOTEntity, SOTRelation } from "@/types";

interface Props {
  entities: SOTEntity[];
  relations: SOTRelation[];
  className?: string;
}

const ENTITY_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  person:       { fill: "#1e3a5f", stroke: "#3b82f6", text: "#93c5fd" },
  organization: { fill: "#1a3548", stroke: "#06b6d4", text: "#67e8f9" },
  location:     { fill: "#1a3530", stroke: "#10b981", text: "#6ee7b7" },
  date:         { fill: "#3b2f0a", stroke: "#f59e0b", text: "#fcd34d" },
  event:        { fill: "#3d1f5e", stroke: "#a855f7", text: "#d8b4fe" },
  claim:        { fill: "#1e1e1e", stroke: "#6b7280", text: "#d1d5db" },
  fact:         { fill: "#1e2a1e", stroke: "#4ade80", text: "#86efac" },
  numeric:      { fill: "#1e1e2e", stroke: "#818cf8", text: "#c7d2fe" },
  technical:    { fill: "#1e1a1a", stroke: "#f87171", text: "#fca5a5" },
};

// Simple force-free layout: distribute nodes in an ellipse
function layoutNodes(entities: SOTEntity[], W: number, H: number) {
  const cx = W / 2, cy = H / 2;
  const rx = W * 0.38, ry = H * 0.38;
  const n = entities.length || 1;
  return entities.map((e, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return {
      id: e.id,
      x: cx + rx * Math.cos(angle),
      y: cy + ry * Math.sin(angle),
      label: e.text.length > 14 ? e.text.slice(0, 12) + "…" : e.text,
      type: e.type,
    };
  });
}

const W = 600, H = 360;

export default function GraphView({ entities, relations, className }: Props) {
  const nodes = useMemo(() => layoutNodes(entities, W, H), [entities]);
  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  if (entities.length === 0) {
    return (
      <div className={cn("flex items-center justify-center h-48 text-slate-600 text-sm rounded-lg bg-slate-900 border border-slate-800", className)}>
        No entities extracted yet.
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl overflow-hidden border border-slate-800 bg-slate-950", className)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ maxHeight: 360 }}>
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#1e293b" strokeWidth="0.5" />
          </pattern>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#334155" />
          </marker>
        </defs>
        <rect width={W} height={H} fill="url(#grid)" />

        {/* Relations (edges) */}
        {relations.map((rel) => {
          const from = nodeMap[rel.fromId];
          const to   = nodeMap[rel.toId];
          if (!from || !to) return null;
          const mx = (from.x + to.x) / 2;
          const my = (from.y + to.y) / 2;
          return (
            <g key={rel.id}>
              <line
                x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                stroke="#334155" strokeWidth="1" markerEnd="url(#arrow)"
                strokeDasharray="4 2"
              />
              <text x={mx} y={my - 4} textAnchor="middle" fontSize="9" fill="#475569">
                {rel.label}
              </text>
            </g>
          );
        })}

        {/* Entity nodes */}
        {nodes.map((node) => {
          const c = ENTITY_COLORS[node.type] ?? ENTITY_COLORS.fact;
          return (
            <g key={node.id}>
              <circle cx={node.x} cy={node.y} r={22} fill={c.fill} stroke={c.stroke} strokeWidth="1.5" />
              <text x={node.x} y={node.y + 1} textAnchor="middle" dominantBaseline="middle"
                fontSize="9.5" fontFamily="JetBrains Mono, monospace" fill={c.text} fontWeight="500">
                {node.label}
              </text>
              <text x={node.x} y={node.y + 13} textAnchor="middle" dominantBaseline="middle"
                fontSize="7.5" fill="#64748b" fontFamily="system-ui">
                {node.type}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="px-3 py-2 border-t border-slate-800 flex flex-wrap gap-3">
        {Object.entries(ENTITY_COLORS).slice(0, 6).map(([type, c]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: c.stroke }} />
            <span className="text-[10px] text-slate-500 capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
