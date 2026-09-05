import { AlertCircle, Search } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  tokenName: string;
  description?: string;
  onOverride?: (value: string) => void;
  className?: string;
}

export default function UnsupportedToken({ tokenName, description, onOverride, className }: Props) {
  const [editing, setEditing] = useState(false);
  const [value, setValue]     = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (value.trim()) {
      onOverride?.(value.trim());
      setEditing(false);
    }
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded",
        "bg-yellow-950/40 border border-yellow-800/60 text-yellow-400",
        "text-xs font-mono cursor-pointer",
        className
      )}
      title={description ?? `Template token '{{${tokenName}}}' could not be resolved`}
    >
      <AlertCircle size={10} className="shrink-0" />
      <span>{`{{${tokenName}}}`}</span>

      {onOverride && !editing && (
        <button
          onClick={() => setEditing(true)}
          className="ml-1 text-[10px] text-yellow-500 hover:text-yellow-300 transition-colors underline underline-offset-2"
        >
          override
        </button>
      )}

      {editing && (
        <form onSubmit={handleSubmit} className="inline-flex items-center gap-1 ml-1">
          <input
            autoFocus
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Enter value…"
            className="bg-slate-900 border border-yellow-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200 w-28 focus:outline-none focus:border-yellow-500"
          />
          <button type="submit" className="text-[10px] text-yellow-400 hover:text-yellow-200">
            <Search size={10} />
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="text-[10px] text-slate-500 hover:text-slate-300"
          >
            ✕
          </button>
        </form>
      )}
    </span>
  );
}
