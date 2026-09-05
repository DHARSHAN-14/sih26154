import { cn } from "@/lib/utils";
import type { SecurityClassification } from "@/types";

interface Props {
  level: SecurityClassification;
  variant?: "pill" | "banner" | "inline";
  className?: string;
}

const config: Record<
  SecurityClassification,
  { label: string; pill: string; banner: string; dot: string }
> = {
  unclassified: {
    label: "UNCLASSIFIED",
    pill:   "bg-green-900/40 border-green-700 text-green-400",
    banner: "bg-green-950/60 border-green-800 text-green-300",
    dot:    "bg-green-500",
  },
  restricted: {
    label: "RESTRICTED",
    pill:   "bg-yellow-900/40 border-yellow-700 text-yellow-400",
    banner: "bg-yellow-950/60 border-yellow-800 text-yellow-300",
    dot:    "bg-yellow-500",
  },
  confidential: {
    label: "CONFIDENTIAL",
    pill:   "bg-orange-900/40 border-orange-700 text-orange-400",
    banner: "bg-orange-950/60 border-orange-800 text-orange-300",
    dot:    "bg-orange-500",
  },
  secret: {
    label: "SECRET",
    pill:   "bg-red-900/40 border-red-700 text-red-400",
    banner: "bg-red-950/60 border-red-800 text-red-300",
    dot:    "bg-red-500",
  },
};

export default function SecurityBadge({ level, variant = "pill", className }: Props) {
  const c = config[level] ?? config.unclassified;

  if (variant === "banner") {
    return (
      <div
        className={cn(
          "flex items-center justify-center gap-2 py-1",
          "text-xs font-bold tracking-[0.2em] uppercase border-b",
          c.banner,
          className
        )}
      >
        <span>◆</span>
        <span>{c.label}</span>
        <span>◆</span>
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <span className={cn("flex items-center gap-1.5", className)}>
        <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", c.dot)} />
        <span className={cn("text-xs font-semibold tracking-wider", c.pill.split(" ").find(x => x.startsWith("text-")))}>{c.label}</span>
      </span>
    );
  }

  // pill (default)
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md",
        "text-[10px] font-bold tracking-widest uppercase border",
        c.pill,
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", c.dot)} />
      {c.label}
    </span>
  );
}
