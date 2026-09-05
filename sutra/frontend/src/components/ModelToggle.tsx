import { cn } from "@/lib/utils";

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  contextWindow: string;
  speed: "fast" | "medium" | "slow";
  description: string;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: "gpt-4o",
    label: "GPT-4o",
    provider: "OpenAI",
    contextWindow: "128K",
    speed: "fast",
    description: "Best for structured outputs and reasoning",
  },
  {
    id: "claude-3-5-sonnet",
    label: "Claude 3.5 Sonnet",
    provider: "Anthropic",
    contextWindow: "200K",
    speed: "medium",
    description: "Best for long-form, nuanced content",
  },
  {
    id: "gemini-1.5-pro",
    label: "Gemini 1.5 Pro",
    provider: "Google",
    contextWindow: "1M",
    speed: "medium",
    description: "Best for multimodal and very long sources",
  },
  {
    id: "local-llama-3",
    label: "Llama 3 (Local)",
    provider: "On-Premise",
    contextWindow: "8K",
    speed: "fast",
    description: "Air-gapped, no external data transfer",
  },
];

const speedColor: Record<string, string> = {
  fast:   "text-emerald-400",
  medium: "text-yellow-400",
  slow:   "text-red-400",
};

interface Props {
  value: string;
  onChange: (modelId: string) => void;
  className?: string;
}

export default function ModelToggle({ value, onChange, className }: Props) {
  return (
    <div className={cn("space-y-2", className)}>
      <div className="label">Generation Model</div>
      <div className="space-y-1.5">
        {AVAILABLE_MODELS.map((model) => {
          const selected = value === model.id;
          return (
            <label
              key={model.id}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                selected
                  ? "bg-blue-950/50 border-blue-700"
                  : "bg-slate-900 border-slate-800 hover:border-slate-700"
              )}
            >
              <input
                type="radio"
                name="model"
                value={model.id}
                checked={selected}
                onChange={() => onChange(model.id)}
                className="sr-only"
              />
              {/* Radio indicator */}
              <div
                className={cn(
                  "w-4 h-4 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center",
                  selected ? "border-blue-500 bg-blue-500" : "border-slate-600"
                )}
              >
                {selected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={cn("text-sm font-semibold", selected ? "text-blue-200" : "text-slate-200")}>
                    {model.label}
                  </span>
                  <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded uppercase tracking-wider">
                    {model.provider}
                  </span>
                  <span className={cn("text-[10px] font-mono ml-auto", speedColor[model.speed])}>
                    {model.speed} · {model.contextWindow} ctx
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{model.description}</p>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
