# 🚀 LearnTube.ai: 10-Day Production AI Backend Roadmap
**Role Target:** AI Backend Engineer (LearnTube.ai)  
**Compensation Benchmark:** ₹1.2M - ₹2.5M INR/yr  
**Interview Format:** Timed Incident Simulation & Live Debugging on Production Systems  

---

## 🏛️ System Architecture Blueprint

```
                            Learner Request (Doubt / Question)
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────────┐
                    │               FastAPI Gateway                     │
                    │   - Pydantic v2 Strict DTOs                       │
                    │   - Redis Hot Path (Rate Limiting & Semantic Cache)│
                    └───────────────────────┬───────────────────────────┘
                                            │ (Cache Miss)
                                            ▼
                    ┌───────────────────────────────────────────────────┐
                    │       LangGraph Multi-Step StateGraph             │
                    │   1. Intent Classifier / Guardrail Node           │
                    │   2. Course Retriever Node (pgvector HNSW)        │
                    │   3. Synthesis & Reasoning Node (LLM)             │
                    │   4. Fallback / Human-in-loop Escalation Node     │
                    └───────────────────────┬───────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────────┐
                    │                                                   │
                    ▼                                                   ▼
     ┌─────────────────────────────┐                     ┌─────────────────────────────┐
     │  PostgreSQL + pgvector      │                     │  SSE Token Stream Engine    │
     │  - Course Chunk Embeddings  │                     │  - TTFT < 200ms Target      │
     │  - HNSW Index (`<=>` Cosine)│                     │  - Client Disconnect Catch  │
     └─────────────────────────────┘                     └──────────────┬──────────────┘
                                                                        │
                                                                        ▼
                                                         ┌─────────────────────────────┐
                                                         │ Async Background Tasks      │
                                                         │ - Tiktoken Usage Accounting │
                                                         │ - Mongo Log (Learner History│
                                                         │ - Redis Cache Warming       │
                                                         └─────────────────────────────┘
```

---

## 📅 The 10-Day Production Master Plan

### Day 1: Foundation, Async Lifespan & Hot-Path Architecture
- **Concepts:** ASGI Lifespan (`@asynccontextmanager`), non-blocking event loop ergonomics, connection pooling vs global socket hazards.
- **Implementations:**
  - FastAPI app lifecycle initializing:
    1. Async SQLAlchemy (Engine + Pool with timeout & pre-ping)
    2. Motor/AsyncIOMotorClient (MongoDB Async driver)
    3. Redis connection pool (`redis.asyncio`)
  - Clean shutdown hooks ensuring 0 socket leaks on `SIGTERM`.
- **Learntube Incident Prep:** Debugging connection pool exhaustion & event loop blocking bugs.

---

### Day 2: Pydantic v2 Validation & Layered Architecture
- **Concepts:** Rust core validation speed, DTO vs ORM separation, custom validators, nested schemas.
- **Implementations:**
  - Schemas for Doubts, Course Contexts, Token Usages, and Streaming chunks.
  - Field validators: Whitespace sanitization, SQL-injection characters filter, model config `from_attributes=True`.
  - Clean Dependency Injection (`Depends(get_db)`, `Depends(get_redis)`).

---

### Day 3: PostgreSQL + pgvector Vector Search Engine
- **Concepts:** Dense Embeddings, Vector Index types (IVFFlat vs HNSW), Distance Operators (`<=>` Cosine Distance, `<#>` Negative Inner Product, `<->` L2 Distance).
- **Implementations:**
  - Enable `vector` extension on Postgres.
  - SQLAlchemy model with `Vector(1536)` (or 768 for open-source embeddings).
  - Create **HNSW Index** (`m=16, ef_construction=64`) for ultra-low latency sub-millisecond retrieval.
  - Repository function running raw hybrid cosine distance queries:
    ```sql
    SELECT id, content, 1 - (embedding <=> :query_vector) AS similarity 
    FROM course_chunks 
    WHERE course_id = :course_id 
    ORDER BY embedding <=> :query_vector 
    LIMIT 5;
    ```
- **Learntube Incident Prep:** Diagnosing sequential table scans vs index utilization via `EXPLAIN ANALYZE`.

---

