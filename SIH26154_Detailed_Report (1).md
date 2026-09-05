# SIH26154 — Gen AI Platform for Automated Content Transformation
## Detailed Solution Report

---

## 1. Problem Statement

**PS ID:** SIH26154 | **Organization:** NTRO | **Category:** Software — Smart Automation

NTRO needs a platform where an operator submits source content — English-language text, documents, reports, prompts, images, video, or general contextual material — and selects one or more required output formats from a fixed set: **Video package, LinkedIn post, Twitter/X post, Advisory, Infographic, Executive summary, Presentation.** The operator also configures generation parameters: **audience, tone, language, level of detail, communication objective, and content style.** The platform must understand the source and produce every selected deliverable from it, consistently, in a single operator-driven session — not as a search tool over an archive, and with no dataset or knowledge-graph requirement stated in the brief.

**What is mandatory:** multi-format generation from one source, operator-controlled parameters, a working dashboard.
**What is explicitly NOT required:** corpus-scale retrieval, multi-document reasoning, actual rendered video (a structured script/storyboard package satisfies the "video" output), fine-tuned models.

---

## 2. Our Idea — Solution Overview

**Core principle:** one locked, verified source of truth → many outputs, each governed by a template contract, each generated under retrieval-augmented and knowledge-graph-grounded constraints, each validated twice — for factual accuracy and for visual/layout correctness — before it ever reaches the operator.

The system is not "upload a PDF, prompt an LLM per format." It is a pipeline where:
1. The source is understood multimodally (OCR for scans/images, ASR for audio/video, NLP for text) and normalized into chunks.
2. A **RAG + Knowledge Graph** layer builds an embedding index and an entity-relationship graph from those chunks, and uses hybrid retrieval (semantic + keyword + reranking) to surface the most relevant, best-supported evidence for whatever is being generated.
3. That evidence is distilled into a **Verified Source of Truth** — a schema-validated set of facts, entities, numbers, timelines, and claims, each with a confidence score, a contradiction flag if sources disagree, and a provenance pointer back to its exact location in the source.
4. An **Output Planner** turns the operator's format selection and parameters (audience/tone/language/detail/objective/style) into a concrete content plan per output — what facts to include, how much detail, in what structure.
5. A **Template Engine** enforces two contracts per output type: a **Content Contract** (required vs. optional fields, how much content is allowed) and a **Layout Contract** (structure, placement, length limits, rendering rules).
6. **LLM Generation** fills each plan, constrained to only reference the locked Source of Truth — never re-deriving or re-researching independently per format, which is what keeps every output consistent with every other output.
7. A **Fact Consistency Checker** — deterministic entity/number/quote diffing against the Source of Truth, plus a cross-output contradiction check — runs before rendering. Failures are regenerated or routed to a human reviewer, never silently published.
8. A **Template Renderer** produces the actual artefact (slides, document, infographic layout, social post text, video script package) in format-correct form.
9. A **Visual Validator** checks the rendered artefact for overflow, clipping, missing required fields, broken layout, empty sections, or unreadable text.
10. The **Final Artefact** ships with a provenance panel — every claim is clickable back to the exact source sentence it came from.

---

## 3. Complete Workflow

```
OPERATOR DASHBOARD (source + output selection + audience/tone/language/detail)
        │
        ▼
MULTIMODAL SOURCE  →  UNDERSTANDING LAYER  →  OCR / ASR / NLP  →  normalized, chunked content
        │
        ▼
RAG + KNOWLEDGE GRAPH
   embedding index  +  entity/relation extraction (KG)  +  hybrid retrieval (semantic + keyword + reranker)
   → contextual / parent-child retrieval + query decomposition
        │
        ▼
VERIFIED SOURCE OF TRUTH
   facts, entities, numbers, timeline  +  confidence scoring + contradiction detection  +  provenance map
        │
        ▼
OUTPUT PLANNER  (per output type × operator parameters, queries RAG/KG for anything missing)
        │
        ▼
TEMPLATE ENGINE  →  Content Contract  +  Layout Contract
        │
        ▼
LLM GENERATION  (one call per output, constrained strictly to the Source of Truth)
        │
        ▼
FACT CONSISTENCY CHECKER
   entity/number/quote diff  +  cross-output contradiction check
   PASS → continue        FAIL → regenerate / flag for human review
        │
        ▼
TEMPLATE RENDERER  (python-pptx / docx / HTML-infographic / plain social text / video script package)
        │
        ▼
VISUAL VALIDATOR  (overflow, clipping, missing fields, broken layout, empty sections)
   PASS → publish          FAIL → re-render / flag for review
        │
        ▼
FINAL ARTEFACT + provenance panel (claim → fact → source span)

Cross-cutting across every layer: security (prompt-injection filtering, session isolation, optional
on-prem deployment), versioning (source update → stale-fact detection → regeneration queue → audit
trail of prior versions), human-in-the-loop review queue for any FAIL state.
```

---

## 4. Key Innovations

