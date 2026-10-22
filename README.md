# 🧠 AI Doubt Engine — Course Assistant Microservice

> **Production-grade AI-powered doubt resolution engine** built for EdTech platforms. Combines LangGraph multi-agent orchestration, pgvector semantic search, and 3-tier intelligent caching to deliver instant, context-aware answers at near-zero LLM cost.

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15_+_pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7_Alpine-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi_Agent-FF6F00)](https://langchain-ai.github.io/langgraph/)

---

## 🏗️ Architecture

```
                         Learner Request (Doubt / Question)
                                         │
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │            FastAPI Gateway (ASGI)            │
                 │     Pydantic v2 DTOs + Dependency Injection  │
                 └──────────────────┬──────────────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │  1. Redis Exact   │  │ 2. Postgres HNSW │  │  3. LLM Inference│
    │  Cache  (~2ms)    │  │ Semantic Cache   │  │  (Groq API)      │
    │  TTL: 24h         │  │ (~93ms, ≥85%)    │  │  SSE Streaming   │
    │  Cost: ₹0.00      │  │ Cost: ₹0.00      │  │  Cost: ~₹0.04    │
    └──────────────────┘  └──────────────────┘  └────────┬─────────┘
                                                         │
                                                         ▼
                                         ┌───────────────────────────┐
                                         │   LangGraph StateGraph     │
                                         │  ┌─────────────────────┐  │
                                         │  │ Guardrail Node      │  │
                                         │  │ (Prompt Injection    │  │
                                         │  │  & Jailbreak Guard)  │  │
                                         │  └──────────┬──────────┘  │
                                         │             ▼             │
                                         │  ┌─────────────────────┐  │
                                         │  │ Retriever Node      │  │
                                         │  │ (RRF Hybrid Search: │  │
                                         │  │  Vector + Keyword)   │  │
                                         │  └──────────┬──────────┘  │
                                         │             ▼             │
                                         │  ┌─────────────────────┐  │
                                         │  │ Tutor Node (LLM)    │  │
                                         │  │ Token-by-Token SSE   │  │
                                         │  └─────────────────────┘  │
                                         └───────────────────────────┘
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **3-Tier Intelligent Caching** | Redis exact match → pgvector semantic similarity (≥85%) → LLM fallback. Eliminates redundant API calls. |
| **LangGraph Multi-Agent Pipeline** | Guardrail → Retriever → Tutor nodes with conditional routing and state management. |
| **Hybrid Search (RRF)** | Reciprocal Rank Fusion combining pgvector cosine similarity + keyword ILIKE search for maximum recall. |
| **HNSW Vector Indexing** | Sub-100ms approximate nearest neighbor search on 768-dim embeddings (`m=16, ef_construction=64`). |
| **Real-Time SSE Streaming** | Token-by-token answer streaming via `StreamingResponse` with TTFT optimization. |
| **Prompt Injection Guard** | Regex-based sanitizer blocks jailbreak attempts and off-topic prompt injections. |
| **Cost Tracking** | Per-request token counting with INR/USD cost calculation reported in stream metrics. |
| **Embedding-on-Ingest** | Every doubt is embedded at creation time for future semantic matching. |

---

## 📁 Project Structure

```
app/
├── server.py                    # FastAPI app, lifespan (DB + Redis init), health check
├── core/
│   └── database.py              # AsyncEngine, async_sessionmaker, get_db dependency
├── models/
│   ├── doubt_model.py           # Doubt ORM (id, question, ai_answer, embedding Vector(768))
│   └── course_chunk_model.py    # CourseChunk ORM (content, embedding Vector(768))
├── schemas/
│   └── doubt_schema.py          # Pydantic v2 DTOs (DoubtCreate, DoubtResponse)
├── repositories/
│   ├── doubt_repository.py      # CRUD operations for doubts
│   └── course_chunk_repository.py  # Vector search, hybrid RRF search, semantic cache query
├── services/
│   └── embedding_service.py     # Google Gemini embedding client (768-dim vectors)
├── routers/
│   └── doubt_router.py          # REST endpoints: POST /doubts/, GET /doubts/{id}, POST /doubts/{id}/stream
└── ai/
    ├── state.py                 # AgentState TypedDict for LangGraph
    ├── sanitizers.py            # Prompt injection & jailbreak regex guard
    ├── orchestrator.py          # LangGraph compiled graph, cost calculator, SSE stream generator
    └── nodes/
        ├── guardrail_node.py    # Input safety filter
        ├── refusal_node.py      # Off-topic refusal response
        ├── retriever_node.py    # pgvector HNSW hybrid retrieval
        └── tutor_node.py        # Groq LLM pedagogical answer generation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker (for PostgreSQL + Redis)

### 1. Start Infrastructure

```bash
# PostgreSQL with pgvector
docker run -d --name learntube-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=learntube \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Redis
docker run -d --name learntube-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Setup Python Environment

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg pgvector \
            redis langchain-core langgraph groq google-genai httpx pydantic
```

### 3. Configure Environment

Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run the Server

```bash
uvicorn app.server:app --port 8000 --reload
```

---

## 📡 API Endpoints

### Health Check
```http
GET /health
```
```json
{ "status": "healthy", "service": "ai tutor engine", "version": "1.0.0" }
```

### Create a Doubt
```http
POST /doubts/
Content-Type: application/json

{
  "title": "Python GIL concept",
  "question": "What is Python GIL and how does it affect multi-threading?",
  "course_id": 1,
  "tags": ["python", "threading"]
}
```
Response: `201 Created` — Doubt object with auto-generated embedding stored for semantic matching.

### Get Doubt by ID
```http
GET /doubts/{doubt_id}
```

### Stream AI Answer (SSE)
```http
POST /doubts/{doubt_id}/stream
```

**Response:** Server-Sent Events stream with 3-tier cache resolution:

```
# Cache Miss (LLM generates answer)
data: The GIL (Global Interpreter Lock) is...
data: {"event": "usage_metrics", "cached": false, "input_tokens": 89, "output_tokens": 718, "cost_inr": "₹0.0373"}

# Exact Cache Hit (Redis, ~2ms)
data: [EXACT CACHE HIT] The GIL (Global Interpreter Lock) is...
data: {"event": "usage_metrics", "cached": true, "cache_type": "exact_redis", "cost_inr": "₹0.00"}

# Semantic Cache Hit (pgvector, ~93ms)
data: [SEMANTIC CACHE HIT (93.6%)] The GIL (Global Interpreter Lock) is...
data: {"event": "usage_metrics", "cached": true, "cache_type": "semantic_vector", "similarity": 0.9355, "cost_inr": "₹0.00"}
```

---

## ⚡ Performance Benchmarks

| Scenario | Response Time | Tokens Used | Cost (INR) |
|---|---|---|---|
| **Cold Call** (LLM Inference) | ~2700ms | ~807 | ₹0.037 |
| **Redis Exact Cache Hit** | ~2ms | 0 | ₹0.00 |
| **Semantic Cache Hit** (93.6% match) | ~93ms | 0 | ₹0.00 |

> Semantic caching alone can reduce LLM API costs by **up to 95%** for platforms with repetitive student queries.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI (100% Async) | ASGI server with dependency injection |
| **Relational + Vector DB** | PostgreSQL 15 + pgvector | Course chunks & doubt embeddings (HNSW index) |
| **Cache** | Redis 7 | Exact query cache with 24h TTL |
| **AI Orchestration** | LangGraph | Multi-node StateGraph with conditional routing |
| **LLM** | Groq API (`openai/gpt-oss-120b`) | Fast inference for answer generation |
| **Embeddings** | Google Gemini (`gemini-embedding-2`) | 768-dim dense vectors for semantic search |
| **Validation** | Pydantic v2 | Rust-core request/response validation |
| **ORM** | SQLAlchemy 2.0 (asyncpg) | Async database operations |

---

## 🔒 Security

- **Prompt Injection Guard**: Regex-based sanitizer detects and blocks jailbreak patterns, system prompt extraction attempts, and off-topic queries before they reach the LLM.
- **Input Validation**: Pydantic v2 strict DTOs with field validators sanitize all incoming data.
- **Graceful Shutdown**: Lifespan manager ensures zero socket leaks on `SIGTERM` — Redis and DB connections cleanly disposed.

---

## 📄 License

MIT

---

<p align="center">
  Built with ❤️ for the EdTech ecosystem
</p>