### Day 4: Hybrid RAG Pipeline & Context Assembly
- **Concepts:** Chunking strategies for educational transcripts, Reciprocal Rank Fusion (RRF) combining Full-Text Keyword Search + Vector Similarity.
- **Implementations:**
  - RAG Service:
    1. Text chunking with metadata (timestamp, video offset, course module).
    2. Vector embedding generator (OpenAI / Local embedding pipeline).
    3. Hybrid retrieval service returning high-relevance course context snippets.

---

### Day 5: LangGraph Multi-Agent Workflow (The AI Core)
- **Concepts:** Cyclic Graphs, State Management (`TypedDict`), Conditional Edge Routing, Tool Integration (MCP-ready).
- **Implementations:**
  - Build LangGraph `StateGraph`:
    - **Node 1: Guardrail & Filter Node** (Refuse off-topic questions, e.g., crypto/politics).
    - **Node 2: Retrieval Node** (Invokes pgvector HNSW query).
    - **Node 3: Evaluation Node** (Did retrieval find relevant course material? If not -> Web/Fallback tool).
    - **Node 4: Tutor Answer Node** (Pedagogical prompt with structured reasoning).
  - Compile graph into runnable pipeline.

---

### Day 6: Real-Time SSE Token Streaming & TTFT Optimization
- **Concepts:** Server-Sent Events (SSE), HTTP/2 Chunked Transfer, Time-To-First-Token (TTFT), handling client disconnects.
- **Implementations:**
  - FastAPI `StreamingResponse` wrapping an async generator.
  - Integrating LangGraph's `.astream_events()` for token-by-token emission.
  - Client disconnect detection via `request.is_disconnected()` to immediately cancel upstream LLM tokens and save money.

---

### Day 7: Economic Guardrails: Tiktoken Accounting & Budgeting
- **Concepts:** LLM economics, tokenization mechanics (BPE - Byte Pair Encoding), cost per 1k input/output tokens.
- **Implementations:**
  - Accurate token counting using `tiktoken` (e.g., `cl100k_base` / `o200k_base`).
  - Strict budget enforcement middleware: If user token consumption exceeds hourly quota, reject with `429 Too Many Requests`.
  - Background Task recording prompt tokens, completion tokens, and dollar cost into MongoDB.

---

### Day 8: MongoDB Primary Audit & Redis Hot Path Cache
- **Concepts:** Hot path vs Cold path, Semantic Caching, TTL strategies, write-behind logging.
- **Implementations:**
  - Redis Hot Path:
    - Exact query cache + Semantic similarity cache (if same doubt asked in last 1 hour, return cached answer instantly).
    - Rate-limiting (Sliding window token bucket).
  - MongoDB Primary Store:
    - Complete unedited conversation sessions, tool invocations, and agent state checkpoints stored asynchronously via `FastAPI.BackgroundTasks`.

---

### Day 9: Monitoring, Tracing & Production Dockerization
- **Concepts:** OpenTelemetry, Prometheus metrics, structured JSON logging, multi-stage Docker builds.
- **Implementations:**
  - Structured logs with correlation IDs (`request_id`).
  - Production `Dockerfile` (distroless/slim, non-root user, proper Uvicorn worker threads).
  - Health check probes (`/live` and `/ready`) with DB & Redis ping tests.

---

### Day 10: LearnTube.ai "Incident Simulation" Battle Test
- **The Crucible (Interview Dress Rehearsal):**
  - Simulating 4 real production breakages on our repo:
    1. **Incident 1:** Massive TTFT spike (Diagnosing unindexed vector search vs LLM socket hang).
    2. **Incident 2:** Silent event loop freeze caused by blocking sync function in an async route.
    3. **Incident 3:** Memory leak from zombie Redis connections under high concurrent load.
    4. **Incident 4:** LLM API billing runaway from infinite agent cycles in LangGraph.
  - Hands-on debugging using logs, execution plans, and fast mitigation!

---

## 🛠️ Tech Stack Locked
| Component | Technology |
|---|---|
| Framework | **FastAPI** (Python 3.11+, 100% Async) |
| Relational & Vector DB | **PostgreSQL 16 + pgvector** (HNSW Indexing) |
| Document / Audit DB | **MongoDB** (Async Motor driver) |
| Cache & Hot Path | **Redis 7** (Asyncio) |
| Orchestration | **LangGraph** (StateGraph) |
| Token / Cost Engine | **Tiktoken** + Async Background Tasks |
| Streaming | **SSE (Server-Sent Events)** with StreamingResponse |
