# AutoResearch — Architecture Document

## Overview

AutoResearch is an autonomous AI research and reporting agent. Given a topic or
query, the system dispatches an agent that searches the web, retrieves and
synthesises information, stores knowledge in a vector store, and produces a
structured markdown report — all accessible via a REST API with a lightweight
dashboard.

---

## High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                  │
│  Dashboard (HTML/JS)          REST Clients           CI / Cron triggers  │
└───────────────┬───────────────────────┬────────────────────┬────────────┘
                │                       │                    │
                ▼                       ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API LAYER  (FastAPI)                            │
│  POST /research        GET /reports/{id}       GET /health              │
│  GET  /reports         DELETE /reports/{id}    GET /metrics             │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│  SCHEDULER      │  │  ORCHESTRATOR    │  │  PERSISTENCE LAYER  │
│  (APScheduler)  │  │  (Supervisor     │  │  SQLite (SQLAlchemy) │
│                 │  │   Agent)         │  │  ChromaDB           │
│  Cron jobs      │  │                  │  │  (vector store)     │
│  Retry/backoff  │  │  Manages agents  │  │                     │
└─────────────────┘  │  + tool calls    │  └─────────────────────┘
                     └────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  RESEARCHER     │  │  SUMMARISER  │  │  REPORT WRITER   │
│  AGENT          │  │  AGENT       │  │  AGENT           │
│                 │  │              │  │                  │
│  Web search     │  │  Chunking +  │  │  Structured      │
│  Scraping       │  │  RAG query   │  │  markdown output │
│  Source eval    │  │  synthesis   │  │  + citations     │
└────────┬────────┘  └──────┬───────┘  └─────────┬────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           TOOL LAYER                                     │
│  web_search  │  web_scraper  │  embed  │  vector_query  │  llm_call     │
└─────────────────────────────────────────────────────────────────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL SERVICES                                  │
│  Anthropic Claude API     SerpAPI / DuckDuckGo     (future: OpenAI)     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. API Layer (`/api`)
Built with **FastAPI**.  Every operation is async.  Endpoints accept a research
topic and return a `job_id`; results are fetched separately (async job model).

| Endpoint                  | Method | Description                         |
|---------------------------|--------|-------------------------------------|
| `/health`                 | GET    | Liveness probe                      |
| `/research`               | POST   | Submit a new research job           |
| `/reports`                | GET    | List all completed reports          |
| `/reports/{id}`           | GET    | Fetch a single report               |
| `/reports/{id}`           | DELETE | Delete a report                     |
| `/metrics`                | GET    | Prometheus-style text metrics       |

### 2. Orchestrator / Supervisor Agent (`/agents/orchestrator.py`)
The central coordinator.  Receives a job from the API, breaks it into sub-tasks,
and sequentially (or in parallel, Phase 5+) invokes specialist agents.

### 3. Researcher Agent (`/agents/researcher.py`)
Uses the **web_search** and **web_scraper** tools.  Produces a list of raw
source documents with metadata (URL, title, snippet, fetch timestamp).

### 4. Summariser Agent (`/agents/summariser.py`)
Chunks raw documents, embeds them into **ChromaDB**, then runs a RAG query to
retrieve the most relevant passages before calling the LLM for synthesis.

### 5. Report Writer Agent (`/agents/report_writer.py`)
Takes the synthesis and formats a structured markdown report with:
- Executive summary
- Key findings (bullet-pointed)
- Source list with links
- Confidence / limitation notes

### 6. Tool Layer (`/tools`)
Each tool is a plain Python callable with a typed `ToolInput` / `ToolOutput`
schema (Pydantic).  The LLM provider calls them via function-calling / tool-use.

| Tool             | Description                                              |
|------------------|----------------------------------------------------------|
| `web_search`     | DuckDuckGo search (no API key needed); swappable to SerpAPI |
| `web_scraper`    | HTTP fetch + BeautifulSoup text extraction               |
| `embed`          | Call embedding model, return vector                      |
| `vector_query`   | Query ChromaDB collection, return top-k chunks           |
| `llm_call`       | Thin wrapper around the LLM provider interface           |

### 7. RAG Layer (`/rag`)
- `embedder.py` — wraps sentence-transformers (local) or OpenAI embeddings
- `vector_store.py` — ChromaDB client; handles collection CRUD + upsert/query
- `chunker.py` — splits documents into overlapping chunks with metadata

### 8. Scheduler (`/scheduler`)
**APScheduler** with a SQLite job store.  Supports:
- Periodic re-research (keep reports fresh)
- Retry logic for failed jobs (exponential back-off)

### 9. Persistence Layer (`/config/database.py`)
**SQLAlchemy** ORM targeting SQLite by default; swap `DATABASE_URL` to a Postgres
DSN for production.  Tables: `jobs`, `reports`, `sources`.

### 10. Dashboard (`/dashboard`)
A single-page `index.html` with vanilla JS.  Served as static files by FastAPI.
Shows job list, report viewer, and a "Submit Research" form.

### 11. Observability
- Structured JSON logging via `structlog`
- `/metrics` endpoint exposes job counts, latencies, error rates
- Eval harness in `/tests/evals/` — checks report quality against golden answers

---

## Data Flow — Happy Path

```
User submits POST /research {"topic": "quantum computing 2025"}
  └─► API creates Job(id=uuid, status=PENDING) in SQLite
  └─► API enqueues job → Orchestrator
        └─► Researcher Agent
              └─► web_search("quantum computing 2025")  → 10 results
              └─► web_scraper(url) × 10               → raw docs
        └─► Summariser Agent
              └─► chunker → ChromaDB upsert
              └─► vector_query("quantum computing 2025") → top-k chunks
              └─► LLM synthesise(chunks)               → synthesis text
        └─► Report Writer Agent
              └─► LLM format_report(synthesis)          → markdown
        └─► API updates Job(status=COMPLETE), stores Report in SQLite
User fetches GET /reports/{id} → receives markdown report + metadata
```

---

## LLM Provider Abstraction

All LLM calls go through `tools/llm_provider.py`:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[Message], tools: list[Tool] | None) -> LLMResponse: ...
```

`AnthropicProvider` implements this today.  Adding `OpenAIProvider` later requires
only a new class — zero changes to agents.

---

## Phase Roadmap

| Phase | What Gets Built                                       |
|-------|-------------------------------------------------------|
| 1     | Repo scaffold, architecture doc, FastAPI skeleton     |
| 2     | LLM provider abstraction + tool layer                 |
| 3     | Researcher + Summariser agents, RAG pipeline          |
| 4     | Report Writer agent, SQLite persistence, job model    |
| 5     | Scheduler (APScheduler), periodic re-research         |
| 6     | Dashboard (HTML/JS), static serving                   |
| 7     | Observability: structlog, /metrics, eval harness      |
| 8     | Docker + docker-compose, GitHub Actions CI            |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async everywhere | `asyncio` + FastAPI | Fits I/O-heavy agent workloads |
| SQLite default | SQLAlchemy abstraction | Zero-friction local dev; Postgres for prod |
| Local embeddings | sentence-transformers | No extra API cost; swappable |
| Tool schemas (Pydantic) | Pydantic v2 | Type safety + auto-docs |
| Report format | Markdown | Renderable in dashboard; Git-friendly |
