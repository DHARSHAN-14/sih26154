import { useState } from "react";
import { Download, FileText, Image, FileCode, File, ExternalLink } from "lucide-react";
import { cn, formatBytes, formatDate, artifactFormatLabel, outputTypeMeta } from "@/lib/utils";
import type { Artifact } from "@/types";
import SecurityBadge from "./SecurityBadge";

interface Props {
  artifact: Artifact;
  onDownload?: (artifact: Artifact) => void;
  className?: string;
}

const formatIcon: Record<string, React.ElementType> = {
  pdf:  FileText,
  docx: FileText,
  html: FileCode,
  txt:  FileText,
  json: FileCode,
  png:  Image,
  md:   FileText,
};

export default function ArtifactPreview({ artifact, onDownload, className }: Props) {
  const [showFullPreview, setShowFullPreview] = useState(false);
  const Icon = formatIcon[artifact.format] ?? File;
  const typeMeta = outputTypeMeta[artifact.type];
  const preview = artifact.previewText ?? "";

  return (
    <div className={cn("card overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-start gap-3 px-4 py-3 border-b border-slate-800">
        <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
          <Icon size={16} className="text-slate-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-100 leading-snug">{artifact.title}</h3>
            <SecurityBadge level={artifact.classification} variant="pill" className="shrink-0" />
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[10px] bg-slate-800 border border-slate-700 text-slate-400 px-1.5 py-0.5 rounded font-mono uppercase">
              {artifactFormatLabel[artifact.format]}
            </span>
            <span className="text-[10px] text-slate-500">{typeMeta?.label}</span>
            <span className="text-[10px] text-slate-500 font-mono ml-auto">{formatBytes(artifact.sizeBytes)}</span>
          </div>
        </div>
      </div>

      {/* Preview text */}
      {preview && (
        <div className="px-4 py-3 border-b border-slate-800/50">
          <div
            className={cn(
              "text-sm text-slate-300 leading-relaxed font-mono text-xs",
              !showFullPreview && "line-clamp-4"
            )}
          >
            {preview}
          </div>
          {preview.length > 200 && (
            <button
              onClick={() => setShowFullPreview(!showFullPreview)}
              className="text-[11px] text-blue-400 hover:text-blue-300 mt-1.5 transition-colors"
            >
              {showFullPreview ? "Show less" : "Show full preview"}
            </button>
          )}
        </div>
      )}

      {/* Metadata footer */}
      <div className="flex items-center gap-3 px-4 py-2.5">
        <div className="flex-1 text-[10px] text-slate-500 space-y-0.5">
          <div className="font-mono">ID: {artifact.id.slice(0, 12)}…</div>
          <div>v{artifact.version} · {formatDate(artifact.createdAt)}</div>
        </div>
        <div className="flex items-center gap-2">
          {artifact.previewUrl && (
            <a
              href={artifact.previewUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary btn-sm"
              title="Open preview"
            >
              <ExternalLink size={12} />
            </a>
          )}
          <button
            onClick={() => {
              if (onDownload) {
                onDownload(artifact);
              } else if (artifact.downloadUrl) {
                window.open(artifact.downloadUrl, "_blank");
              }
            }}
            className="btn btn-primary btn-sm"
            title="Download verified artefact"
          >
            <Download size={12} />
            <span>Download</span>
          </button>
        </div>
      </div>
    </div>
  );
}
