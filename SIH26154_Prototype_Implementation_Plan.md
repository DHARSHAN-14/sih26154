# SIH26154 — Gen AI Platform for Automated Content Transformation
## Prototype Implementation Plan (Internal Selection Round)

**Scope of this document:** everything needed to build a demo-grade prototype where every capability claimed in the idea submission is *actually working* — grounding, provenance, fact validation, visual validation, repair loop, versioning, multilingual, security. Horizontal scalability is deliberately out of scope; everything else is in.

**Codename used throughout:** `sutra` (one thread from source to every output). Rename freely.

---

# PART 0 — Corrections and issues found in your two documents

Read this part before anything else. Some of these will be asked by judges.

## 0.1 Factual corrections

**a) Theme mismatch — fix before submission.**
Your idea deck (Page 1) says **Theme: Blockchain & Cybersecurity**. Your detailed report says **Smart Automation**. They contradict each other. The public SIH 2026 problem-statement listing shows SIH26154 (NTRO, "Gen AI Platform for Automated Content Transformation") under **Smart Automation** — but note that third-party mirror's theme column is visibly scrambled for several other rows, so **verify the theme directly on sih.gov.in for PS ID SIH26154 and make both documents agree.** A mismatch on Page 1 of the deck is a free, avoidable deduction.

**b) "Diarizes" is a claim you can't currently back.**
Detailed report §5 says ASR "transcribes and diarizes." Speaker diarization is a separate model (pyannote.audio), needs a gated Hugging Face token, and is fiddly. Either implement it (Phase 2, optional) or change the wording to "transcribes with timestamped segments." Don't claim it in the deck unless it runs in the demo.

**c) "python-pptx renders" — it does not.**
Detailed report §3 lists python-pptx under Template Renderer and §5 says the Visual Validator "measures rendered text against layout limits." python-pptx writes XML; it never rasterizes anything and has no idea how tall your text will be. To actually detect slide overflow you need either (i) font-metric prediction with PIL/fontTools before writing, or (ii) LibreOffice headless → PDF → PyMuPDF box extraction after writing. The plan below does both. **This is the single most underestimated component in your design** and also your best differentiator, because almost no competing team will have real layout validation.

**d) "Video package" needs an explicit definition on a slide.**
Your report correctly notes rendered video isn't required. Say so out loud in the demo: *"Video output = shot-by-shot script + storyboard + VO timing + B-roll cues, exported as a structured package."* Otherwise a judge asks "where's the video?" and you look like you skipped a deliverable. Optionally add a 15-second stitched slideshow-with-TTS as a bonus (see Phase 6, optional).

## 0.2 The one architectural weakness a sharp judge will attack

Your report itself says the brief has **no corpus-scale retrieval requirement and no knowledge-graph requirement**, and then the architecture puts RAG + KG at the centre. A good judge will ask:

> *"You're doing vector retrieval over a single 12-page PDF that fits entirely in a 128k context window. Why?"*

If your answer is "for grounding," you lose the exchange — stuffing the whole document in context is *better* grounding than retrieving 8 chunks of it.

**Fix: make retrieval conditional and honest.** Build a `RetrievalPolicy` gate:

| Source size | Route | What runs |
|---|---|---|
| ≤ ~25k tokens | **Route A — whole-source** | Full document goes into fact extraction. No vector search. Faster, higher recall, fewer failure modes. |
| > ~25k tokens, or multi-file upload, or audio/video > 20 min | **Route B — retrieval** | Chunk → hybrid search (dense + sparse) → rerank → extract per topic cluster |

Then your answer becomes:

> *"Retrieval isn't decoration — it's a size-triggered route. Small source, we don't use it, because context beats retrieval there. Drop in a 200-page annual report or a 90-minute briefing transcript and Route B engages. We'll demo both."*

That is a winning answer, and it costs you one `if` statement plus a chunk of honesty.

**Same treatment for the Knowledge Graph.** Vector search is genuinely bad at three things this PS needs, so scope the KG to exactly those and say so:
1. **Entity resolution** — "NTRO", "the Organisation", "it" all resolving to one node, so a fact stated in §2 and referenced in §7 doesn't become two contradictory facts.
2. **Timeline consistency** — event ordering, so an advisory can't say "patched before disclosure."
3. **Contradiction detection** — two edges with the same (subject, predicate) and different objects is a *structural* contradiction, found deterministically, not by asking an LLM nicely.

A KG that does those three things earns its place in your architecture diagram. A KG that just stores triples nobody queries does not — and judges can tell the difference.

## 0.3 Redundancy worth collapsing

Cross-output contradiction checking is *mostly* subsumed by the locked Source of Truth: if every claim in every output must cite `fact_ids` and every claim is entailment-checked against those facts, two outputs cannot contradict on facts. Keep the cross-output check, but scope it to what the SoT can't catch:
- **Numeric rounding drift** — "₹4.2 crore" in the exec summary vs "₹4,20,00,000" in the advisory vs "over ₹4 cr" on LinkedIn: all traceable to one fact, all cosmetically different. Normalize and compare.
- **Emphasis inversion** — the advisory calls it critical, the LinkedIn post calls it minor. Compare severity/sentiment labels attached to shared facts.
- **Selective omission** — LinkedIn post cites fact F-3 but drops the caveat fact F-4 that F-3 depends on. This is the interesting one; model it as a `depends_on` edge in the SoT and enforce "if you cite F-3, you must cite F-4 or drop F-3."

That last rule is a genuinely novel, demoable guarantee. Nobody else will have it.

## 0.4 Missing from both documents: evaluation

Neither document contains a single number. For a tough internal round, this is the gap to close. You need a slide that says:

> Validation OFF: 11.4% of generated claims contained an unsupported number, name or date.
> Validation ON: 0%. 4 outputs were auto-repaired, 1 escalated to human review.
> Layout failures caught pre-publish: 7 of 7.

That requires a small eval harness and a labelled golden set (Phase 7). It is roughly 1.5 days of work and it is the highest-ROI 1.5 days in this entire plan. It also plays directly to your existing strength with evaluation infrastructure — reuse the LiteLLM-gateway pattern you already know rather than inventing a new one.

---

# PART 1 — Locked architecture decisions

These are the decisions the rest of the plan depends on. Settle them on day 0; changing them later costs days.

## 1.1 The Source of Truth is the product

Everything else is replaceable. Get this schema right first and the rest of the system is plumbing.

```python
# backend/app/core/schemas.py  (abridged)

class Provenance(BaseModel):
    doc_id: str
    locator: str            # "p4" | "t00:14:22" | "slide3" | "sheet1!B7"
    page: int | None
    bbox: tuple[float, float, float, float] | None   # normalized 0-1, from Docling
    char_start: int | None
    char_end: int | None
    chunk_id: str
    snippet: str            # the exact source sentence, ≤300 chars — powers the provenance panel

class NormalizedValues(BaseModel):
    numbers: list[Quantity]     # {value, unit, raw, scale}
    dates: list[DateSpan]       # ISO-normalized, with granularity
    entities: list[EntityRef]   # {surface, canonical_id, type}

class Fact(BaseModel):
    fact_id: str                # "F-014" — stable, referenced everywhere
    type: Literal["metric","event","attribute","relation","claim","quote","definition"]
    subject: str
    predicate: str
    object: str
    canonical_text: str         # one self-contained sentence a human can verify
    normalized: NormalizedValues
    provenance: list[Provenance]      # ≥1, more = higher support
    confidence: float                 # 0-1, see §1.4
    contradicts: list[str] = []       # other fact_ids
    depends_on: list[str] = []        # caveat / qualifier facts (see §0.3)
    sensitivity: Literal["public","internal","restricted"] = "internal"

class SourceOfTruth(BaseModel):
    sot_id: str
    session_id: str
    version: int
    facts: list[Fact]
    entities: list[Entity]
    timeline: list[TimelineEvent]
    graph_ref: str              # path to serialized KG
    locked_at: datetime
    lock_hash: str              # sha256 over sorted canonical_texts — the freeze
```

**The lock is not metaphorical.** After `lock()`, the SoT object is immutable in memory and on disk; every generation call receives the hash; the fact checker refuses to validate against a different hash. Show the hash in the UI. It makes "locked source of truth" a verifiable claim rather than a slide bullet.

## 1.2 Every generated claim carries fact IDs

This is the mechanism that makes validation deterministic. The generator never returns free prose. It returns:

```json
{
  "section": "affected_systems",
  "claims": [
    {"text": "Apache Struts 2.5.30 and earlier are affected.", "fact_ids": ["F-014"]},
    {"text": "No exploitation has been observed in the wild.", "fact_ids": ["F-021"]}
  ]
}
```

Enforced with **constrained decoding against the JSON schema**, not by asking politely. Then validation is mechanical:

1. **Citation check** — every `fact_ids` entry exists in the locked SoT. Missing → hard fail.
2. **Token-grounding check** — every number, date, named entity, CVE ID, currency amount and percentage extracted from `text` must appear in the union of `normalized` values of the cited facts (after unit/format normalization). Any leftover → **unsupported token**, hard fail. *This is the hallucination catcher and it is 100% deterministic.*
3. **Entailment check** — NLI model scores `text` as entailed by the concatenation of cited `canonical_text`s. Below threshold → soft fail → repair.
4. **Dependency check** — if a cited fact has `depends_on`, those facts must also be cited in the same output. Else → soft fail.

Steps 1, 2 and 4 need no LLM. Step 3 needs a 180M-parameter NLI cross-encoder, not a frontier model. Say this on stage: *"Our hallucination detector costs about 3 milliseconds and cannot itself hallucinate."*

## 1.3 Templates are contracts, in YAML, loaded at runtime

Two contracts per output type, in one file. Example (`advisory.yaml`):

