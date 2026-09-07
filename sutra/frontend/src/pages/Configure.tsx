import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, ChevronDown, ChevronRight, Play, Settings, Info, Loader } from "lucide-react";
import { cn, outputTypeMeta } from "@/lib/utils";
import { useSessionStore, selectConfigs, selectSOT } from "@/store/session";
import { configsApi } from "@/api/client";
import ModelToggle from "@/components/ModelToggle";
import SecurityBadge from "@/components/SecurityBadge";
import type {
  OutputType, OutputConfig, ToneType, LanguageCode,
  SecurityClassification, DetailLevel, Objective, AudienceType, StyleType,
} from "@/types";

const OUTPUT_TYPES: OutputType[] = [
  "advisory",
  "executive_summary",
  "presentation",
  "infographic",
  "linkedin",
  "twitter_x",
  "video_package",
  "press_release",
  "social_post",
  "executive_brief",
  "technical_report",
  "intelligence_summary",
  "operational_bulletin",
];

interface SelectDef<T extends string> { value: T; label: string; desc?: string }

const TONE_OPTIONS: SelectDef<ToneType>[] = [
  { value: "formal",     label: "Formal",     desc: "Professional, authoritative language" },
  { value: "neutral",    label: "Neutral",    desc: "Balanced, objective tone" },
  { value: "urgent",     label: "Urgent",     desc: "Time-sensitive, action-oriented" },
  { value: "analytical", label: "Analytical", desc: "Data-driven, technical depth" },
];

const DETAIL_OPTIONS: SelectDef<DetailLevel>[] = [
  { value: "brief",         label: "Brief",         desc: "Key points only, minimal background" },
  { value: "standard",      label: "Standard",      desc: "Balanced coverage with context" },
  { value: "comprehensive", label: "Comprehensive", desc: "Full analysis with supporting detail" },
  { value: "exhaustive",    label: "Exhaustive",    desc: "Maximum depth, all available evidence" },
];

const OBJECTIVE_OPTIONS: SelectDef<Objective>[] = [
  { value: "inform",    label: "Inform",    desc: "Communicate facts and findings" },
  { value: "alert",     label: "Alert",     desc: "Trigger immediate action" },
  { value: "persuade",  label: "Persuade",  desc: "Influence decision or policy" },
  { value: "summarize", label: "Summarize", desc: "Condense for quick consumption" },
  { value: "brief",     label: "Brief",     desc: "Prepare for meeting or presentation" },
];

const AUDIENCE_OPTIONS: SelectDef<AudienceType>[] = [
  { value: "public",         label: "Public / Media",    desc: "General audience, no jargon" },
  { value: "internal",       label: "Internal Staff",    desc: "Department-level awareness" },
  { value: "executive",      label: "Executive",         desc: "Leadership, concise and strategic" },
  { value: "technical",      label: "Technical",         desc: "Analysts, engineers, specialists" },
  { value: "field_operator", label: "Field Operator",    desc: "Actionable instructions on the ground" },
  { value: "media",          label: "Press / Media",     desc: "Journalists and external communications" },
];

const STYLE_OPTIONS: SelectDef<StyleType>[] = [
  { value: "narrative",     label: "Narrative",     desc: "Flowing prose paragraphs" },
  { value: "bullet_points", label: "Bullet Points", desc: "Structured lists, easy to scan" },
  { value: "table",         label: "Table",         desc: "Comparative or grid layout" },
  { value: "mixed",         label: "Mixed",         desc: "Prose with embedded lists/tables" },
];

const LANGUAGE_OPTIONS: SelectDef<LanguageCode>[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi (हिन्दी)" },
  { value: "ta", label: "Tamil (தமிழ்)" },
  { value: "te", label: "Telugu (తెలుగు)" },
  { value: "mr", label: "Marathi (मराठी)" },
  { value: "bn", label: "Bengali (বাংলা)" },
  { value: "gu", label: "Gujarati (ગુજરાતી)" },
  { value: "pa", label: "Punjabi (ਪੰਜਾਬੀ)" },
];

