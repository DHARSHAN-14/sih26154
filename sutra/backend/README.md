# Sutra Backend

**SIH26154 — Gen AI Platform for Automated Content Transformation**

> One locked, verified source of truth → many consistent, validated output formats.

---

## Architecture

```
Source Upload
    │
    ▼
Multimodal Understanding  (OCR / ASR / NLP via Docling)
    │
    ▼
RAG + Knowledge Graph     (Route A: full-context | Route B: hybrid search + rerank)
    │
    ▼
Verified Source of Truth  (facts + confidence + provenance + lock hash)
    │
    ▼
Output Planner            (per format × operator parameters)
    │
    ▼
Template Engine           (Content Contract + Layout Contract per YAML)
    │
    ▼
LLM Generation            (constrained to locked SoT, structured JSON output)
    │
    ▼
Fact Consistency Checker  (deterministic entity/number diffing + NLI entailment)
    │
    ▼
Template Renderer         (python-pptx / python-docx / HTML / social text / video pkg)
    │
    ▼
Visual Validator          (overflow, clipping, empty sections — pre-publish)
    │
    ▼
Final Artifact + Provenance Panel
```

**Output formats:** Advisory · Executive Summary · Presentation · LinkedIn · Twitter/X · Infographic · Video Package

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ running locally (or via Docker)
- (Optional) Qdrant for vector search (Route B)

---

## Quick Start

```bash
# 1. Clone and enter the backend directory
cd backend

# 2. Create a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate           # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env             # Windows
# cp .env.example .env             # macOS / Linux
# Edit .env — set DATABASE_URL, API keys, etc.

# 5. Run the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **Docs (Swagger):** http://localhost:8000/docs
- **Docs (ReDoc):**   http://localhost:8000/redoc
- **Health:**         http://localhost:8000/api/health
- **Readiness:**      http://localhost:8000/api/health/ready

---

## API Endpoints (Phase 0)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info and links |
| `GET` | `/api/health` | Liveness — returns 200 if process is alive |
| `GET` | `/api/health/ready` | Readiness — checks DB + dependencies |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  ← FastAPI app, middleware, lifespan
│   ├── config.py                ← Pydantic Settings (all env vars)
│   ├── deps.py                  ← FastAPI dependency providers
│   ├── api/
│   │   └── health.py            ← GET /api/health + /ready
│   ├── core/
│   │   ├── errors.py            ← Typed exceptions + global handlers
│   │   ├── logging.py           ← structlog configuration
│   │   └── ids.py               ← Stable ID generators (F-001, etc.)
│   ├── db/
│   │   ├── base.py              ← DeclarativeBase, TimestampMixin, SessionMixin
│   │   └── session.py           ← Async engine, session factory, init_db()
│   ├── models/                  ← SQLAlchemy ORM models (Phase 1+)
│   ├── schemas/                 ← Pydantic request/response schemas (Phase 1+)
│   ├── services/                ← Business logic services (Phase 1+)
│   ├── document_processing/     ← Docling adapter, OCR, ASR (Phase 2+)
│   ├── rag/                     ← Embeddings, vector store, hybrid search (Phase 2+)
│   ├── knowledge_graph/         ← NetworkX KG, contradiction detection (Phase 3+)
│   ├── llm/                     ← LiteLLM gateway, constrained decoding (Phase 3+)
│   ├── templates/               ← YAML contract registry (Phase 3+)
│   ├── outputs/                 ← Renderers: pptx, docx, html, social (Phase 4+)
│   ├── validation/              ← Citation, grounding, entailment, repair (Phase 4+)
│   ├── security/                ← Sanitizer, spotlight, isolation (Phase 1+)
│   └── utils/                   ← Shared utilities
├── tests/
│   └── test_health.py
├── data/
│   └── artifacts/               ← Generated output artifacts (gitignored)
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

---

## Running Tests

```bash
# Activate venv first, then:
pytest tests/ -v
```

Tests are designed to pass even without a running PostgreSQL instance.
`/api/health/ready` will return 503 (degraded) in that case — which is the
expected and tested behaviour.

---

## Environment Variables

See [`.env.example`](.env.example) for all supported variables with comments.

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://sutra:sutra@localhost:5432/sutra_db` | Async Postgres URL |
| `MODEL_BACKEND` | `fast` | `sovereign` (local) or `fast` (cloud API) |
| `RETRIEVAL_TOKEN_THRESHOLD` | `25000` | Route A/B decision boundary |
| `DEBUG` | `true` | Enable debug mode + console logging |
| `LOG_FORMAT` | `console` | `console` (dev) or `json` (production) |

---

## Configuration Philosophy

Every tunable number lives in `config.py` / `.env` — never hard-coded in business logic.
If a judge asks *"why 0.7 for the entailment threshold?"*, the answer is a pointer to `.env`, not a shrug.