```yaml
id: advisory
version: 1
renderer: docx
content_contract:
  sections:
    - key: title
      required: true
      max_chars: 120
      prefers_fact_types: [event, attribute]
    - key: severity
      required: true
      enum: [Critical, High, Medium, Low, Informational]
      source: fact_or_gap          # never invented
    - key: affected_systems
      required: true
      min_facts: 1
      on_missing: flag_gap          # NOT "generate anyway"
    - key: technical_details
      required: false
      min_facts: 2
    - key: recommended_actions
      required: true
      min_facts: 1
    - key: references
      required: true
      render: provenance_list
layout_contract:
  max_pages: 2
  font: {family: "Noto Sans", body_pt: 10.5, heading_pt: 14}
  checks: [page_count, empty_section, orphan_heading, table_overflow]
parameter_bindings:
  detail_level:
    low:    {include: [title, severity, affected_systems, recommended_actions], max_claims_per_section: 2}
    medium: {include: [title, severity, affected_systems, technical_details, recommended_actions], max_claims_per_section: 4}
    high:   {include: "*", max_claims_per_section: 8}
  audience:
    executive:  {tone: neutral-formal, jargon: strip, prefers_fact_types: [metric, event]}
    technical:  {tone: precise, jargon: keep, prefers_fact_types: [attribute, relation]}
    public:     {tone: plain, jargon: strip, sensitivity_max: public}
  language: {supported: [en, hi, ta], generate_in_target: true}
```

Two things this buys you:
- **"Parameters reshape the plan, not just the wording"** stops being an assertion. Flip `detail_level` from `low` to `high` live on stage and *sections appear*. That is a five-second demo beat that proves the claim.
- **`sensitivity_max: public`** means selecting audience = public *structurally excludes* facts marked restricted from ever entering the prompt. For an NTRO judge, information-flow control by construction is a very strong signal.

## 1.4 Confidence scoring — define it, don't hand-wave it

Judges ask "where does 0.87 come from?" Answer with a formula, not a vibe:

```
confidence = w1·extraction_agreement      # same fact extracted in ≥2 of 3 passes / self-consistency
           + w2·source_quality            # OCR conf, ASR conf, or 1.0 for native text
           + w3·support_count_bonus       # appears in multiple places in the source
           - w4·contradiction_penalty     # participates in a contradiction edge
```
Weights in `config.py`, thresholds in one place, printed in the UI's fact table. `confidence < 0.5` → excluded from generation unless the operator overrides. `0.5–0.75` → usable but auto-caveated ("reportedly", "according to the source"). `> 0.75` → stated plainly.

## 1.5 Model routing — sovereign by default, fast when needed

Use **LiteLLM as the single gateway** so every call site is provider-agnostic, and expose the backend as a UI toggle:

| Mode | Backend | Use |
|---|---|---|
| **Sovereign** | vLLM or Ollama on your RTX 5060 Ti 16GB, `Qwen3-8B-Instruct` AWQ/GGUF Q5 | The demo mode for NTRO. Nothing leaves the machine. |
| **Fast** | Cloud API (whichever you have credits on) | Rehearsals, eval runs, fallback if GPU misbehaves |

Having the toggle *visible in the UI* is worth more than either mode alone. "Air-gapped deployable" becomes something you click rather than something you claim.

**Hardware note for your card:** the 5060 Ti is Blackwell (compute capability sm_120). PyTorch wheels built against CUDA ≤12.6 will fail with `no kernel image is available for execution on the device` even though `torch.cuda.is_available()` returns True. Install a **cu128 or newer build**; verify with `torch.cuda.get_arch_list()` containing `sm_120` before you build anything else. Budget half a day for environment setup and do it on day 0, not the night before.

**vLLM API note:** structured output parameters changed. `guided_json` was removed in v0.12.0; use `structured_outputs={"json": schema}` (xgrammar backend). If you copy a 2025 tutorial you will silently get unconstrained output.

## 1.6 Everything streams

The pipeline has ~10 stages and takes 1–4 minutes. A spinner for 4 minutes kills a demo. Emit a Server-Sent Event on every stage transition and render a live pipeline view: stage name, elapsed time, artifacts produced, checks passed/failed. The judges watch the system think. This is disproportionately persuasive and costs about half a day.

---

# PART 2 — Tech stack

| Layer | Choice | Why this one |
|---|---|---|
| Language / runtime | Python 3.11, Node 20 | 3.11 for library compat; avoid 3.13 (some ML wheels lag) |
| API | FastAPI + Uvicorn, Pydantic v2 | Schema-first, and Pydantic models double as LLM output schemas |
| Job orchestration | In-process async pipeline + SQLite job store | Celery/Redis is scalability theatre for a demo. Skip it. |
| Streaming | SSE (`sse-starlette`) | Simpler than WebSockets, one-way is all you need |
| Ingestion | **Docling** (MIT, LF AI & Data) | One library covers PDF/DOCX/PPTX/XLSX/HTML/images + audio ASR, emits a unified `DoclingDocument` **with page + bbox provenance** — which is exactly what your provenance panel needs. Runs fully local. |
| OCR engine | RapidOCR or EasyOCR via Docling; Granite-Docling VLM pipeline for hard scans | Docling wraps them; you get a confidence signal per span |
| ASR | Docling ASR pipeline / `faster-whisper` (`large-v3-turbo`, int8) | Timestamps become provenance locators |
| Video | `ffmpeg` → audio track + keyframes at scene cuts | Keyframes go through OCR for slide-in-video text |
| Chunking | `docling-core` HybridChunker | Preserves provenance through chunking — do not write your own |
| Embeddings | `BAAI/bge-m3` | Multilingual (needed for hi/ta), and gives dense + sparse in one model, so hybrid search is one index not two |
| Vector store | **Qdrant** (Docker) | Native hybrid dense+sparse, payload filters, runs offline. LanceDB is the zero-ops fallback. |
| Reranker | `BAAI/bge-reranker-v2-m3` | Small, multilingual, big precision gain on Route B |
| Knowledge graph | **NetworkX** in-process, persisted as JSON; Cytoscape.js to visualize | Neo4j is a deployment risk for a 2-week build and buys nothing you need. NetworkX *is* a real graph. |
| LLM gateway | **LiteLLM** | Provider-agnostic call sites; you already know this pattern |
| Local inference | vLLM (preferred, gives constrained decoding) or Ollama | vLLM's xgrammar backend enforces your JSON schemas at the token level |
| NLI / entailment | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | Multilingual entailment; ~15ms/pair on GPU; cannot hallucinate |
| NER / normalization | spaCy (`en_core_web_trf`) + `dateparser` + custom regex for CVE/IP/currency/percent | Deterministic token grounding depends on this |
| Renderers | `python-pptx`, `python-docx`, Jinja2 + HTML/CSS, `WeasyPrint` (PDF) | Standard, offline, well-documented |
| Visual validation | **Playwright** (HTML), **LibreOffice headless + PyMuPDF** (pptx/docx), PIL + fontTools (pre-render prediction) | See §1 correction (c) — this is the real implementation |
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui, Zustand | Fast to build, looks professional without a designer |
| Visualization | Cytoscape.js (KG), `react-pdf` (previews) | |
| Storage | SQLite + filesystem artifact store | One file to back up; trivially reproducible on demo day |
| Packaging | Docker Compose (api, qdrant, worker-gpu, web) | "Runs on-prem" demonstrated by `docker compose up` |
| Eval | pytest + a custom harness writing JSONL results | Produces the numbers for your results slide |

**Deliberate exclusions, with the reason to give if asked:** Kubernetes, Kafka, Neo4j, Celery, fine-tuning, a separate BM25 service. All are scalability or scale-out concerns; the prototype's job is to prove correctness guarantees, not throughput.

---

# PART 3 — Repository structure and what every file does

## 3.1 The tree