const CLASSIFICATION_OPTIONS: SelectDef<SecurityClassification>[] = [
  { value: "unclassified", label: "UNCLASSIFIED" },
  { value: "restricted",   label: "RESTRICTED" },
  { value: "confidential", label: "CONFIDENTIAL" },
  { value: "secret",       label: "SECRET" },
];

const MAX_TOKENS: Record<OutputType, number> = {
  advisory: 1500,
  executive_summary: 800,
  presentation: 1200,
  infographic: 1000,
  linkedin: 600,
  twitter_x: 280,
  video_package: 1000,
  press_release: 800,
  social_post: 280,
  executive_brief: 600,
  technical_report: 2000,
  intelligence_summary: 1000,
  operational_bulletin: 500,
};

let _idCounter = 0;
function newId() { return `cfg-${Date.now()}-${++_idCounter}`; }

function FieldRow({ label, tooltip, children }: { label: string; tooltip?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <label className="label">{label}</label>
        {tooltip && (
          <span title={tooltip} className="cursor-help">
            <Info size={11} className="text-slate-600" />
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

export default function Configure() {
  const navigate = useNavigate();
  const sot      = useSessionStore(selectSOT);
  const configs  = useSessionStore(selectConfigs);
  const { upsertOutputConfig, removeOutputConfig, goToStage } = useSessionStore();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const sessionId = useSessionStore((s) => s.sessionId);
  const demoMode = useSessionStore((s) => s.demoMode);

  async function handleProceedToRun() {
    if (enabledCount === 0) return;
    setSaving(true);
    // Sync configurations to backend session if active
    if (sessionId && !demoMode) {
      try {
        const enabledConfigs = configs.filter((c) => c.enabled);
        await Promise.allSettled(
          enabledConfigs.map((cfg) => configsApi.create(sessionId, cfg))
        );
      } catch {
        // Continue to run even if backend configs endpoint is still being wired
      }
    }
    setSaving(false);
    goToStage("run");
    navigate("/run");
  }

  function addConfig(type: OutputType) {
    const cfg: OutputConfig = {
      id: newId(), type,
      templateId:   `${type}_default`,
      language:     "en",
      tone:         "formal",
      classification: sot?.status === "locked" ? "restricted" : "unclassified",
      model:        "gpt-4o",
      maxTokens:    MAX_TOKENS[type],
      enabled:      true,
      detailLevel:  "standard",
      objective:    "inform",
      audience:     "internal",
      style:        "narrative",
    };
    upsertOutputConfig(cfg);
    setExpandedId(cfg.id);
  }

  function updateCfg(id: string, updates: Partial<OutputConfig>) {
    const cur = configs.find((c) => c.id === id);
    if (cur) upsertOutputConfig({ ...cur, ...updates });
  }

  const enabledCount = configs.filter((c) => c.enabled).length;

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="page-title">Configure Outputs</h2>
          <p className="text-sm text-slate-400 mt-1">
            Select output types and configure model, audience, tone, style and classification for each.
          </p>
        </div>
        {enabledCount > 0 && (
          <div className="shrink-0 text-right">
            <div className="text-2xl font-bold text-blue-400 tabular-nums">{enabledCount}</div>
            <div className="text-xs text-slate-500">output{enabledCount !== 1 ? "s" : ""} configured</div>
          </div>
        )}
      </div>

      {/* Output type picker */}
      <div>
        <div className="label mb-2">Add Output Type</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {OUTPUT_TYPES.map((type) => {
            const meta       = outputTypeMeta[type];
            const alreadyAdded = configs.some((c) => c.type === type);
            return (
              <button
                key={type}
                onClick={() => alreadyAdded ? undefined : addConfig(type)}
                disabled={alreadyAdded}
                className={cn(
                  "flex flex-col gap-1 p-3 rounded-xl border text-left transition-all",
                  alreadyAdded
                    ? "border-blue-800 bg-blue-950/30 opacity-70 cursor-default"
                    : "border-slate-800 bg-slate-900 hover:border-slate-600 hover:bg-slate-800 cursor-pointer"
                )}
              >
                <span className="text-xl">{meta.icon}</span>
                <span className={cn("text-xs font-semibold", alreadyAdded ? "text-blue-300" : "text-slate-300")}>
                  {meta.label}
                </span>
                <span className="text-[10px] text-slate-500">{meta.description}</span>
                {alreadyAdded && <span className="text-[9px] text-blue-400 font-mono uppercase tracking-widest mt-0.5">✓ Added</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Configured outputs */}
      {configs.length > 0 && (
        <div className="space-y-2">
          <div className="label">Configured Outputs</div>
          {configs.map((cfg) => {
            const meta   = outputTypeMeta[cfg.type];
            const isOpen = expandedId === cfg.id;
            return (
              <div key={cfg.id} className={cn(
                "rounded-xl border overflow-hidden transition-colors",
                cfg.enabled ? "border-slate-700 bg-slate-900" : "border-slate-800 bg-slate-900/50 opacity-60"
              )}>
                {/* Header row */}
                <div className="flex items-center gap-3 px-4 py-3">
                  <span className="text-lg shrink-0">{meta.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-200">{meta.label}</span>
                      <SecurityBadge level={cfg.classification} variant="pill" />
                      <span className="text-[10px] text-slate-500 font-mono ml-auto">
                        {LANGUAGE_OPTIONS.find((l) => l.value === cfg.language)?.label} ·{" "}
                        {cfg.audience ?? "—"} · {cfg.model.split("-")[0]}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <label className="relative inline-flex items-center cursor-pointer" title={cfg.enabled ? "Enabled" : "Disabled"}>
                      <input type="checkbox" checked={cfg.enabled} onChange={(e) => updateCfg(cfg.id, { enabled: e.target.checked })} className="sr-only peer" />
                      <div className="w-8 h-4 bg-slate-700 rounded-full peer peer-checked:bg-blue-600 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:after:translate-x-4" />
                    </label>
                    <button onClick={() => setExpandedId(isOpen ? null : cfg.id)} className="btn btn-ghost btn-sm p-1.5">
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    <button onClick={() => { removeOutputConfig(cfg.id); if (expandedId === cfg.id) setExpandedId(null); }} className="btn btn-ghost btn-sm p-1.5 text-slate-600 hover:text-red-400">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Expanded config */}
                {isOpen && (
                  <div className="px-4 pb-5 pt-3 border-t border-slate-800 space-y-5">
                    {/* Row 1: Language + Classification */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <FieldRow label="Output Language">
                        <select value={cfg.language} onChange={(e) => updateCfg(cfg.id, { language: e.target.value as LanguageCode })} className="select">
                          {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </FieldRow>
                      <FieldRow label="Security Classification">
                        <select value={cfg.classification} onChange={(e) => updateCfg(cfg.id, { classification: e.target.value as SecurityClassification })} className="select">
                          {CLASSIFICATION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </FieldRow>
                    </div>

                    {/* Row 2: Audience + Objective */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <FieldRow label="Target Audience" tooltip="Who will read this output?">
                        <div className="space-y-1">
                          {AUDIENCE_OPTIONS.map((o) => (
                            <label key={o.value} className={cn(
                              "flex items-start gap-2 p-2 rounded-lg border cursor-pointer transition-colors",
                              cfg.audience === o.value ? "border-blue-700 bg-blue-950/40" : "border-slate-800 hover:border-slate-700"
                            )}>
                              <input type="radio" name={`audience-${cfg.id}`} value={o.value} checked={cfg.audience === o.value} onChange={() => updateCfg(cfg.id, { audience: o.value as AudienceType })} className="sr-only" />
                              <div className={cn("w-3.5 h-3.5 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center", cfg.audience === o.value ? "border-blue-500 bg-blue-500" : "border-slate-600")}>
                                {cfg.audience === o.value && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                              </div>
                              <div>
                                <div className="text-xs font-medium text-slate-300">{o.label}</div>
                                <div className="text-[10px] text-slate-500">{o.desc}</div>
                              </div>
                            </label>
                          ))}
                        </div>
                      </FieldRow>

                      <div className="space-y-4">
                        {/* Objective */}
                        <FieldRow label="Objective" tooltip="Primary communicative goal">
                          <select value={cfg.objective ?? "inform"} onChange={(e) => updateCfg(cfg.id, { objective: e.target.value as Objective })} className="select">
                            {OBJECTIVE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label} — {o.desc}</option>)}
                          </select>
                        </FieldRow>

                        {/* Tone */}
                        <FieldRow label="Tone">
                          <select value={cfg.tone} onChange={(e) => updateCfg(cfg.id, { tone: e.target.value as ToneType })} className="select">
                            {TONE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label} — {o.desc}</option>)}
                          </select>
                        </FieldRow>

                        {/* Detail Level */}
                        <FieldRow label="Detail Level" tooltip="How much depth to include">
                          <div className="grid grid-cols-2 gap-1.5">
                            {DETAIL_OPTIONS.map((o) => (
                              <button key={o.value} onClick={() => updateCfg(cfg.id, { detailLevel: o.value as DetailLevel })}
                                className={cn("px-2 py-1.5 rounded-lg border text-left transition-colors text-xs",
                                  cfg.detailLevel === o.value ? "border-blue-700 bg-blue-950/40 text-blue-300" : "border-slate-800 text-slate-400 hover:border-slate-700")}>
                                <div className="font-medium">{o.label}</div>
                                <div className="text-[10px] text-slate-500 mt-0.5">{o.desc}</div>
                              </button>
                            ))}
                          </div>
                        </FieldRow>

                        {/* Style */}
                        <FieldRow label="Output Style">
                          <div className="grid grid-cols-2 gap-1.5">
                            {STYLE_OPTIONS.map((o) => (
                              <button key={o.value} onClick={() => updateCfg(cfg.id, { style: o.value as StyleType })}
                                className={cn("px-2 py-1.5 rounded-lg border text-left transition-colors text-xs",
                                  cfg.style === o.value ? "border-blue-700 bg-blue-950/40 text-blue-300" : "border-slate-800 text-slate-400 hover:border-slate-700")}>
                                <div className="font-medium">{o.label}</div>
                                <div className="text-[10px] text-slate-500 mt-0.5">{o.desc}</div>
                              </button>
                            ))}
                          </div>
                        </FieldRow>

                        {/* Max tokens */}
                        <FieldRow label="Max Output Tokens">
                          <input type="number" value={cfg.maxTokens} min={50} max={4000} step={50}
                            onChange={(e) => updateCfg(cfg.id, { maxTokens: Number(e.target.value) })} className="input font-mono" />
                        </FieldRow>
                      </div>
                    </div>

                    {/* Model toggle */}
                    <ModelToggle value={cfg.model} onChange={(m) => updateCfg(cfg.id, { model: m })} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {configs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-600 border border-dashed border-slate-800 rounded-xl">
          <Settings size={28} className="text-slate-700" />
          <p className="text-sm">Select at least one output type above to get started.</p>
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center justify-between pt-2">
        <p className="text-xs text-slate-500">
          {enabledCount === 0 ? "No outputs enabled." : `${enabledCount} output${enabledCount !== 1 ? "s" : ""} will be generated.`}
        </p>
        <button
          onClick={handleProceedToRun}
          disabled={enabledCount === 0 || saving}
          className="btn btn-primary btn-lg"
        >
          {saving ? (
            <><Loader size={16} className="animate-spin" /> Saving Configuration…</>
          ) : (
            <><Play size={16} /> Run Pipeline</>
          )}
        </button>
      </div>
    </div>
  );
}