1. **Template-as-schema, not template-as-skin.** Templates don't just format the answer — they define what information a Presentation, Advisory, or Infographic structurally *requires*, feeding that requirement back into retrieval and planning.
2. **Locked Source of Truth shared across all outputs.** Every format is generated from the same frozen fact set, so a Twitter post and an Advisory can never silently contradict each other — consistency is structural, not hoped for.
3. **RAG + Knowledge Graph grounding.** Hybrid retrieval (semantic + keyword + reranking) surfaces the best-supported evidence; the knowledge graph captures entity relationships and timelines that pure vector search misses, and flags contradictions across the source.
4. **Claim-to-source provenance.** Every generated statement is traceable — claim → fact → source page/section/chunk — clickable in the final artefact, not asserted on trust.
5. **Two-tier validation, deterministic-first.** Fact checking is entity/number/quote diffing against the Source of Truth (cheap, explainable, catches most errors), backed by a light LLM-judge pass for tone/coherence — not "LLM-as-judge" alone.
6. **Deterministic visual/layout validation.** Overflow, clipping, empty required fields, and broken layout are caught automatically before an operator ever sees a broken deck.
7. **Operator parameters reshape the plan, not just the wording.** Audience/tone/detail change what content is selected and how much, matching exactly what the PS asks operators to control.

---

## 5. Edge Cases Covered

| Edge case | How the system handles it |
|---|---|
| Source has conflicting facts across sections | Contradiction detection flags it in the Source of Truth; conflicting claims are marked low-confidence and excluded from generation unless the operator resolves them |
| LLM hallucinates a number, name, or date | Fact Consistency Checker diffs every generated claim against the locked Source of Truth; mismatches trigger regeneration or a review flag, never silent publish |
| Two outputs (e.g. Advisory and LinkedIn post) would otherwise disagree | Cross-output contradiction check runs before rendering, since both derive from the same locked facts to begin with |
| Scanned document or low-quality image input | OCR layer in the Understanding stage extracts text before chunking; low-confidence OCR spans are flagged rather than silently trusted |
| Audio/video source | ASR transcribes and diarizes before the same NLP/RAG pipeline processes it identically to text |
| Required template field has no supporting evidence in the source | Content Contract marks it required-but-unavailable; system flags the gap to the operator rather than inventing content to fill it |
| Generated Presentation text overflows its slide | Visual Validator measures rendered text against layout limits and flags/re-renders before publish |
| Source is updated after outputs were already generated | Versioning layer diffs V1 vs V2, detects which facts and embeddings are stale, and queues only the affected outputs for regeneration, keeping prior versions auditable |
| Malicious or prompt-injected content embedded in an uploaded document | Ingested content is sanitized before it reaches any system prompt, preventing indirect prompt injection |
| Multiple operators using the platform concurrently | Per-session isolation prevents one operator's source data or generated content from leaking into another's session |
| Ambiguous or low-confidence extracted facts | Confidence scoring surfaces this in the Source of Truth; low-confidence claims are either excluded from generation or explicitly caveated |
| Multilingual output requirement | Language is a first-class operator parameter feeding both the content plan and generation step, not a post-hoc translation pass |

---

## 6. Pros / Advantages

- Single source, many consistent outputs — no manual reformatting per channel
- Every claim is provably grounded and traceable, not just plausible-sounding
- Broken or incomplete outputs are caught automatically, before they reach the operator
- Operator-level control over audience, tone, language, detail, and objective — genuinely changes content structure, not just phrasing
- Cheaper and faster than a human team manually producing seven different deliverables from one report
- Deterministic-first validation keeps the system explainable to a non-technical operator, not a black box

---

## 7. Impact

- Cuts the time from "raw intelligence/report" to "ready-to-distribute deliverable across seven formats" from hours of manual drafting to a single operator session
- Reduces the risk of inconsistent public/internal messaging, since every output is fact-locked to one verified source
- Frees analysts and communications staff from repetitive reformatting work to focus on judgment calls and review
- Improves traceability and auditability of generated content — critical where the source material may be sensitive or high-stakes (advisories, intelligence summaries)

---

## 8. Benefits

- **For operators:** one upload, one set of parameters, multiple ready-to-use deliverables with a visible provenance trail
- **For reviewers:** clear PASS/FAIL flags on both factual grounding and visual correctness, so review effort concentrates only where it's needed
- **For the organization:** consistent voice and facts across every channel a piece of content reaches, plus an audit trail if a source is later revised
- **For future scale:** template registry and Source-of-Truth schema are reusable across new output types without re-architecting the pipeline

---

## 9. Feasibility

- Every component maps to mature, available technology: LLM APIs for extraction/planning/generation, a vector store for retrieval, a lightweight graph structure for entities/relationships, python-pptx/python-docx/HTML-to-image for rendering, and standard NLP libraries for deterministic fact-checking
- No model fine-tuning is required — RAG plus structured knowledge plus controlled prompting plus validation is sufficient
- MVP scope (four to five output types fully working, two languages, core validation loop) is realistic within a hackathon build window
- Architecture is modular — ingestion, understanding, retrieval, planning, generation, and validation are independently buildable and testable by separate team members in parallel

---

## 10. Viability

- Directly addresses NTRO's stated requirement without over-committing.
- Clear extension path for production: on-prem/local model deployment for sensitive data, full version-management for evolving sources, human-approval workflows for high-stakes publishing — all designed into the architecture as add-on layers rather than retrofits
- Differentiates defensibly from a simple LLM-prompt wrapper because cross-output consistency, provenance, and validation are structural guarantees, not one-off prompt quality — a genuine, demonstrable answer to "why not just ask ChatGPT"
- Cost of operation scales with API calls per job, not infrastructure, keeping ongoing viability straightforward to reason about