```
sutra/
├── docker-compose.yml
├── Makefile
├── .env.example
├── README.md
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── deps.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes_session.py
│   │   │   ├── routes_source.py
│   │   │   ├── routes_sot.py
│   │   │   ├── routes_jobs.py
│   │   │   ├── routes_outputs.py
│   │   │   ├── routes_stream.py
│   │   │   ├── routes_versions.py
│   │   │   └── routes_admin.py
│   │   │
│   │   ├── core/
│   │   │   ├── schemas.py            ★
│   │   │   ├── params.py
│   │   │   ├── events.py
│   │   │   ├── ids.py
│   │   │   ├── hashing.py
│   │   │   └── errors.py
│   │   │
│   │   ├── security/
│   │   │   ├── sanitizer.py          ★
│   │   │   ├── spotlight.py
│   │   │   ├── classifier.py
│   │   │   └── isolation.py
│   │   │
│   │   ├── ingest/
│   │   │   ├── router.py
│   │   │   ├── docling_adapter.py    ★
│   │   │   ├── asr.py
│   │   │   ├── video.py
│   │   │   ├── chunker.py
│   │   │   ├── quality.py
│   │   │   └── store.py
│   │   │
│   │   ├── retrieval/
│   │   │   ├── policy.py             ★
│   │   │   ├── embedder.py
│   │   │   ├── vectorstore.py
│   │   │   ├── hybrid.py
│   │   │   ├── reranker.py
│   │   │   └── decompose.py
│   │   │
│   │   ├── kg/
│   │   │   ├── extractor.py
│   │   │   ├── resolver.py           ★
│   │   │   ├── graph.py
│   │   │   ├── contradiction.py      ★
│   │   │   └── export.py
│   │   │
│   │   ├── sot/
│   │   │   ├── extractor.py          ★
│   │   │   ├── normalizer.py         ★
│   │   │   ├── confidence.py
│   │   │   ├── dependencies.py
│   │   │   ├── builder.py
│   │   │   ├── lock.py
│   │   │   └── diff.py               ★
│   │   │
│   │   ├── planner/
│   │   │   ├── planner.py            ★
│   │   │   ├── parameter_policy.py
│   │   │   ├── selection.py
│   │   │   ├── coverage.py           ★
│   │   │   └── gapfill.py
│   │   │
│   │   ├── templates/
│   │   │   ├── registry.py
│   │   │   ├── contract.py
│   │   │   └── defs/
│   │   │       ├── linkedin.yaml
│   │   │       ├── twitter_x.yaml
│   │   │       ├── advisory.yaml
│   │   │       ├── executive_summary.yaml
│   │   │       ├── presentation.yaml
│   │   │       ├── infographic.yaml
│   │   │       └── video_package.yaml
│   │   │
│   │   ├── generation/
│   │   │   ├── llm.py                ★
│   │   │   ├── generator.py
│   │   │   ├── budgets.py
│   │   │   ├── language.py
│   │   │   └── prompts/
│   │   │       ├── extract_facts.j2
│   │   │       ├── extract_triples.j2
│   │   │       ├── plan_output.j2
│   │   │       ├── generate_section.j2
│   │   │       ├── repair_claim.j2
│   │   │       └── style_guide.j2
│   │   │
│   │   ├── validation/
│   │   │   ├── citation.py
│   │   │   ├── grounding.py          ★
│   │   │   ├── entailment.py
│   │   │   ├── dependency.py
│   │   │   ├── cross_output.py
│   │   │   ├── report.py
│   │   │   └── repair.py             ★
│   │   │
│   │   ├── render/
│   │   │   ├── base.py
│   │   │   ├── pptx_renderer.py
│   │   │   ├── docx_renderer.py
│   │   │   ├── html_renderer.py
│   │   │   ├── social_renderer.py
│   │   │   ├── video_package.py
│   │   │   ├── pdf.py
│   │   │   └── assets/
│   │   │
│   │   ├── visual/
│   │   │   ├── predict.py            ★
│   │   │   ├── office.py
│   │   │   ├── pdf_probe.py          ★
│   │   │   ├── html_probe.py         ★
│   │   │   ├── rules.py
│   │   │   ├── autofix.py
│   │   │   └── screenshot.py
│   │   │
│   │   ├── orchestrator/
│   │   │   ├── pipeline.py           ★
│   │   │   ├── stages.py
│   │   │   ├── job_store.py
│   │   │   ├── review_queue.py
│   │   │   └── versioning.py
│   │   │
│   │   └── db/
│   │       ├── models.py
│   │       └── migrations/
│   │
│   ├── evals/
│   │   ├── golden/
│   │   │   ├── cyber_advisory_source.pdf     + labels.json
│   │   │   ├── scanned_report.pdf            + labels.json
│   │   │   ├── briefing_audio.mp3            + labels.json
│   │   │   ├── contradictory_report.docx     + labels.json
│   │   │   ├── injected_document.pdf         + labels.json
│   │   │   └── long_annual_report.pdf        + labels.json
│   │   ├── run_eval.py               ★
│   │   ├── metrics.py
│   │   ├── ablations.py              ★
│   │   └── report.py
│   │
│   └── tests/
│       ├── test_normalizer.py        ★
│       ├── test_grounding.py
│       ├── test_contracts.py
│       ├── test_lock.py
│       ├── test_visual_pptx.py
│       ├── test_injection.py
│       └── test_pipeline_e2e.py
│
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── store/
│       │   └── session.ts
│       ├── api/
│       │   └── client.ts
│       ├── pages/
│       │   ├── Upload.tsx
│       │   ├── Configure.tsx         ★
│       │   ├── Truth.tsx             ★
│       │   ├── Run.tsx               ★
│       │   ├── Results.tsx
│       │   └── Versions.tsx
│       └── components/
│           ├── PipelineStage.tsx
│           ├── ProvenancePanel.tsx   ★
│           ├── ValidationBadge.tsx
│           ├── UnsupportedToken.tsx  ★
│           ├── GraphView.tsx
│           ├── ArtifactPreview.tsx
│           ├── LayoutFailure.tsx     ★
│           ├── SecurityBadge.tsx
│           └── ModelToggle.tsx
│
└── infra/
    ├── qdrant/
    ├── models/
    └── seed/                         ★
```

★ = load-bearing. If you're triaging effort, these are the files that determine whether the demo lands.

---

## 3.2 File-by-file specification

### Root

**`docker-compose.yml`** — Four services: `api` (FastAPI, GPU passthrough via `deploy.resources.reservations.devices`), `qdrant` (with a named volume so the index survives restarts), `web` (Vite dev server or a static nginx build), and optionally `vllm` if you serve the model in its own container rather than in-process. Mount `infra/models/` into `api` so model weights are cached on the host and not re-downloaded on every rebuild. This file *is* your "runs on-prem" claim — make sure `docker compose up` genuinely works from a cold clone, because you may be asked to prove it.

**`Makefile`** — Thin wrappers so nobody on the team has to remember flags: `make dev` (compose up with reload), `make eval` (run the golden set and print the metrics table), `make demo-seed` (regenerate the offline fallback run), `make reset` (wipe SQLite, Qdrant collections and artifacts for a clean demo), `make check` (ruff + mypy + pytest). Six commands is enough; more and nobody uses them.

**`.env.example`** — Every knob the system reads, with safe defaults and a comment per line: model endpoints (`LITELLM_LOCAL_BASE`, cloud keys), `MODEL_BACKEND=sovereign|fast`, `RETRIEVAL_TOKEN_THRESHOLD`, confidence weights, `ENTAILMENT_THRESHOLD`, `MAX_REPAIR_ATTEMPTS`, `DEMO_MODE`. Commit the example, gitignore the real `.env`. Anything hard-coded in a module that should be here will cost you a rebuild during rehearsal.

**`README.md`** — Setup in under ten steps, the architecture diagram, and — importantly — the *demo runbook*: exact click sequence, expected timings, and how to trigger demo mode. Write the runbook in Phase 6, not on the morning of the demo.

### `backend/` top level

**`pyproject.toml`** — Pinned dependencies (pin exactly; a surprise minor-version bump in Docling or vLLM two days before the demo is a real failure mode). Includes the torch cu128 index URL for Blackwell. Separate `[dependency-groups]` for `dev` (pytest, ruff, mypy) and `eval` so the demo image stays lean.

**`Dockerfile`** — CUDA base image, Python 3.11, and three easy-to-forget system installs: **LibreOffice** (`libreoffice-impress`, `libreoffice-writer`) for the office→PDF conversion path, **fonts-noto** including Devanagari and Tamil for Indic rendering, and **ffmpeg** for the video path. Also runs `playwright install chromium`. Multi-stage build; if the image exceeds ~8 GB your demo-day rebuild becomes a liability.

### `app/` top level

**`main.py`** — Constructs the FastAPI app, mounts routers, configures CORS for the Vite origin, and — critically — runs a **startup warm-up** that loads the embedder, reranker and NLI model into GPU memory and issues one dummy LLM call. Without warm-up, the first request of the demo takes 40 seconds of model loading while the judges watch a spinner. Also registers the global exception handler that maps `errors.py` types to user-facing messages.

**`config.py`** — A single Pydantic `Settings` object read from environment. Everything tunable lives here: the retrieval token threshold, the four confidence weights, the three confidence bands (exclude / caveat / state plainly), the entailment threshold, repair attempt caps, per-format token budgets, and feature flags (`ENABLE_KG`, `ENABLE_ROUTE_B`, `ENABLE_VIDEO_PACKAGE`, `DEMO_MODE`). The rule: **if a judge could ask "why that number?", the number lives in this file and nowhere else.** The feature flags also give you a graceful way to disable a component that breaks the night before.

**`deps.py`** — FastAPI dependency providers for the session store, database session, vector client, and the singleton model handles. Keeps heavyweight objects out of module-level globals so tests can inject fakes and the eval harness can run without a running server.

### `app/api/`

**`routes_session.py`** — `POST /session` creates an isolated workspace: a UUID, a jailed directory under the artifact root, a dedicated Qdrant collection name, and a row in the session table. Everything downstream is scoped by `session_id`. This endpoint is what makes "per-session isolation prevents cross-operator leakage" a structural property rather than a promise.

**`routes_source.py`** — `POST /session/{id}/source` accepts multi-file upload, writes to content-addressed storage, and kicks off ingestion as a background task returning immediately with a job handle. `GET` returns ingestion status and the parsed document preview (per-page text with OCR confidence). Enforces size and MIME allow-lists; rejects anything not in the supported set with a clear message rather than failing deep in Docling.

**`routes_sot.py`** — The operator's control surface over the fact set. `GET /sot` returns the full fact table with confidence, provenance and contradiction flags. `POST /facts/{fid}/resolve` lets the operator pick a winner among contradicting facts or exclude one. `POST /facts/{fid}/exclude` drops a fact from generation entirely. `POST /lock` freezes the SoT, computes the hash, and returns it. **After lock, all mutating routes on this router return 409.** That refusal is worth demonstrating.

**`routes_jobs.py`** — `POST /session/{id}/generate` takes `{formats: [...], params: {audience, tone, language, detail_level, objective, style}}`, validates the params against the enums in `core/params.py`, verifies the SoT is locked, and starts the orchestrator. Returns a `job_id` immediately; all progress arrives over SSE. Rejects generation against an unlocked SoT — that ordering constraint is the whole point of the lock.

**`routes_outputs.py`** — Lists outputs for a job with their validation verdicts; `GET /outputs/{id}` returns the structured claims plus the validation report; `GET /outputs/{id}/download` streams the rendered artifact with the right MIME type; `GET /outputs/{id}/provenance` returns the claim → fact → source-span mapping that powers the provenance panel. Keep the provenance payload denormalized (snippet text included) so the frontend needs one call, not N.

**`routes_stream.py`** — SSE endpoint (`sse-starlette`) that subscribes to the session's event bus and streams `StageEvent` objects. Sends a heartbeat comment every 15 seconds so proxies don't drop the connection, and replays the last N events on reconnect so a browser refresh mid-run doesn't lose the pipeline view. This is a small file that carries the most visible part of the demo.

**`routes_versions.py`** — `POST /session/{id}/source/v2` ingests a revised source, builds a second SoT, diffs it against v1, and returns added/removed/changed facts plus the list of previously generated outputs now affected by stale facts. `POST /regenerate` queues only those outputs. Prior versions stay readable — never overwrite v1 artifacts.

**`routes_admin.py`** — Model backend toggle (sovereign ↔ fast, applied at the LiteLLM layer), health check that reports GPU memory, loaded models, Qdrant reachability and LibreOffice availability, and a `POST /eval/run` trigger. The health endpoint saves you fifteen minutes of panic on demo morning; build it early.

### `app/core/`

