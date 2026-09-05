import { NavLink, useLocation } from "react-router-dom";
import {
  Upload, ShieldCheck, Settings2, Play,
  FileOutput, History, Lock, Cpu, LayoutDashboard, FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSessionStore, selectDemoMode } from "@/store/session";
import type { SessionStage } from "@/types";

interface NavItem {
  path: string;
  stage: SessionStage | "dashboard";
  step: number;
  label: string;
  sublabel: string;
  Icon: React.ElementType;
  alwaysAccessible?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { path: "/dashboard", stage: "dashboard", step: 0, label: "Dashboard",          sublabel: "Overview & quick actions",      Icon: LayoutDashboard, alwaysAccessible: true },
  { path: "/upload",    stage: "upload",    step: 1, label: "Source Upload",       sublabel: "Ingest source material",        Icon: Upload },
  { path: "/truth",     stage: "truth",     step: 2, label: "Source of Truth",     sublabel: "Entities · KG · Lock SOT",      Icon: ShieldCheck },
  { path: "/configure", stage: "configure", step: 3, label: "Configure Outputs",   sublabel: "Type · Tone · Model · Language", Icon: Settings2 },
  { path: "/run",       stage: "run",       step: 4, label: "Run Pipeline",        sublabel: "Live stage visualization",       Icon: Play },
  { path: "/results",   stage: "results",   step: 5, label: "Review & Approve",    sublabel: "Validate · Provenance · Export", Icon: FileOutput },
  { path: "/versions",  stage: "versions",  step: 6, label: "Versions",            sublabel: "Audit trail · History",          Icon: History },
];

// Pipeline-only items (excludes dashboard)
const PIPELINE_ITEMS = NAV_ITEMS.filter((n) => n.step > 0);

interface SidebarProps {
  onClose?: () => void;
}

export default function Sidebar({ onClose }: SidebarProps) {
  const location     = useLocation();
  const session      = useSessionStore((s) => s.session);
  const demoMode     = useSessionStore(selectDemoMode);
  const currentStage = useSessionStore((s) => s.currentStage);

  const stageIndex = PIPELINE_ITEMS.findIndex((n) => n.stage === currentStage);

  function isAccessible(item: NavItem) {
    if (item.alwaysAccessible) return true;
    if (!session) return item.step === 1;
    const itemIndex = PIPELINE_ITEMS.findIndex((n) => n.stage === item.stage);
    return itemIndex <= stageIndex + 1;
  }

  return (
    <aside className="w-64 shrink-0 flex flex-col bg-slate-900 border-r border-slate-800 overflow-y-auto">
      {/* Brand */}
      <div className="px-5 py-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <Cpu size={16} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-wide">SUTRA</div>
            <div className="text-[10px] text-slate-500 tracking-widest uppercase">NTRO · SIH 2026</div>
          </div>
        </div>
      </div>

      {/* Demo mode indicator */}
      {demoMode && (
        <div className="mx-3 mt-3 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-purple-950/50 border border-purple-800">
          <FlaskConical size={11} className="text-purple-400 shrink-0" />
          <span className="text-[10px] text-purple-400 font-medium">Demo Mode</span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4">
        {/* Dashboard (standalone) */}
        <div className="mb-3">
          {NAV_ITEMS.filter((n) => n.alwaysAccessible).map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => onClose?.()}
                className={cn(
                  "flex items-center gap-3 px-2 py-2.5 rounded-lg transition-colors",
                  isActive
                    ? "bg-blue-950/70 text-blue-300"
                    : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                )}
              >
                <div className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center shrink-0",
                  isActive ? "bg-blue-600" : "bg-slate-800 border border-slate-700"
                )}>
                  <item.Icon size={13} className={isActive ? "text-white" : "text-slate-500"} />
                </div>
                <div>
                  <div className={cn("text-sm font-medium", isActive ? "text-blue-200" : "")}>{item.label}</div>
                </div>
              </NavLink>
            );
          })}
        </div>

        <div className="label px-2 mb-2">Pipeline</div>

        {/* Pipeline steps */}
        <ul className="space-y-1">
          {PIPELINE_ITEMS.map((item, idx) => {
            const accessible = isAccessible(item);
            const isActive   = location.pathname === item.path;
            const isPast     = idx < stageIndex;
            const isCurrent  = idx === stageIndex;

            return (
              <li key={item.path} className="relative">
                {idx < PIPELINE_ITEMS.length - 1 && (
                  <div className={cn(
                    "absolute left-[22px] top-9 h-[calc(100%+4px)] w-px",
                    isPast ? "bg-blue-800" : "bg-slate-800"
                  )} />
                )}

                <NavLink
                  to={item.path}
                  onClick={(e) => {
                    if (!accessible) {
                      e.preventDefault();
                    } else {
                      onClose?.();
                    }
                  }}
                  className={cn(
                    "relative flex items-start gap-3 px-2 py-2.5 rounded-lg transition-colors duration-150",
                    isActive
                      ? "bg-blue-950/70 text-blue-300"
                      : accessible
                      ? "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                      : "opacity-40 cursor-not-allowed text-slate-600"
                  )}
                >
                  {/* Step circle */}
                  <div className={cn(
                    "relative z-10 w-7 h-7 rounded-full shrink-0 flex items-center justify-center",
                    "text-xs font-bold border transition-colors",
                    isPast    ? "bg-blue-900 border-blue-700 text-blue-300" :
                    isCurrent ? "bg-blue-600 border-blue-500 text-white" :
                                "bg-slate-800 border-slate-700 text-slate-500"
                  )}>
                    {isPast ? (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : item.step}
                  </div>

                  <div className="pt-0.5 min-w-0">
                    <div className={cn("text-sm font-medium truncate", isActive ? "text-blue-200" : "")}>
                      {item.label}
                    </div>
                    <div className="text-[11px] text-slate-500 truncate mt-0.5">{item.sublabel}</div>
                  </div>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Session footer */}
      <div className="px-4 py-3 border-t border-slate-800 space-y-1">
        {session ? (
          <>
            <div className="label">Session</div>
            <div className="mono-sm truncate">{session.id.slice(0, 16)}…</div>
            <div className="flex items-center gap-1.5 mt-1">
              <Lock size={11} className="text-slate-500" />
              <span className="text-[11px] text-slate-500">{session.operatorId}</span>
            </div>
          </>
        ) : (
          <div className="text-[11px] text-slate-600">No active session</div>
        )}
      </div>
    </aside>
  );
}
