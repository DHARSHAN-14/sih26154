import { useLocation } from "react-router-dom";
import { Bell, RefreshCw } from "lucide-react";
import { cn, formatDate, shortId } from "@/lib/utils";
import { useSessionStore } from "@/store/session";
import SecurityBadge from "./SecurityBadge";

const PAGE_META: Record<string, { title: string; description: string }> = {
  "/upload":    { title: "Source Upload",     description: "Upload a source document, image, audio or video for transformation" },
  "/truth":     { title: "Source of Truth",   description: "Review extracted knowledge, verify entities, and lock the SOT" },
  "/configure": { title: "Configure Outputs", description: "Select output types, templates, models and transformation parameters" },
  "/run":       { title: "Run Pipeline",      description: "Monitor live pipeline execution across all processing stages" },
  "/results":   { title: "Review & Approve",  description: "Validate generated artefacts, review provenance, and approve for release" },
  "/versions":  { title: "Version History",   description: "Audit trail of all sessions, sources and generated outputs" },
};

import { Menu } from "lucide-react";

interface HeaderProps {
  onMenuClick?: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const location   = useLocation();
  const session    = useSessionStore((s) => s.session);
  const sourceName = session?.source?.name;
  const meta       = PAGE_META[location.pathname] ?? { title: "SUTRA", description: "" };
  const classification = session?.classification ?? "unclassified";

  return (
    <header className="flex items-center gap-4 px-4 sm:px-6 py-3.5 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm shrink-0">
      {onMenuClick && (
        <button
          onClick={onMenuClick}
          className="lg:hidden btn-ghost btn-sm p-1.5 -ml-1 text-slate-400 hover:text-white"
          aria-label="Toggle menu"
        >
          <Menu size={18} />
        </button>
      )}
      {/* Left: page title */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="page-title truncate">{meta.title}</h1>
          {sourceName && (
            <span className="hidden md:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700">
              <span className="text-[11px] text-slate-400 font-mono truncate max-w-[200px]">
                {sourceName}
              </span>
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 mt-0.5 truncate">{meta.description}</p>
      </div>

      {/* Right: session info + badge */}
      <div className="flex items-center gap-3 shrink-0">
        {session && (
          <div className="hidden lg:flex items-center gap-3 text-[11px] text-slate-500">
            <span className="mono-sm">SID·{shortId(session.id)}</span>
            <span className="text-slate-700">|</span>
            <span>{formatDate(session.createdAt)}</span>
          </div>
        )}

        <SecurityBadge level={classification} variant="pill" />

        <button className="btn-ghost btn-sm p-2" title="Refresh">
          <RefreshCw size={14} className="text-slate-500" />
        </button>
        <button className="btn-ghost btn-sm p-2 relative" title="Notifications">
          <Bell size={14} className="text-slate-500" />
        </button>
      </div>
    </header>
  );
}