**`schemas.py`** ★ — The contract every other module codes against: `Provenance`, `Quantity`, `DateSpan`, `EntityRef`, `NormalizedValues`, `Fact`, `Entity`, `TimelineEvent`, `SourceOfTruth`, `ContentPlan`, `SectionPlan`, `Claim`, `GeneratedOutput`, `RenderedArtifact`, `ValidationReport`, `UnsupportedToken`, `RepairInstruction`, `GapReport`. **Freeze this on day 1 and change it only by team agreement**, because six people are simultaneously writing against it. The same Pydantic models are reused as JSON schemas for constrained decoding, so a field rename silently changes what the LLM is allowed to emit — that dual role is exactly why it must stabilize early.

**`params.py`** — The six operator parameters as strict enums: `Audience` (executive/technical/public/field), `Tone` (neutral/formal/urgent/plain), `Language` (en/hi/ta), `DetailLevel` (low/medium/high), `Objective` (inform/warn/persuade/instruct), `ContentStyle` (narrative/bulleted/analytical). Enums rather than free strings so the template `parameter_bindings` can be validated at startup and the UI controls can be generated from them. Any parameter value with no binding in any template is a startup error, not a runtime surprise.

**`events.py`** — `StageEvent` (stage name, status, timestamp, duration, message, counters, artifact refs) plus the in-process pub/sub bus and an `emit()` helper. Every stage function calls `emit()` on entry and exit. Keep the event payload small and serializable; the frontend renders it directly. Also persist events to the DB so a run can be replayed for the offline demo mode.

**`ids.py`** — Generators for `fact_id` (`F-001`, zero-padded and sortable so the UI table orders naturally), `claim_id`, `chunk_id`, `doc_id`, `job_id`. Stability matters: the same fact extracted in a re-run of the same source should keep its ID, otherwise the version diff and the provenance links break.

**`hashing.py`** — Computes `lock_hash` as SHA-256 over the sorted, canonicalized fact texts plus their provenance locators, and provides `verify(sot, hash)` used by the validators. Also content-addresses uploaded files. The canonicalization must be deterministic (sorted keys, normalized whitespace) or the hash changes between runs and the demo's headline claim quietly breaks.

**`errors.py`** — Typed exceptions with user-facing messages: `SoTNotLocked`, `SoTAlreadyLocked`, `UnsupportedSourceType`, `ExtractionFailed`, `ContractViolation`, `RenderFailed`, `ValidationExhausted`, `InjectionDetected`. Mapped to HTTP status codes in `main.py`. The point is that a failure shows a sentence a judge can read, not a stack trace.

### `app/security/`

**`sanitizer.py`** ★ — Runs over every ingested text span *before* it can reach a prompt. Detects and neutralizes indirect prompt injection: imperative override phrasing ("ignore previous instructions", "you are now", "system:"), fake role markers and chat-template tokens, zero-width and bidirectional Unicode control characters, invisible/white-on-white text extracted from PDFs, and embedded base64 blobs. Returns `(clean_text, detections[])` where each detection carries the span, the pattern class and the provenance — so the UI can show *which page* of *which document* carried the attempt. Neutralize by escaping and annotating rather than deleting, so the operator can still see what the document said.

**`spotlight.py`** — Builds the prompt envelope: source content wrapped in unambiguous delimiters, datamarked, preceded by an instruction stating that everything inside the delimiters is untrusted data and never an instruction. Every prompt that includes source-derived text must be constructed through this module — no module should ever f-string source text into a prompt directly. Enforce that with a lint rule or a code-review convention.

**`classifier.py`** — A second opinion beyond regex: a small heuristic scorer (imperative density, second-person address to a model, presence of tool/format directives) with an optional lightweight model check. Produces a risk score per span that feeds both the detections list and `Fact.confidence`. Keep it cheap; this runs over every chunk.

**`isolation.py`** — Enforces the session jail: path resolution that refuses to escape the session directory, a guard that rejects any DB query missing a `session_id` filter, and artifact access checks. Small file, but it's what lets you answer the concurrent-operators edge case in your report with a mechanism rather than an intention.

### `app/ingest/`

**`router.py`** — Maps MIME type and extension to the right pipeline (Docling standard, Docling VLM for hard scans, ASR, video). Handles multi-file uploads by ingesting each and merging into one `InternalDoc` set under a shared `session_id`, keeping per-file `doc_id`s so provenance stays attributable to the right document. Also decides when to escalate a low-confidence OCR page to the VLM pipeline for a second pass.

**`docling_adapter.py`** ★ — Wraps Docling's `DocumentConverter` and maps the resulting `DoclingDocument` items into your `InternalDoc` model, **preserving page number, normalized bounding box, character offsets and per-span OCR confidence**. This mapping is what makes the provenance panel possible; if bounding boxes are lost here, no amount of downstream work recovers them. Configure the pipeline options (OCR engine, table structure model, VLM preset) from `config.py` rather than inline, so you can switch engines without touching the adapter.

**`asr.py`** — faster-whisper wrapper (`large-v3-turbo`, int8 on GPU) producing timestamped segments. Each segment becomes a chunk whose `Provenance.locator` is a timestamp like `t00:14:22`, so a claim in the advisory can be traced back to a moment in the briefing audio. Exposes per-segment average log-probability as the confidence signal. Optional diarization hook, off by default (see Part 0 correction b).

**`video.py`** — ffmpeg orchestration: demux the audio track for `asr.py`, detect scene cuts, extract keyframes, and run those keyframes through OCR so text that only appears on screen (slides inside a recorded briefing) enters the fact pool. Merges both streams into one time-ordered document. Guard with timeouts and a max-duration cap; a 2-hour video will otherwise eat your demo.

**`chunker.py`** — Configures Docling's `HybridChunker` (tokenizer-aware, structure-aware) and asserts the invariant that **every emitted chunk carries at least one valid `Provenance`**. Do not write a custom splitter; naive character splitting destroys the page/bbox mapping and you will not notice until the provenance panel shows wrong pages. Chunk size tuned to the embedder's window, with overlap configured in `config.py`.

**`quality.py`** — Aggregates per-span OCR confidence, ASR log-probability and structural signals (was this text in a table? a figure caption? a header?) into a per-chunk quality score that feeds `sot/confidence.py`. Also flags spans below the threshold so the UI can show an OCR confidence heatmap over the source preview — a small feature that reads as very thorough in a demo.

**`store.py`** — Persists the raw uploaded file and the parsed `InternalDoc` immutably, content-addressed by hash. Immutability matters for the versioning story: v2 never overwrites v1, and the diff has something real to compare against.

### `app/retrieval/`

**`policy.py`** ★ — Implements the Route A / Route B decision from §0.2. Token-counts the parsed source, checks file count and media duration, and returns a `RetrievalDecision` object carrying the route, the measured token count, the threshold and a human-readable reason. **Log it and show it in the UI** ("Route A — 8,400 tokens, fits in context; retrieval skipped"). This one small file converts your weakest architectural point into a prepared answer.

**`embedder.py`** — bge-m3 wrapper producing dense and sparse (lexical) vectors in a single forward pass, batched, with a small on-disk cache keyed by chunk hash so re-runs during development don't re-embed. Multilingual by design, which is what lets Hindi and Tamil outputs retrieve against an English source.

**`vectorstore.py`** — Qdrant client. Creates one collection per session with both dense and sparse vector configs, stores the full `Provenance` in the payload so retrieval results arrive already traceable, and provides payload-filtered search (by `doc_id`, by section, by sensitivity). Includes teardown so `make reset` leaves no stale collections.

**`hybrid.py`** — Runs dense and sparse retrieval and fuses with Reciprocal Rank Fusion. RRF over score normalization, because it needs no per-corpus tuning — which matters when your corpus is whatever the operator just uploaded. Returns a ranked candidate list with both component ranks retained for debugging.

**`reranker.py`** — bge-reranker-v2-m3 cross-encoder over the fused top-k (typically 50 → 8). This is where most of the precision on Route B comes from. Batched, GPU, with a configurable cutoff; falls back to fusion order if the model fails to load rather than crashing the pipeline.

**`decompose.py`** — Breaks a complex planner gap-fill query ("what mitigations are recommended and by when") into sub-queries, retrieves for each, and merges. Used only by `planner/gapfill.py`, not on the main path. Low priority — cut first if Phase 2 is running late.

### `app/kg/`

**`extractor.py`** — Schema-constrained triple extraction from chunks: `(subject, predicate, object, provenance, temporal_qualifier)`. Uses the same constrained-decoding path as fact extraction so output is always parseable. Predicates are drawn from a small controlled vocabulary defined in `config.py` — free-form predicates make contradiction detection impossible because "affects" and "impacts" become different edges.

**`resolver.py`** ★ — Entity resolution: clusters surface forms ("NTRO", "the Organisation", "the agency") into canonical entities via string similarity, embedding similarity and simple coreference heuristics, then assigns `canonical_id`. This is what prevents one real-world entity from producing two facts that look contradictory but aren't — and, conversely, what lets genuine contradictions surface. Keep the merge decisions inspectable; an over-eager merge produces confusing facts and you'll want to see why.

**`graph.py`** — Builds a NetworkX `MultiDiGraph` from resolved triples and provides the queries the rest of the system needs: neighbours of an entity, timeline subgraph, path between entities, edges supporting a given fact. Serializes to JSON alongside the SoT so the graph is part of the frozen state.

**`contradiction.py`** ★ — Two detectors, both deterministic. First: same `(subject, predicate)` with different `object` values that don't normalize to the same thing → contradiction edge. Second: temporal impossibility — event ordering that violates a stated sequence (patch released before vulnerability disclosed, report published before the incident). Emits contradiction edges that populate `Fact.contradicts` and the red edges in the graph view. This is the file that makes the KG earn its slot in your architecture diagram.

**`export.py`** — Converts the NetworkX graph into Cytoscape.js element JSON with styling hints (node type → colour, contradiction edges → red, confidence → opacity). Prunes to a readable subgraph for display; a 400-node hairball impresses nobody. Default view: top entities by degree plus everything involved in a contradiction.

### `app/sot/`

