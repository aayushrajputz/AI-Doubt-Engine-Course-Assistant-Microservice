# 🚀 LearnTube.ai: 15-Day Production AI Backend Roadmap
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

## 🎬 Phase 2: Video Context-Aware Doubt Engine (Day 11-15)

> **Goal:** Student kisi bhi video ka timestamp de ke pooch sake — "is part mein ye concept samajh nahi aaya" — aur system us specific chapter ka context LLM ko bheje for a laser-focused answer.

### Day 11: Video & Chapter Data Models + Admin CRUD APIs
- **Concepts:** Relational data modeling (1:Many — Video has many Chapters), time-range overlap queries, admin-only endpoints.
- **Implementations:**
  - PostgreSQL Tables:
    1. `videos` — `id`, `title`, `url`, `course_id`, `description`, `duration_seconds`, `created_at`
    2. `video_chapters` — `id`, `video_id` (FK), `title`, `start_time` (seconds), `end_time` (seconds), `summary`, `key_concepts` (text[])
  - Pydantic v2 DTOs: `VideoCreate`, `VideoResponse`, `ChapterCreate`, `ChapterResponse`
  - Admin Router (`/admin/videos/`):
    - `POST /admin/videos/` — Add a new video with metadata
    - `GET /admin/videos/{course_id}` — List all videos for a course
    - `POST /admin/videos/{video_id}/chapters/` — Add chapters with start/end timestamps
    - `GET /admin/videos/{video_id}/chapters/` — List all chapters of a video
    - `PUT /admin/videos/{video_id}/chapters/{chapter_id}` — Update chapter content
    - `DELETE /admin/videos/{video_id}/chapters/{chapter_id}` — Remove a chapter
- **Learntube Incident Prep:** Debugging overlapping chapter time ranges & orphan foreign keys.

---

### Day 12: Smart Timestamp → Chapter Resolver & Local Scope Isolation
- **Concepts:** Time-range binary search, interval detection, 3-tier priority matching, timestamp bucketing for cache hits.
- **Implementations:**
  - `ChapterResolver` service (`app/services/chapter_resolver.py`):
    - **Tier 1 (Exact Match)**: `start_time <= timestamp <= end_time`.
    - **Tier 2 (Fuzzy Buffer ±30s)**: `start_time - 30 <= timestamp <= end_time + 30` (handles border clicks).
    - **Tier 3 (Nearest Distance Fallback)**: `min(abs(start_time - ts), abs(end_time - ts))` (handles gaps between chapters).
    - **Timestamp Bucketing for Cache Keys**:
      - Har second ka alag cache key nahi banta (warna cache hit ratio 0% hoga).
      - Chapter level par bucket: `f"video:{video_id}:chapter:{chapter.id}"`.
      - Unchaptered video par 30s bucket: `f"video:{video_id}:bucket:{timestamp // 30 * 30}"`.
    - Returns structured `ChapterContext` with formatted time strings, summaries, key concepts, and `cache_bucket_key`.

---

### Day 13: Hierarchical Context-Bounded RAG with Cross-Video RRF Fallback & Cost-Gating
- **Concepts:** Two-Tier Retrieval (Local Chapter Window -> Course-Wide RRF Fallback), Reciprocal Rank Fusion, Cross-Referenced LLM Synthesis.
- **Architecture Flow (Local-First, Course-Wide Fallback):**
  - **Tier 1 (Local Chapter Context - Primary)**:
    - Pehle student ke current video aur chapter window se local context verify karo.
    - Agar doubt concept usi chapter ke summary/key-concepts aur local cached answers me directly mil jata hai -> **Zero LLM Token Cost (₹0.00)**.
  - **Tier 2 (Course-Wide RRF Fallback - Scope Expansion)**:
    - Agar concept current video ke bahar kisi aur lecture me explain kiya gaya hai (e.g., current lecture React ka hai par foundational concept JavaScript Closures video me tha):
    - Trigger **Hybrid RRF (pgvector Cosine Distance + Full-Text Keyword Search)** across all `course_chunks`.
    - Retrieve cross-video references with their respective `video_id` and timestamp offsets.
  - **Tier 3 (Cross-Referenced Synthesis)**:
    - LLM prompt dynamically combines:
      1. *Current Context*: "Student is watching Video X at timestamp Y"
      2. *Reference Context*: "Foundational concept explained in Video Z at offset W"
    - Student gets an exact answer + reference recommendation to the other video without hallucinations!
  - Extend `doubts` table with `video_id` (FK) and `timestamp` (integer seconds).
  - Update `doubt_router.py` streaming SSE engine with Hierarchical Context-Bounded + RRF Fallback injection.

---

### Day 14: Video Doubt Integration Testing + Edge Cases [COMPLETED]
- **Concepts:** Integration test patterns, edge case handling, error recovery, API contract testing.
- **Implementations:**
  - Automated Chaos Test Suite (`test_day_14_chaos_edge_cases.py`):
    1. **Invalid Video ID**: Returns clean HTTP 404 without database foreign key violation (Zero 500 crash).
    2. **Orphan Timestamp**: Pydantic `@model_validator` rejects timestamp without video_id with HTTP 422.
    3. **Zero-Chapter Video Fallback**: 30s bucket fallback handles videos with 0 chapters gracefully.
    4. **Gap Timestamp Match**: Nearest Euclidean/Absolute distance resolves timestamps falling in gaps.
    5. **Cache Isolation**: Cross-video cache collision prevented via video-scoped cache keys.

---

### Day 15: Bulk Chapter Import + Video Doubt Analytics [COMPLETED]
- **Concepts:** Bulk database operations, overlapping interval validation, SQL group-by aggregations.
- **Implementations:**
  - Bulk Chapter Import API (`POST /admin/videos/{video_id}/chapters/bulk`):
    - Multi-chapter JSON upload with automated start_time chronological sorting.
    - Overlapping interval rejection with HTTP 400 Bad Request.
  - Video Doubt Hotspots Analytics API (`GET /admin/videos/{video_id}/hotspots`):
    - PostgreSQL SQL Aggregation (`LEFT OUTER JOIN doubts ON timestamp BETWEEN start_time AND end_time GROUP BY chapter_id`).
    - Chapters ranked by difficulty/doubt count to pinpoint exact lecture segments needing instructor attention.

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
| Containerization | **Docker** + **Docker Compose** (Multi-service) |

