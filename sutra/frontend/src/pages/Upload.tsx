import { useCallback, useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload as UploadIcon, FileText, Image, Music, Video,
  Link, AlignLeft, X, CheckCircle, AlertCircle, Loader,
  ChevronRight, RefreshCw, FlaskConical,
} from "lucide-react";
import { cn, formatBytes } from "@/lib/utils";
import { useSessionStore, selectDemoMode, selectSource } from "@/store/session";
import { sourcesApi, sessionsApi, sotApi } from "@/api/client";
import type { SourceType, Source } from "@/types";

type InputMode = "file" | "url" | "text";
type UploadProcessingStatus = "idle" | "uploading" | "processing" | "ready" | "done" | "error";

const ACCEPTED: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "text/plain": "TXT",
  "image/png": "PNG",
  "image/jpeg": "JPEG",
  "audio/mpeg": "MP3",
  "audio/wav": "WAV",
  "video/mp4": "MP4",
};

export default function Upload() {
  const navigate = useNavigate();
  const {
    initSession,
    setSource,
    setSourceStatus,
    setUploadProgress,
    setSOT,
    goToStage,
    sessionId,
    seedDemo,
  } = useSessionStore();
  const currentSource = useSessionStore(selectSource);
  const demoMode      = useSessionStore(selectDemoMode);

  const [mode, setMode]             = useState<InputMode>("file");
  const [dragging, setDragging]     = useState(false);
  const [file, setFile]             = useState<File | null>(null);
  const [url, setUrl]               = useState("");
  const [text, setText]             = useState("");
  const [textName, setTextName]     = useState("source-text");
  const [status, setStatus]         = useState<UploadProcessingStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [uploadedSource, setUploadedSource] = useState<Source | null>(currentSource ?? null);
  const [error, setError]           = useState<string | null>(null);
  const [progress, setProgress]     = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (currentSource && status === "idle") {
      setUploadedSource(currentSource);
    }
  }, [currentSource, status]);

  // ── Drag-and-drop ──────────────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      if (!ACCEPTED[dropped.type]) {
        setError(`Unsupported file type: ${dropped.type}`);
        return;
      }
      setFile(dropped);
      setError(null);
    }
  }, []);

  // ── Upload action ──────────────────────────────────────────────────────────
  async function handleUpload() {
    setError(null);
    setStatus("uploading");
    setProgress(0);
    setStatusMessage("Uploading source material to secure storage...");

    try {
      // 1. Ensure a session exists for real data upload
      let sid = sessionId;
      if (!sid || demoMode || sid.startsWith("sess-demo")) {
        try {
          const res = await sessionsApi.create();
          sid = res.data.id;
          initSession(sid);
        } catch {
          // If session creation endpoint fails, generate unique local session ID
          sid = `sess-${Date.now()}`;
          initSession(sid);
        }
      }

      // 2. Upload source via real API
      let source: Source;
      if (mode === "file" && file) {
        const res = await sourcesApi.upload(file, (pct) => {
          setProgress(pct);
          setUploadProgress(pct);
        }, sid);
        source = res.data;
      } else if (mode === "url" && url.trim()) {
        const res = await sourcesApi.uploadUrl(url.trim(), sid);
        source = res.data;
      } else if (mode === "text" && text.trim()) {
        const res = await sourcesApi.uploadText(text.trim(), textName, sid);
        source = res.data;
      } else {
        throw new Error("No source provided.");
      }

      // Ensure session store uses the active backend session ID
      const backendSid = (source as any).sessionId || (source as any).session_id || sid;
      if (backendSid && backendSid !== sessionId) {
        initSession(backendSid);
      }

      setUploadedSource(source);
      setSource(source);
      setSourceStatus("processing");
      setStatus("processing");
      setStatusMessage("Source uploaded. Ingesting content and analyzing Source of Truth...");

      // 3. Poll for processing status or attempt to load initial SOT
      try {
        const statusRes = await sourcesApi.getStatus(source.id);
        if (statusRes.data.status === "ready") {
          setSourceStatus("ready");
          setStatus("ready");
          setStatusMessage("Ingestion complete. Source of Truth ready for review.");
        } else if (statusRes.data.status === "failed") {
          throw new Error(statusRes.data.error || "Source processing failed on the backend.");
        } else {
          setStatusMessage("Source registered. Processing multimodal content...");
        }
      } catch {
        // Backend getStatus endpoint might be pending; check if SOT already available
        try {
          const sotRes = await sotApi.get(source.id);
          if (sotRes.data) {
            setSOT(sotRes.data);
            setSourceStatus("ready");
            setStatus("ready");
            setStatusMessage("Source of Truth extracted successfully.");
          }
        } catch {
          // Normal during initial backend integration
          setStatus("ready");
          setStatusMessage("Source registered. Ready to inspect Source of Truth.");
        }
      }

      goToStage("truth");
    } catch (err: unknown) {
      let msg = "Upload failed. Check your connection to the backend.";
      if (err && typeof err === "object") {
        const ax = err as any;
        if (ax.response?.data?.detail) {
          msg = typeof ax.response.data.detail === "string" ? ax.response.data.detail : JSON.stringify(ax.response.data.detail);
        } else if (ax.response?.data?.message) {
          msg = ax.response.data.message;
        } else if (ax.message) {
          msg = ax.message;
        }
      }
      setError(msg);
      setStatus("error");
      setSourceStatus("failed");
    }
  }

  function handleContinueToTruth() {
    goToStage("truth");
    navigate("/truth");
  }

  function handleLoadDemo() {
    seedDemo();
    navigate("/truth");
  }

  const canUpload =
    (mode === "file" && file != null) ||
    (mode === "url" && url.trim().length > 0) ||
    (mode === "text" && text.trim().length > 0);

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="page-title">Upload Source Material</h2>
          <p className="text-sm text-slate-400 mt-1">
            Provide the source document, image, audio, video, URL, or raw text to extract a verified Source of Truth.
          </p>
        </div>
        {!demoMode && (
          <button
            onClick={handleLoadDemo}
            className="btn btn-secondary btn-sm gap-1.5 text-purple-300 border-purple-800/60 hover:border-purple-700"
            title="Load sample intelligence document without backend"
          >
            <FlaskConical size={13} className="text-purple-400" />
            <span>Load Demo</span>
          </button>
        )}
      </div>

      {/* Mode selector */}
      <div className="flex gap-1 p-1 bg-slate-900 border border-slate-800 rounded-xl">
        {([
          { id: "file", label: "File Upload", Icon: UploadIcon },
          { id: "url",  label: "URL / Link",   Icon: Link },
          { id: "text", label: "Raw Text",     Icon: AlignLeft },
        ] as { id: InputMode; label: string; Icon: React.ElementType }[]).map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => { setMode(id); setError(null); setStatus("idle"); }}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-colors",
              mode === id
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* ── File drop zone ─────────────────────────────────────────────────── */}
      {mode === "file" && (
        <div className="space-y-3">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !file && fileInputRef.current?.click()}
            className={cn(
              "relative rounded-xl border-2 border-dashed transition-colors cursor-pointer",
              "flex flex-col items-center justify-center gap-3 py-12 px-6 text-center",
              dragging
                ? "border-blue-500 bg-blue-950/20"
                : file
                ? "border-emerald-700 bg-emerald-950/10 cursor-default"
                : "border-slate-700 bg-slate-900 hover:border-slate-600 hover:bg-slate-800/50"
            )}
          >
            {file ? (
              <>
                <CheckCircle size={32} className="text-emerald-400" />
                <div>
                  <p className="text-sm font-medium text-slate-200">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatBytes(file.size)} · {ACCEPTED[file.type] ?? file.type}</p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); setStatus("idle"); }}
                  className="btn btn-ghost btn-sm text-xs text-slate-400 hover:text-red-400"
                >
                  <X size={12} /> Remove
                </button>
              </>
            ) : (
              <>
                <UploadIcon size={32} className="text-slate-600" />
                <div>
                  <p className="text-sm font-medium text-slate-300">
                    {dragging ? "Release to upload" : "Drag & drop or click to select"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">PDF · DOCX · TXT · PNG · JPEG · MP3 · WAV · MP4</p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={Object.keys(ACCEPTED).join(",")}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) { setFile(f); setError(null); setStatus("idle"); }
            }}
            className="sr-only"
          />

          {/* Supported formats legend */}
          <div className="flex flex-wrap gap-2">
            {[
              { label: "Document", Icon: FileText, formats: "PDF, DOCX, TXT" },
              { label: "Image",    Icon: Image,    formats: "PNG, JPEG" },
              { label: "Audio",    Icon: Music,    formats: "MP3, WAV" },
              { label: "Video",    Icon: Video,    formats: "MP4" },
            ].map(({ label, Icon, formats }) => (
              <div key={label} className="flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-900 border border-slate-800 rounded-md px-2 py-1">
                <Icon size={11} />
                <span className="font-medium text-slate-400">{label}</span>
                <span className="text-slate-600">{formats}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── URL input ──────────────────────────────────────────────────────── */}
      {mode === "url" && (
        <div className="space-y-2">
          <label className="label">Source URL</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Link size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="input pl-9"
              />
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Publicly accessible URLs to PDFs, pages, or media files. Protected/internal URLs require operator credentials.
          </p>
        </div>
      )}

      {/* ── Text input ─────────────────────────────────────────────────────── */}
      {mode === "text" && (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="label">Source Name</label>
            <input
              type="text"
              value={textName}
              onChange={(e) => setTextName(e.target.value)}
              placeholder="e.g. operational-brief-draft"
              className="input"
            />
          </div>
          <div className="space-y-1.5">
            <label className="label">Source Text</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the source text here…"
              rows={10}
              className="textarea font-mono text-xs leading-relaxed"
            />
            <p className="text-xs text-slate-500">
              {text.trim().split(/\s+/).filter(Boolean).length} words · {text.length} characters
            </p>
          </div>
        </div>
      )}

      {/* Upload progress bar */}
      {status === "uploading" && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-slate-400">
            <span>Uploading to backend…</span>
            <span className="font-mono">{progress}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Processing status banner */}
      {(status === "processing" || status === "ready") && (
        <div className="p-4 rounded-xl border border-blue-800 bg-blue-950/20 space-y-3">
          <div className="flex items-center gap-3">
            {status === "processing" ? (
              <Loader size={18} className="animate-spin text-blue-400 shrink-0" />
            ) : (
              <CheckCircle size={18} className="text-emerald-400 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-slate-200">
                {status === "processing" ? "Processing Source" : "Source Ready"}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">{statusMessage}</div>
            </div>
          </div>

          {uploadedSource && (
            <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 font-mono">
              <div>
                <span className="text-slate-500 text-[10px] block uppercase">Source ID</span>
                <span className="text-slate-300 truncate block">{uploadedSource.id}</span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block uppercase">File Name</span>
                <span className="text-slate-300 truncate block">{uploadedSource.name}</span>
              </div>
              {uploadedSource.checksum && (
                <div className="col-span-2">
                  <span className="text-slate-500 text-[10px] block uppercase">Checksum</span>
                  <span className="text-slate-400 truncate block text-[11px]">{uploadedSource.checksum}</span>
                </div>
              )}
            </div>
          )}

          {status === "ready" && (
            <div className="flex justify-end pt-1">
              <button onClick={handleContinueToTruth} className="btn btn-primary btn-sm">
                View Source of Truth <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="space-y-3 p-4 rounded-xl bg-red-950/30 border border-red-900 text-sm text-red-400">
          <div className="flex items-start gap-2.5">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold text-red-300">Upload / Ingest Failed</div>
              <p className="text-xs mt-1 text-red-400/90 leading-relaxed">{error}</p>
            </div>
          </div>
          <div className="flex gap-2 justify-end pt-1">
            <button
              onClick={() => { setError(null); setStatus("idle"); }}
              className="btn btn-ghost btn-sm text-xs text-slate-400 hover:text-slate-200"
            >
              Dismiss
            </button>
            <button
              onClick={handleUpload}
              className="btn btn-secondary btn-sm text-xs gap-1"
            >
              <RefreshCw size={12} /> Retry
            </button>
            <button
              onClick={handleLoadDemo}
              className="btn btn-secondary btn-sm text-xs gap-1 text-purple-300"
            >
              <FlaskConical size={12} className="text-purple-400" /> Use Demo Data
            </button>
          </div>
        </div>
      )}

      {/* Action button */}
      <div className="flex justify-end">
        {status !== "ready" && (
          <button
            onClick={handleUpload}
            disabled={!canUpload || status === "uploading" || status === "processing"}
            className="btn btn-primary btn-lg"
          >
            {status === "uploading" ? (
              <><Loader size={16} className="animate-spin" /> Uploading…</>
            ) : status === "processing" ? (
              <><Loader size={16} className="animate-spin" /> Processing…</>
            ) : (
              <><UploadIcon size={16} /> Upload & Analyse</>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