**`extractor.py`** ★ — Fact extraction with schema-constrained decoding, run as N independent passes (default 3) over the same content at nonzero temperature. Facts appearing in multiple passes get an agreement bonus in `confidence.py`; facts appearing once are flagged as low-agreement. Each extracted fact must carry the provenance of the chunk it came from — reject any fact the model returns without one rather than patching it in afterwards.

**`normalizer.py`** ★ — Converts every number, unit, currency amount, percentage and date into canonical comparable form: Indian numbering (lakh/crore) to absolute values, currency symbols and codes unified, percentages vs proportions disambiguated, relative dates ("last Tuesday") resolved against a document date, date granularity preserved (2026 vs March 2026 vs 2026-03-14). **The token-grounding check in `validation/grounding.py` is only as good as this file**, so it gets the most unit tests in the repo. Every normalization is reversible enough to render the original surface form back to the operator.

**`confidence.py`** — Implements the §1.4 formula: extraction agreement, source quality from `ingest/quality.py`, support count bonus, contradiction penalty. Weights and band thresholds from `config.py`. Also assigns the band (exclude below 0.5, auto-caveat 0.5–0.75, state plainly above) that the planner and generator both consume.

**`dependencies.py`** — Detects when one fact qualifies another — scope limits ("in tested configurations only"), conditions ("if remote access is enabled"), caveats ("preliminary finding") — and writes `depends_on` edges. These edges power the selective-omission check in §0.3, which is your most novel guarantee: you cannot cite a claim while silently dropping the caveat it depends on.

**`builder.py`** — Assembles everything into the `SourceOfTruth`: deduplicates facts across extraction passes, merges provenance lists for duplicates, attaches entities and the timeline, links the graph, and sorts deterministically. Deduplication is subtler than it looks — two facts with the same meaning and different wording should merge and *combine* their provenance, which is exactly what raises support count.

**`lock.py`** — Freezes the SoT: computes the hash, marks the object immutable (Pydantic `model_config = ConfigDict(frozen=True)` on the frozen copy), writes it to disk, and provides `verify_against(hash)` used by every validator. Any attempt to mutate after lock raises `SoTAlreadyLocked`. Make the immutability real, not conventional — a judge who asks "what stops the generator from adding a fact?" deserves a code answer.

**`diff.py`** ★ — Compares two SoT versions fact by fact using canonical text and provenance: returns added, removed, changed (same subject/predicate, different object) and unchanged sets. Then maps changed/removed facts to the outputs that cited them, producing the stale-output list. This file is the entire versioning feature; it's about 150 lines and buys a 30-second demo beat.

### `app/planner/`

**`planner.py`** ★ — For each (output format × operator parameters) pair, produces a `ContentPlan`: which sections to include, which `fact_ids` fill each section, and the token/character budget per section. Reads the content contract, applies parameter bindings, calls `selection.py` for ranking and `coverage.py` for gaps. The critical property: **the plan is produced before any prose is generated**, so parameters demonstrably change structure and fact selection, not just phrasing.

**`parameter_policy.py`** — Resolves the `parameter_bindings` block from a template YAML against the operator's actual parameters, composing overlapping bindings (audience *and* detail level both constrain the section list) with a defined precedence order. Also applies `sensitivity_max`, which structurally removes restricted facts from the candidate pool before the planner ever sees them.

**`selection.py`** — Ranks candidate facts for a section by relevance to the section's purpose, confidence, contract fit (does this fact type match `prefers_fact_types`?), and diversity so five near-identical facts don't fill a slide. Respects `min_facts` / `max_claims_per_section` from the contract. Pulls in `depends_on` facts automatically whenever a dependent fact is selected.

**`coverage.py`** ★ — Checks every required section against the selected facts. If a required section has no supporting evidence after `gapfill.py` has tried, it emits a `GapReport` rather than letting generation proceed. The system then **shows the operator the gap** instead of inventing content. Demo this explicitly; refusing to fabricate is a trust signal most teams cannot show, and it directly answers an edge case from your report.

**`gapfill.py`** — Before declaring a gap, issues targeted retrieval queries derived from the missing section's description (via `retrieval/decompose.py` when the query is complex). If evidence is found, it is extracted into new facts — but only *before* lock, or into a clearly marked supplementary set if after. Keeps the SoT from being under-populated just because the first extraction pass didn't ask the right question.

### `app/templates/`

**`registry.py`** — Loads every YAML in `defs/` at startup, validates it against the `contract.py` models, and cross-checks that every enum value in `core/params.py` has a binding somewhere. **Fails fast and loudly** — a malformed contract discovered at generation time during the demo is much worse than a container that refuses to start during setup. Exposes lookup by format ID and the list of available formats for the UI.

**`contract.py`** — Pydantic models for `ContentContract` (sections, required flags, min/max facts, `on_missing` behaviour, preferred fact types) and `LayoutContract` (renderer, page/slide limits, fonts, the list of visual checks to run) plus `ParameterBindings`. Typed contracts mean the planner, the generator, the renderer and the visual validator all read the same object rather than each parsing YAML their own way.

**`defs/*.yaml`** — Seven files, one per output format, each specifying both contracts and the parameter bindings. `advisory.yaml` is fully worked in §1.3 and is the template to copy. Notable per-format specifics: `twitter_x.yaml` enforces a 280-character hard limit and hashtag/URL counting; `linkedin.yaml` caps at 3,000 characters with a hook-first structure; `presentation.yaml` defines slide archetypes and per-slide text budgets that `visual/predict.py` reads directly; `infographic.yaml` defines named HTML slots that `html_probe.py` checks for emptiness; `video_package.yaml` defines shot structure, VO word-count-to-seconds ratio, and B-roll cue fields.

### `app/generation/`

**`llm.py`** ★ — The single LiteLLM-backed call site for the entire system. Handles backend routing (sovereign vs fast), schema enforcement via vLLM `structured_outputs` (note: `guided_json` was removed in v0.12.0 — see §1.5), retries with backoff, timeouts, token accounting, and a per-call trace log written to the job record. Because every LLM call goes through here, you get a complete audit trail of what the model was asked and what it returned — useful for debugging and quietly impressive if a judge asks how you'd investigate a bad output.

**`generator.py`** — Generates one output per call. Input is strictly the `ContentPlan` plus the `canonical_text` of the cited facts — **never the raw source**. That restriction is what makes cross-output consistency structural: two formats cannot diverge on facts they were never independently shown. Returns `Claim` objects with `fact_ids`; any response failing schema validation is retried once, then failed rather than parsed leniently.

**`budgets.py`** — Derives per-section token and character budgets from the layout contract and passes them into prompts and into `visual/predict.py`. Keeps the "how much text fits on a slide" number in exactly one place, so the generator and the layout validator can never disagree about it.

**`language.py`** — Handles target-language generation: selects the appropriate model, injects language and register instructions, and provides the script/font hints the renderers need for Devanagari and Tamil. Generation is in the target language directly, not translated after the fact — which matters because post-hoc translation breaks the claim-to-fact-ID mapping that validation depends on.

**`prompts/*.j2`** — Jinja2 templates, versioned in git so prompt changes are reviewable. `extract_facts.j2` and `extract_triples.j2` run at SoT build time; `plan_output.j2` assists planning; `generate_section.j2` is the workhorse that emits `{text, fact_ids}` claims and must state explicitly that unlisted facts may not be used; `repair_claim.j2` receives the exact failure reason and the permitted fact set, and is deliberately narrow; `style_guide.j2` holds the tone/audience/objective modifiers composed into the others. All of them receive source-derived text only through `security/spotlight.py`.

### `app/validation/`

**`citation.py`** — Check 1. Verifies the SoT hash matches what generation was given, then that every `fact_id` in every claim exists in that SoT. Cheap, and it catches the entire class of "the model invented a citation" failures. Hard fail — no repair attempt, straight to regeneration.

**`grounding.py`** ★ — Check 2, and the heart of the hallucination defence. Extracts every number, date, named entity, CVE ID, currency amount, percentage and proper noun from the claim text using spaCy plus domain regexes, normalizes them through `sot/normalizer.py`, and takes the set difference against the normalized values of the cited facts. Anything left over is an `UnsupportedToken` with its character span — which the frontend highlights in red. **No LLM involved**, so the detector cannot itself hallucinate. Needs careful false-positive handling for ordinals, section numbers and dates that are part of a template rather than a claim.

**`entailment.py`** — Check 3. Runs mDeBERTa NLI with the concatenated `canonical_text` of the cited facts as premise and the claim as hypothesis. Below the entailment threshold → soft fail → repair. Multilingual, so a Hindi claim can be checked against English source facts, which is what makes the multilingual story credible rather than decorative. Batched, ~15 ms per pair on GPU.

**`dependency.py`** — Check 4. For every cited fact with `depends_on` edges, verifies those facts are also cited somewhere in the same output. Catches selective omission — using a finding while dropping the caveat that qualifies it. Simple set logic, and a genuinely novel guarantee to describe on stage.

**`cross_output.py`** — Runs after all outputs are generated. Compares numeric renderings of the same fact across outputs (rounding drift), severity/sentiment labels attached to shared facts (emphasis inversion), and citation sets against `depends_on` closure across the whole batch. Produces a batch-level report; failures route individual outputs back to repair.

**`report.py`** — Aggregates the four checks plus cross-output results into a `ValidationReport` per output with a verdict: PASS, REPAIRED (with the repair history), or REVIEW (with the reason and evidence). This object is what the Results page renders, so include everything the UI needs — spans, reasons, the facts involved — rather than making the frontend re-derive it.

**`repair.py`** ★ — Builds a `RepairInstruction` naming the exact offending claim, the failure type, the character span, and the permitted `fact_ids`, then regenerates **only that section**, not the whole output. Attempts deterministic fixes first where possible (drop an unsupported adjective, re-cite a missing dependency). Caps at `MAX_REPAIR_ATTEMPTS` (default 2), then escalates to the review queue with all evidence attached. The narrowness is the point — "we regenerate one section, not one document" is a good answer to a cost question.

### `app/render/`

**`base.py`** — The `Renderer` protocol (`render(plan, claims, contract) -> RenderedArtifact`) plus shared helpers for fact-ID embedding and asset resolution. A common interface means `orchestrator/pipeline.py` treats all seven formats identically and adding an eighth format needs no pipeline change — which is exactly the extensibility claim in your report, made real.

