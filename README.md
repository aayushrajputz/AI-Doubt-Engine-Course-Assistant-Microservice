# 🎓 LearnTube AI — Intelligent Video Course Doubt Engine

> **Production-grade AI-powered doubt resolution & video course platform** built for modern EdTech. Combines **LangGraph multi-agent orchestration**, **pgvector HNSW semantic search**, **Server-Sent Events (SSE) streaming**, and a **Coursera/Udemy-style React web application** with automated YouTube transcription and smart chaptering.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15_+_pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7_Alpine-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi_Agent-FF6F00)](https://langchain-ai.github.io/langgraph/)

---

## 🏗️ System Architecture

```
                          Learner / Web Application (React + Vite)
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
                                          │  │ (Prompt Injection   │  │
                                          │  │  & Safety Guard)    │  │
                                          │  └──────────┬──────────┘  │
                                          │             ▼             │
                                          │  ┌─────────────────────┐  │
                                          │  │ Retriever Node      │  │
                                          │  │ (RRF Hybrid Search: │  │
                                          │  │  Vector + Keyword)  │  │
                                          │  └──────────┬──────────┘  │
                                          │             ▼             │
                                          │  ┌─────────────────────┐  │
                                          │  │ Tutor Node (LLM)    │  │
                                          │  │ Adaptive Hinglish/EN│  │
                                          │  │ Token-by-Token SSE  │  │
                                          │  └─────────────────────┘  │
                                          └───────────────────────────┘
```

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| **Udemy / Coursera 3-Pane Web App** | Modern responsive React UI: Left Playlist sidebar, Center interactive Video Player + Seekable Chapters, Right Real-Time AI Doubt Assistant. |
| **Real-Time SSE Streaming Chapter Generator** | Auto-generates structured chapters from video transcripts and streams them row-by-row live over Server-Sent Events directly into PostgreSQL! |
| **Universal YouTube Transcription** | Multi-language transcript parser with automatic fallback (English, Hindi, Hinglish, auto-captions) without needing manual timestamps. |
| **Adaptive Pedagogical AI Tutor** | Natural Hinglish/English language mirroring — provides direct intuitions, real-world analogies, concise code snippets, and common traps. |
| **Hierarchical Two-Tier RAG** | **Tier 1 (Local Bounded)**: Searches pgvector HNSW chunks within current chapter timestamp boundary. **Tier 2 (RRF Fallback)**: Cross-video Reciprocal Rank Fusion search across the entire course. |
| **Timestamp Bucketing Cache** | Chapter-level cache keys (`doubt_cache:video:id:chapter:id:hash`) saving 90%+ LLM costs on repeated doubt timestamps. |
| **Video Doubt Hotspots Analytics** | SQL aggregation rankings (`LEFT JOIN doubts ON timestamp BETWEEN start_time AND end_time`) highlighting difficult lecture segments in red/orange badges. |
| **Two-Tier Intelligent Caching** | **Tier 1**: Redis exact match (~2ms, ₹0.00). **Tier 2**: pgvector HNSW semantic similarity (≥85%, ₹0.00). |
| **Dual Rate Limiting & Budgeting** | Sliding-window limiter: max 5 requests/hr + 10,000 tokens/hr via Redis TTL keys (cache hits are free). |
| **Full Video CRUD & Cascade Cleanup** | Clean deletion of videos, cascade deleting associated chapters and doubt histories to preserve database integrity. |

---

## 📁 Project Structure

```
├── doubt-ui/                     # React + Vite Frontend Web Application
│   ├── src/
│   │   ├── App.jsx               # Master state, Course switcher & Header
│   │   ├── Student.jsx           # 3-Pane Learner View (Playlist + Video + Chat)
│   │   ├── Admin.jsx             # Instructor Studio (Videos, Hotspots, SSE Chapters)
│   │   ├── api.js                # Fetch API & ReadableStream SSE client
│   │   └── styles.css            # Dark-mode responsive styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js            # Reverse proxy configuration (/api -> :8000)
├── app/                          # FastAPI Backend Microservice
│   ├── server.py                 # FastAPI ASGI, Lifespan, Logging middleware
│   ├── core/
│   │   ├── database.py           # AsyncEngine pool (pool_pre_ping=True, recycle=300)
│   │   └── rate_limiter.py       # Redis sliding-window limiter & token budgeting
│   ├── models/
│   │   ├── doubt_model.py        # Doubt ORM (Vector(768) pgvector embeddings)
│   │   ├── video_model.py        # Video & VideoChapter ORM
│   │   └── course_chunk_model.py # CourseChunk ORM for RAG retrieval
│   ├── schemas/
│   │   ├── doubt_schema.py       # Pydantic v2 DTOs with model validators
│   │   └── video_schema.py       # Video, Chapter, Bulk & Hotspots DTOs
│   ├── services/
│   │   ├── chapter_resolver.py   # Smart 3-tier timestamp resolver
│   │   ├── embedding_service.py  # Google Gemini embedding client (768-dim)
│   │   └── transcript_service.py # YouTube transcript & sliding-window generator
│   ├── repositories/
│   │   ├── doubt_repository.py   # Doubt CRUD queries
│   │   └── course_chunk_repository.py # pgvector HNSW hybrid RRF & bounded search
│   ├── routers/
│   │   ├── doubt_router.py       # /doubts/, /doubts/{id}/stream
│   │   └── video_router.py       # /admin/videos/, /auto-chapters-stream, /hotspots
│   └── ai/
│       ├── state.py              # LangGraph AgentState TypedDict
│       ├── sanitizers.py         # Prompt injection & jailbreak regex sanitizer
│       ├── orchestrator.py       # LangGraph multi-node state graph & SSE generator
│       └── nodes/
│           ├── guardrail_node.py # Safety validation filter
│           ├── refusal_node.py   # Safe off-topic refusal handler
│           ├── retriever_node.py # pgvector hybrid retrieval node
│           └── tutor_node.py     # Adaptive Hinglish/English pedagogical tutor
├── chat.py                       # Unified interactive CLI client (video optional)
├── demo_student_video_doubt.py   # Live demo showing Exact & Semantic caching
├── test_day_14_chaos_edge_cases.py
├── test_day_15_bulk_and_hotspots.py
├── requirements.txt
└── docker-compose.yml
```

---

## ⚡ Quick Start

### 1. Start Infrastructure (PostgreSQL + Redis)

```bash
# PostgreSQL 15 with pgvector
docker run -d --name learntube-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=learntube \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Redis 7
docker run -d --name learntube-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Setup & Run Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt

# Start FastAPI Server
uvicorn app.server:app --port 8000 --reload
```

Configure `.env`:
```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/learntube
REDIS_URL=redis://localhost:6379
```

### 3. Setup & Run Frontend Web App

```powershell
cd doubt-ui
npm install
npm run dev
```

Open browser at **`http://localhost:5173/`** 🎉

---

## 📡 API Endpoints

### Student Doubt Resolution
- `POST /doubts/` — Create doubt (Mode A: General Course, Mode B: Video & Timestamp context)
- `POST /doubts/{id}/stream` — Server-Sent Events (SSE) token streaming (Exact/Semantic Cache badges, tokens & cost metrics)
- `GET /doubts/{id}` — Get doubt details

### Instructor Studio & Video APIs
- `POST /admin/videos/` — Add a new video lecture
- `GET /admin/videos/course/{course_id}` — List all videos for playlist view
- `DELETE /admin/videos/{video_id}` — Cascade delete video, chapters, and associated doubts
- `POST /admin/videos/{video_id}/auto-chapters-stream` — **SSE Real-time streaming chapter generator**
- `POST /admin/videos/{video_id}/chapters/bulk` — Bulk manual chapter importer with validation
- `GET /admin/videos/{video_id}/chapters` — Get chronological chapters
- `GET /admin/videos/{video_id}/hotspots` — Video doubt hotspots analytics

---

## ⚡ Performance Benchmarks

| Scenario | Response Time | Tokens Used | Cost (INR) |
|---|---|---|---|
| **Cold Call** (Groq LLM Inference) | ~1800ms | ~450 | ₹0.021 |
| **Redis Exact Cache Hit** | ~2ms | 0 | ₹0.00 |
| **Semantic Cache Hit** (≥85% match) | ~90ms | 0 | ₹0.00 |

---

## 📄 License
MIT License. Built with ❤️ for scalable AI EdTech microservices.