**`pptx_renderer.py`** — python-pptx deck generation from slide archetypes defined in `presentation.yaml`. Writes each claim's `fact_id` into the shape's **alt-text**, so traceability survives into the downloaded file and the provenance panel can map back from a shape. Reads text budgets from `budgets.py` and calls `visual/predict.py` before committing a text frame. Uses a base `.pptx` template from `assets/` for consistent theming.

**`docx_renderer.py`** — python-docx for the advisory and executive summary: styled headings, tables, and a references section rendered from provenance. Embeds `fact_id`s as bookmarks or comments. Uses the Noto font family so Indic scripts render rather than boxing out.

**`html_renderer.py`** — Jinja2 → HTML/CSS infographic against named slots defined in `infographic.yaml`. Every claim is wrapped in a `<span data-fact-id="F-014">`, which does triple duty: provenance panel mapping, `html_probe.py` overflow attribution, and empty-slot detection. Self-contained output (inlined CSS, embedded fonts) so the downloaded file renders anywhere.

**`social_renderer.py`** — Plain-text renderers for LinkedIn and X with platform rules applied: character limits, hashtag and mention counts, link handling, emoji policy, and line-break conventions. Returns the text plus a structured metadata block the UI uses to render a realistic post preview.

**`video_package.py`** — Produces the structured video deliverable: numbered shot list, voiceover script with per-shot word counts converted to estimated seconds, storyboard frame descriptions, on-screen text, and B-roll cues — exported as both JSON and a readable document. **Define this on a slide** (Part 0, correction d) so nobody expects an MP4. Optional Phase 6 extension: render a slideshow with TTS if everything else is green.

**`pdf.py`** — WeasyPrint conversion for PDF variants of the advisory and executive summary, and PDF export of the infographic. Shares the HTML path, so styling stays consistent.

**`assets/`** — Fonts (Noto Sans, Noto Sans Devanagari, Noto Sans Tamil), the base pptx template, infographic CSS, and logo placeholders. Ship the fonts in-repo and install them in the Dockerfile; relying on system fonts is how Tamil output turns into a row of empty boxes on demo day.

### `app/visual/`

**`predict.py`** ★ — Pre-render fit estimation. Given the text, the font family, size and the target box dimensions from the layout contract, uses PIL/fontTools metrics to compute wrapped line count and required height, and predicts overflow **before** anything is written. Catches roughly 80% of layout problems at near-zero cost and lets `budgets.py` be enforced rather than hoped for. Also feeds `autofix.py` with the exact overshoot so the fix can be proportionate.

**`office.py`** — Runs LibreOffice headless (`soffice --headless --convert-to pdf`) in a subprocess with a hard timeout, a per-session working directory and a lock (LibreOffice misbehaves under concurrent invocations from the same profile). Caches conversions by artifact hash. Returns the PDF path or a typed failure that degrades gracefully to `predict.py`-only validation rather than failing the run.

**`pdf_probe.py`** ★ — The ground truth for layout validation. Opens the converted PDF with PyMuPDF, extracts every text block with its bounding box, and compares against the expected placeholder rectangles recorded by the renderer: text extending past its box, text crossing the page or slide margin, overlapping blocks, empty regions where a required section should be, and page/slide count against the contract. This is what turns "visual validation" from a slide bullet into a screenshot with a red rectangle on it.

**`html_probe.py`** ★ — Playwright loads the rendered infographic and injects a JS probe that walks the DOM checking `scrollWidth > clientWidth`, `scrollHeight > clientHeight`, elements whose bounding boxes escape their parent, failed image loads, WCAG contrast ratios on text over backgrounds, and empty required slots by `data-slot` attribute. Exact, fast and dependency-light — **build this before the LibreOffice path**, because it gives you a working visual validator in an afternoon.

**`rules.py`** — All visual thresholds in one place: minimum readable font size, maximum lines per bullet and bullets per slide, margin tolerance in points, minimum contrast ratio, maximum page count deviation. Read from the layout contract with these as defaults. Same principle as `config.py` — a judge asking "why 18pt?" should get a pointer to a file, not a shrug.

**`autofix.py`** — Deterministic layout repairs attempted before any LLM call: step the font down within the allowed range, split a bullet, push overflow to a continuation slide, shrink an image, tighten line spacing. Each fix is re-validated. Only if deterministic fixes fail does the content go back to `validation/repair.py` for a text rewrite. Say this explicitly on stage — "we don't spend a model call on a font size."

**`screenshot.py`** — Rasterizes artifacts to PNG for UI previews and, importantly, captures **failure evidence images**: the broken render with the offending region boxed, paired with the repaired version. That before/after pair is your strongest single demo asset (Milestone M4); generate and cache it rather than producing it live.

### `app/orchestrator/`

**`pipeline.py`** ★ — The stage graph. Runs ingest → sanitize → route → retrieve → extract → KG → SoT → lock, then fans out per selected output through plan → generate → fact-validate → render → visually-validate → repair, then the cross-output pass, then finalize. Emits a `StageEvent` at every transition, handles per-output failure isolation (one failed format must not kill the other six), and enforces the repair attempt cap. Keep the stage list declarative so the frontend can render the pipeline shape before the run starts.

**`stages.py`** — Each stage as a typed function with explicit inputs and outputs and no hidden state, so stages can be unit-tested individually and replayed from persisted intermediate artifacts. This is what makes `DEMO_MODE` replay possible and what lets a teammate debug the renderer without running ingestion.

**`job_store.py`** — SQLite-backed registry of jobs, per-output status, artifacts, validation reports and events. Also the persistence layer behind demo-mode replay. Nothing exotic; the value is that a run is fully reconstructible after a restart, which you will need at least once during rehearsal.

**`review_queue.py`** — Holds outputs that exhausted repair attempts, each with the full failure evidence: the offending claim, the span, the facts involved, the failure type, and the screenshot if it was a layout failure. Provides accept / regenerate / edit actions. Human-in-the-loop is in your report as a design principle; this file is where it becomes a screen.

**`versioning.py`** — Orchestrates the v2 flow: ingest the revised source, build SoT v2, call `sot/diff.py`, mark stale facts, compute the affected-output set from stored citations, and queue only those for regeneration while preserving v1 artifacts. About a day of work for a memorable demo beat and a direct answer to one of your report's edge cases.

### `app/db/`

**`models.py`** — SQLModel tables: `session`, `source_document`, `sot_version`, `fact` (denormalized for the fact table query), `job`, `output_artifact`, `validation_result`, `stage_event`, `review_item`, `security_detection`. Every table carries `session_id` and the isolation guard enforces it. Keep facts queryable in SQL rather than only inside a JSON blob — the Truth page needs sorting and filtering.

**`migrations/`** — Alembic or plain versioned SQL. With six people on one schema, "just delete the DB" stops being viable around day 6.

### `backend/evals/`

**`golden/`** — Six source documents, each paired with a hand-labelled `labels.json` containing the facts a correct system should extract, the traps planted in the document, and the expected system behaviour. Chosen to exercise different failure modes: a clean cyber advisory (baseline), a scanned report (OCR stress), a briefing audio file (ASR stress), a document with deliberately conflicting statements (contradiction detection), a document with an embedded prompt injection (security), and a 200-page report (Route B trigger). Labelling six documents takes an afternoon and is the input to every number you'll put on a slide.

**`run_eval.py`** ★ — Runs the full pipeline over the golden set across a matrix of parameter combinations, writes one JSONL row per generated output with all metrics attached, and is runnable headless (`make eval`) with no server. Keep it deterministic where possible — fixed seeds, fixed model, recorded prompts — so numbers are reproducible when a judge asks you to re-run it.

**`metrics.py`** — Computes grounded-claim rate, unsupported-token rate, fact precision and recall against the labels, contradiction detection rate, layout failure catch rate, repair success rate, human-escalation rate, and latency percentiles per stage. Each metric is one small, testable function; the composite table comes from combining them.

**`ablations.py`** ★ — Runs the comparisons that make your results slide: validation ON vs OFF, Route A vs Route B on the long document, sovereign vs fast model, and repair enabled vs disabled. The validation ON/OFF delta is the single most persuasive number in the entire project — it's the difference between claiming your architecture works and showing it.

**`report.py`** — Renders the metrics into a markdown table and a chart you can paste directly into the deck. Small file, but it's what converts a JSONL file into a slide at 2 a.m.

### `backend/tests/`

**`test_normalizer.py`** ★ — The highest-value test file in the repo, because `grounding.py` inherits every one of its bugs. Cover: lakh/crore conversion, currency symbols and codes, percentages vs proportions vs basis points, date granularities and relative dates, ranges and approximations ("about 40,000"), units with prefixes, and thousands separators in both Indian and international grouping. Aim for genuine breadth here; every gap is a hallucination that slips through.

**`test_grounding.py`** — Unsupported-token detection on crafted claims, including the false-positive cases that matter: section numbers, ordinals, dates that come from the template rather than the source, and numbers spelled out in words. A grounding checker that cries wolf is worse than none, because you'll start ignoring it.

**`test_contracts.py`** — Every YAML in `defs/` loads, validates, and has bindings for every parameter enum value. Runs in CI and at startup. Catches the class of error that would otherwise surface mid-demo.

**`test_lock.py`** — SoT immutability after lock, hash determinism across runs on identical input, hash change on any fact change, and that validators reject a mismatched hash. This test defends the claim you'll make out loud on stage.

**`test_visual_pptx.py`** — Feeds a deliberately overflowing deck through `predict.py` and the LibreOffice path and asserts both **fail** it, then asserts `autofix.py` produces a passing version. A visual validator that never fails anything is indistinguishable from no validator; this test is what proves otherwise.

**`test_injection.py`** — A corpus of planted injection strings (imperative overrides, fake system markers, zero-width characters, invisible PDF text) must all be detected, and an assertion that no detected span appears verbatim in any prompt sent through `llm.py`. That second assertion is the one that actually matters.

**`test_pipeline_e2e.py`** — A tiny fixture document through the full pipeline to all seven formats, asserting every output validates and every claim traces to a fact with valid provenance. Runs in CI; it's your regression net when someone refactors on day 14.

### `frontend/`

**`package.json`** — React 18, Vite, TypeScript, Tailwind, shadcn/ui, Zustand, Cytoscape.js, react-pdf. Pin versions. Keep the dependency list short; every extra library is a build risk on demo morning.

**`src/App.tsx`** — Router and shell: the five-step operator flow (Upload → Truth → Configure → Run → Results) as a visible stepper, plus the persistent header carrying `ModelToggle` and `SecurityBadge`. The stepper matters more than it sounds — it tells the judges where they are in a workflow they've never seen.

**`src/store/session.ts`** — Zustand store holding session ID, source status, the SoT and lock hash, operator parameters, job state, per-output validation results, and the SSE subscription lifecycle. Single source of truth for the client; every page reads from here so a page change mid-run doesn't lose the pipeline state.

**`src/api/client.ts`** — Typed fetch wrappers generated from or mirroring the backend Pydantic models, plus the EventSource setup with reconnect. Keeping types in sync with `core/schemas.py` by hand is fine at this scale; drifting types are not.

**`src/pages/Upload.tsx`** — Drag-and-drop multi-file upload with type and size validation, per-file ingestion progress, and a source preview showing extracted text with the OCR confidence heatmap and ASR timestamps. First screen the judges see — it should look finished.

**`src/pages/Configure.tsx`** ★ — Output format multi-select plus the six operator parameter controls, generated from `core/params.py` enums. Shows a live preview of *what will change* when a parameter moves (e.g. detail=low greys out sections that will be excluded). That preview is what makes the "parameters reshape the plan" claim visible before you even hit generate.

**`src/pages/Truth.tsx`** ★ — The fact table: canonical text, confidence bar with its band, provenance link, contradiction badges, sensitivity tag, and operator actions (resolve, exclude, override confidence). The LOCK button and the resulting hash are the visual centrepiece. Also hosts `GraphView`. Spend real design time here; it's the screen that most clearly communicates that you built something other teams didn't.

**`src/pages/Run.tsx`** ★ — The live pipeline view driven by SSE: every stage as a card with status, elapsed time, counters (facts extracted, chunks retrieved, checks passed/failed) and per-output fan-out. Judges watch this for ninety seconds; it must look alive and legible from three metres away. Include a subtle "Route A — retrieval skipped, source fits in context" annotation so the routing decision is visible without you narrating it.

**`src/pages/Results.tsx`** — Per-output preview, validation report, provenance panel, download, and the review queue for escalated items. Tabs across the seven formats. Each tab shows its verdict badge immediately so the overall picture reads at a glance.

**`src/pages/Versions.tsx`** — v1 vs v2 side by side with the fact diff colour-coded, the stale fact list, the affected-output list, and a regenerate action. Keep prior versions openly accessible — auditability is the point.

**`src/components/PipelineStage.tsx`** — One stage card: name, status icon, duration, expandable detail with counters and messages. Animates on transition. Small component, heavily reused, worth polishing.

**`src/components/ProvenancePanel.tsx`** ★ — Click a claim → shows the cited facts → shows each fact's source snippet with the page image and bounding-box highlight overlaid on the original document. The single feature that most directly proves "claim-level provenance" isn't a slide bullet. Needs `bbox` to have survived from `docling_adapter.py`, which is why that file is starred too.

**`src/components/ValidationBadge.tsx`** — PASS / REPAIRED / REVIEW badge with the failure reason and repair history on hover. Consistent colour language across every screen so a judge learns it once.

**`src/components/UnsupportedToken.tsx`** ★ — Renders claim text with ungrounded spans highlighted in red and a tooltip explaining what wasn't found in the source. Used in the validation-OFF demo to show what the system catches. This component is the visual form of your core technical claim.

**`src/components/GraphView.tsx`** — Cytoscape.js knowledge graph with contradiction edges in red, node size by degree, click-to-filter into the fact table. Pruned to a readable subgraph by default with an expand control.

**`src/components/ArtifactPreview.tsx`** — Format-aware preview: rendered images for pptx/docx via `screenshot.py`, an iframe for the HTML infographic, realistic post cards for social, and a shot-list view for the video package. Judges should never have to download a file to see the output.

**`src/components/LayoutFailure.tsx`** ★ — Side-by-side broken vs repaired render with the offending region boxed and a caption naming what was wrong. Milestone M4's payoff lives here; build it as a dedicated component so it's guaranteed to look right on stage.

**`src/components/SecurityBadge.tsx`** — Header badge showing the count of neutralized injection attempts, opening a drawer listing each detection with its source document, page and pattern class. Two-minute demo beat, disproportionate impact with an NTRO panel.

**`src/components/ModelToggle.tsx`** — Sovereign (local GPU) ↔ Fast (cloud) switch showing which model is active and where it runs. Persistent in the header. Makes "air-gapped deployable" something the judges watch you click.

### `infra/`

**`qdrant/`** — Persisted volume for the vector store. Included in `make reset`.

**`models/`** — Local model cache mounted into the container: the LLM weights, bge-m3, the reranker, the NLI model, Whisper, and the Docling models. Gitignored, but **pre-warm this before demo day** — a first-run model download over conference wifi is a lost demo.

**`seed/`** ★ — A complete pre-computed run: source files, the built SoT, all generated outputs, validation reports, rendered artifacts, screenshots and the full event stream. `DEMO_MODE=true` replays it through the same UI at realistic pacing. Test the replay the night before. This is your insurance policy against a dead GPU, a failed conversion or a hostile network, and it costs half a day.

---

# PART 4 — Phases and milestones

Assumes **18 working days** and a **6-person team** (standard SIH team size). A compression path to 10 days is in §4.9.

### Ownership split

| Member | Owns |
|---|---|
| **A** | Ingestion, provenance, OCR/ASR, chunking, quality signals |
| **B** | Retrieval, KG, entity resolution, contradiction detection |
| **C** | SoT builder, normalizer, confidence, lock, diff/versioning |
| **D** | Planner, template contracts, generation, prompts, LLM gateway |
| **E** | Renderers + visual validation + autofix *(hardest track — give this to your strongest engineer)* |
| **F** | Frontend, SSE pipeline view, provenance panel + integration, eval harness, demo |

Fact checker (`validation/`) is co-owned by C and D; C owns grounding, D owns entailment/repair.

---

## Phase 0 — Walking skeleton (Day 0–1)

**Goal: an end-to-end request returns 7 stub artifacts on day 1.** Not one component finished — the *whole loop* wired with stubs. Teams that build components first and integrate last do not finish.

- [ ] Repo, Docker Compose (api + qdrant + web), Makefile, `.env.example`
- [ ] `core/schemas.py` frozen — Fact, Provenance, SourceOfTruth, Claim, ContentPlan, ValidationReport. **Everyone codes against these from day 1.**
- [ ] `core/params.py` — the six operator parameters as enums
- [ ] All 7 template YAMLs written with *placeholder* section lists, `registry.py` loads and validates them
- [ ] `orchestrator/pipeline.py` with all ~10 stages present and stubbed, emitting StageEvents
- [ ] SSE endpoint + a React page that renders the live stage list
- [ ] **GPU environment verified**: cu128 PyTorch, `sm_120` in `torch.cuda.get_arch_list()`, vLLM serving Qwen3-8B, one constrained-JSON call succeeding
- [ ] LiteLLM gateway with both backends reachable and a UI toggle

**Milestone M0:** upload any file → click generate → live stage view runs → 7 dummy files download. Nothing is real. Everything is connected.

## Phase 1 — Ingestion & provenance (Day 2–4) — *owner A*

- [ ] Docling adapter for PDF/DOCX/PPTX/XLSX/HTML/image; `InternalDoc` retains page, bbox, char offsets
- [ ] Scanned-PDF path with OCR confidence per span; low-confidence spans flagged, not silently trusted
- [ ] ASR path: mp3/wav/mp4 → faster-whisper → timestamped segments as provenance locators
- [ ] Video: ffmpeg audio demux + scene-cut keyframes → keyframe OCR merged into the same doc
- [ ] HybridChunker with provenance preserved; assert in tests that **every chunk has ≥1 valid Provenance**
- [ ] Sanitizer + spotlighting run on ingest output before any prompt sees it; detections recorded

**Milestone M1:** upload a scanned PDF and an MP3; UI shows extracted content with page/timestamp locators and OCR confidence heatmap. A planted injection string appears in the security drawer as neutralized.

## Phase 2 — Retrieval, KG, Source of Truth (Day 4–7) — *owners B + C*

- [ ] `retrieval/policy.py` route decision, logged and surfaced in the UI ("Route A — source fits in context")
- [ ] Route B: bge-m3 dense+sparse into Qdrant, RRF fusion, bge-reranker-v2-m3
- [ ] Constrained fact extraction with N-pass self-consistency; `normalizer.py` for numbers/units/currency/percent/dates
- [ ] Triple extraction → NetworkX graph; entity resolution/alias clustering
- [ ] Contradiction detection: same (subject, predicate) → different object; temporal impossibility
- [ ] `depends_on` inference for caveat facts
- [ ] Confidence formula wired; thresholds in config
- [ ] `lock.py` freeze + hash; SoT becomes immutable
- [ ] Truth page: fact table with confidence bars, provenance links, contradiction badges, operator resolve/exclude, LOCK button showing the hash
- [ ] Cytoscape KG panel with contradiction edges in red

**Milestone M2 — the hardest milestone.** Upload the contradictory-report fixture → the contradiction is flagged in the fact table *and* visible as a red edge in the graph → operator resolves it → SoT locks with a hash. If M2 slips more than a day, cut KG scope to entity resolution + contradiction only and drop timeline reasoning.

## Phase 3 — Planner, contracts, generation (Day 6–10) — *owner D*

- [ ] Fill in all 7 template contracts properly, with `parameter_bindings` for detail/audience/language
- [ ] Planner: fact selection per section, budgets, audience sensitivity filtering
- [ ] `coverage.py`: required section with no supporting facts → **GapReport**, and the gap is *shown to the operator*, never filled by invention
- [ ] `gapfill.py`: targeted retrieval before declaring a gap
- [ ] Generation with `structured_outputs` JSON schema — claims with `fact_ids`, never free prose
- [ ] Style/tone/language modifiers composed into prompts
- [ ] Generate-in-target-language for hi + ta

**Milestone M3:** same locked SoT, `detail_level` flipped low→high, and the advisory visibly gains sections. Same SoT, `language=hi`, and a Hindi advisory generates with the same fact IDs.

## Phase 4 — Renderers and visual validation (Day 8–13) — *owner E* — **start this early, it will take longer than you think**

- [ ] All 7 renderers producing real artifacts; every claim carries its `fact_id` into the artifact (pptx shape alt-text, HTML `data-fact-id`, docx comment/bookmark)
- [ ] `predict.py`: PIL/fontTools pre-render fit estimation
- [ ] `html_probe.py`: Playwright overflow/contrast/empty-slot probe — **build this one first, it's exact and fast**
- [ ] `office.py` + `pdf_probe.py`: LibreOffice → PDF → PyMuPDF bbox comparison for pptx/docx
- [ ] `autofix.py`: deterministic repairs (font step-down, bullet split, continuation slide) attempted before any LLM call
- [ ] Failure evidence screenshots surfaced in the UI

**Milestone M4:** force a 400-word bullet into a slide → the validator catches the overflow → autofix splits it across two slides → side-by-side broken/repaired screenshots render in the UI. **This is your strongest single demo moment. Rehearse it.**

## Phase 5 — Fact validation and repair (Day 10–14) — *owners C + D*

- [ ] Citation check against lock hash
- [ ] Grounding check: unsupported number/date/entity detection with character spans
- [ ] Entailment check with mDeBERTa NLI (multilingual, so hi/ta outputs validate too)
- [ ] Dependency check (co-citation of `depends_on` facts)
- [ ] Cross-output: numeric drift, severity inversion, selective omission
- [ ] Repair loop: targeted `RepairInstruction`, max 2 attempts, then review queue with evidence attached
- [ ] Results page: per-output validation report, red-highlighted unsupported tokens, PASS/REPAIRED/REVIEW badges

**Milestone M5:** run with validation disabled → the UI shows N ungrounded tokens highlighted in red. Re-run with validation on → 0 remain, X auto-repaired, Y escalated. This *is* the results slide.

## Phase 6 — Provenance, versioning, security, polish (Day 13–16) — *owner F + all*

- [ ] Provenance panel: click a claim → fact → source snippet with page/bbox highlight overlay on the original
- [ ] Versioning: upload v2 → SoT diff → stale facts marked → only affected outputs queued → prior versions kept auditable
- [ ] Security demo path: injected document → detections badge → confirm no injected instruction reached generation
- [ ] Session isolation demonstrated (two browser sessions, no leakage)
- [ ] Sovereign/Fast model toggle wired end to end
- [ ] *(Optional)* video package → slideshow + TTS render, only if everything else is green

**Milestone M6:** the full happy path runs clean, twice in a row, on the demo machine.

## Phase 7 — Evaluation, hardening, rehearsal (Day 16–18) — *owner F + all*

- [ ] Golden set of 6 sources with hand-labelled facts and planted traps
- [ ] `run_eval.py` + `metrics.py` + `ablations.py` producing the results table
- [ ] `infra/seed/` — a full pre-computed run, replayable in **demo mode** if GPU, network or LibreOffice fails on the day
- [ ] Judge Q&A drilled (§6), demo script timed to 7 minutes, run three times end to end
- [ ] Models pre-downloaded, Docker images pre-built, laptop plugged in, browser cache warm

**Milestone M7:** demo runs cold from `docker compose up` in under 5 minutes, and you have numbers on a slide.

## 4.9 If you only have 10 days

Keep: walking skeleton, ingestion (PDF + image + one audio), Route A only (hard-code Route B as "implemented, demoed on the long fixture" only if it works), SoT + lock + contradiction detection, 4 output formats (advisory, presentation, LinkedIn, executive summary), grounding + entailment checks, HTML **and** pptx visual validation, provenance panel, eval numbers.

Cut: Route B retrieval, video package, infographic, Tamil (keep Hindi), versioning, KG timeline reasoning, autofix beyond font step-down.

**Never cut:** the lock hash, the grounding check, visual validation, the provenance panel, the eval numbers. Those five are the entire differentiation.

---

# PART 5 — The demo script (7 minutes)

Rehearse this until it's muscle memory. Judges remember the demo, not the deck.

| Time | Beat | What they see |
|---|---|---|
| 0:00 | **Frame the problem** | One NTRO report → 7 deliverables, currently hours of manual work with no consistency guarantee |
| 0:30 | **Upload** | A scanned PDF *plus* an audio briefing. Point out OCR confidence and ASR timestamps. "Multimodal isn't a bullet, it's two files." |
| 1:15 | **The Source of Truth** | Fact table with confidence bars. **Point at the contradiction flag.** Resolve it as the operator. Click LOCK. Read the hash out loud. |
| 2:00 | **Security beat** | Open the security drawer: "this uploaded document contained an embedded instruction telling the model to ignore its constraints. It was neutralized at ingest and never reached a prompt." *(For an NTRO panel this lands harder than anything else in the demo.)* |
| 2:30 | **Configure** | Select all 7 formats. Set audience=executive, detail=low, language=English. Generate. |
| 3:00 | **Live pipeline** | SSE stage view running. Narrate the stages while it works — don't stand in silence. |
| 4:00 | **Results + provenance** | Open the advisory. Click a sentence → fact → source page with the exact span highlighted. "Every claim is one click from the source." |
| 4:45 | **The validation beat** | Show a caught failure: an ungrounded number highlighted red, auto-repaired. Then the layout failure: broken slide vs repaired slide, side by side. |
| 5:30 | **Parameters reshape the plan** | Regenerate with detail=high, audience=technical, language=Hindi. Sections appear. Hindi advisory, same fact IDs, same provenance. |
| 6:15 | **Versioning** | Upload v2 of the source. Only the affected outputs queue for regeneration. Prior version still auditable. |
| 6:45 | **Numbers + sovereignty** | Results table: unsupported-claim rate 11.4% → 0%. Flip the model toggle to local. "Everything you just saw runs air-gapped on one GPU." |

**Fallback protocol:** if anything hangs past 10 seconds, say *"switching to the recorded run"* and hit demo mode. Never debug on stage. Have `infra/seed/` tested the night before.

---

# PART 6 — Judge questions, and how to answer them

**"Why not just prompt ChatGPT seven times?"**
Because seven independent prompts produce seven independently hallucinated fact sets with no guarantee they agree, no way to check them, and no way to trace a claim back to a source. We generate from one frozen, hashed fact set, every claim cites fact IDs, and every claim is mechanically verified against those IDs before it renders. Show the lock hash and the red-token highlighting.

**"Your fact checker is an LLM checking an LLM."**
No. Three of our four checks use no LLM at all: citation existence, token grounding by set-difference over normalized values, and dependency co-citation. The fourth is a 180M-parameter NLI cross-encoder, not a generative model. Our hallucination detector cannot itself hallucinate.

**"Why RAG on a 12-page PDF?"**
We don't. Retrieval is a size-triggered route — under the threshold we use the whole source, because context beats retrieval at that scale. Here's the 200-page fixture that triggers Route B. *(Have the fixture ready. This answer only works if you can show it.)*

**"What does the knowledge graph actually do?"**
Three things vector search can't: entity resolution so one entity doesn't become two contradictory facts, temporal ordering so an advisory can't say "patched before disclosure," and structural contradiction detection — same subject and predicate, different object, found deterministically. Show the red edge.

**"What happens when the source doesn't contain what the template needs?"**
The system flags a gap to the operator. It does not invent content. *(Demo this — it's a trust signal most teams can't show.)*

**"How is this deployable at NTRO?"**
Flip the toggle. Local Qwen3 on one 16GB GPU, Docker Compose, no external calls, no fine-tuning, models cached offline. Everything you saw works air-gapped.

**"How do you know it works?"**
Six-document golden set with hand-labelled facts, ablation with validation on and off, and these numbers. *(This is why Phase 7 is not optional.)*

**"What breaks at scale?"**
Honest answer, and say it confidently: single-node, synchronous, one job at a time. The path is a real queue, a worker pool, and a shared vector store — none of which changes a single correctness guarantee, which is what we spent our time proving instead.

---

# PART 7 — Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Blackwell/CUDA environment eats two days | High | Do it on day 0. Verify `sm_120` in `get_arch_list()`. Cloud fallback via the LiteLLM toggle. |
| LibreOffice conversion slow/flaky in Docker | Medium | Timeout-guarded, cached, and `predict.py` catches most overflow without it. HTML probe needs no LibreOffice. |
| Fact extraction quality is mediocre on messy sources | Medium | Self-consistency passes + confidence thresholds + operator review of the fact table *is* the mitigation, and it's also a feature. |
| Team integrates only in the last three days | High | Phase 0 walking skeleton is non-negotiable. Frozen `schemas.py` on day 1. |
| Indic font rendering breaks in pptx/docx | Medium | Ship Noto Sans Devanagari/Tamil in `render/assets/` and install them in the Dockerfile. Test on day 1 of Phase 3, not day 15. |
| Visual validation slips and gets cut | Medium | It's your best differentiator — start it in Phase 4 alongside Phase 3, not after. |
| Demo-day failure | Medium | `infra/seed/` replay mode, tested the night before. |
| Scope creep into rendered video | Low but fatal | Video = structured package. Decided. Written on a slide. |

---

# PART 8 — First three commits

1. `core/schemas.py` + `core/params.py` + all 7 template YAML skeletons + `templates/registry.py` that validates them at startup. Nothing else. Get the team to agree on these types before anyone writes logic.
2. `orchestrator/pipeline.py` with every stage stubbed, `core/events.py` emitting, `api/routes_stream.py` serving SSE, and a React page rendering the live stage list.
3. GPU verification script: cu128 torch, `sm_120` check, vLLM serving Qwen3-8B, one `structured_outputs` call returning schema-valid JSON, LiteLLM routing to both backends.

If those three land in 24 hours, the rest of the plan is achievable.
