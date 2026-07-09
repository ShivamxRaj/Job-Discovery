# Job Discovery — AI-Powered Career Intelligence Platform

> A production-grade fullstack SaaS that matches job seekers to the right opportunities using semantic search, hybrid ranking, and explainable AI.

---

## What This Is

Job Discovery is not a job board. It is a **Career Intelligence Platform** — the difference being:

| Job Board | Career Intelligence Platform |
|---|---|
| "Apply here" | Why this job fits you |
| Show all listings | Ranked by your real profile |
| No personalization | Skill gap roadmap |
| No feedback | What to learn next |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                     │
│         Dashboard · Resume Upload · Recommendations          │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│                    Backend (FastAPI)                          │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Ingestion    │  │ Normalization│  │ Matching Engine  │   │
│  │ Engine       │  │ & Dedup      │  │ (Hybrid Ranking) │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │              │
│  ┌──────▼─────────────────▼────────────────────▼──────────┐  │
│  │              PostgreSQL + pgvector                      │  │
│  │   jobs · companies · skills · embeddings · resumes     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Celery Beat (Background Workers)                    │    │
│  │  • Daily job ingestion (2AM UTC)                     │    │
│  │  • Daily embedding queue (00:05 UTC)                 │    │
│  │  • Email digest (daily + weekly)                     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, CSS Modules |
| Backend | FastAPI, Python 3.12, SQLAlchemy (async) |
| Database | PostgreSQL 16 + pgvector extension |
| Embeddings | GitHub Models → `text-embedding-3-small` (1536 dims) |
| Background Jobs | Celery + Redis (Celery Beat for scheduling) |
| Auth | JWT (access + refresh tokens) |
| Resume Parsing | OpenAI GPT-4o-mini via GitHub Models |
| Containerization | Docker + Docker Compose |

---

## Sprint History

| Sprint | Focus | Status |
|---|---|---|
| Sprint 1 | Data Foundation (multi-source ingestion, schema) | ✅ Complete |
| Sprint 2 | Data Quality Engine (normalization, dedup, salary parser, diversity ranking) | ✅ Complete |
| Sprint 3 | Career Intelligence Engine (hybrid ranking, skill gap roadmap) | 🔄 In Progress |

---

## Project Structure

```
job-discovery/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI route handlers
│   │   │   ├── admin.py     # Admin endpoints + queue health
│   │   │   ├── auth.py      # JWT auth (login, register, refresh)
│   │   │   ├── jobs.py      # Job search + recommendations
│   │   │   ├── resumes.py   # Resume upload + parsing
│   │   │   └── applications.py
│   │   ├── core/
│   │   │   ├── config.py    # Settings (env-based)
│   │   │   └── security.py  # JWT helpers
│   │   ├── models/
│   │   │   └── models.py    # SQLAlchemy ORM models
│   │   ├── repositories/    # DB query layer
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── celery_app.py          # Celery tasks + Beat schedule
│   │   │   ├── embedding_service.py   # Async embedding queue
│   │   │   ├── ingestion_service.py   # Job ingestion pipeline
│   │   │   ├── matching_service.py    # Hybrid ranking engine
│   │   │   ├── normalization_service.py # Company/salary/category normalization
│   │   │   ├── deduplication_service.py # Semantic + exact dedup
│   │   │   ├── openai_service.py      # LLM + embedding calls
│   │   │   ├── resume_service.py      # Resume parsing pipeline
│   │   │   └── connectors/            # Job source adapters (RemoteOK, Adzuna, etc.)
│   │   └── seed/            # DB seed data (skills hierarchy, canonical companies)
│   ├── alembic/             # DB migrations
│   ├── tests/               # Test suite (77 tests)
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   │   ├── dashboard/   # Main recommendation dashboard
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── upload/      # Resume upload
│   │   ├── components/      # Reusable UI components
│   │   └── lib/
│   │       └── api.ts        # Type-safe API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example             # Template — copy to .env and fill in keys
└── README.md
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose, OR
- Python 3.12, Node.js 20, PostgreSQL 16 with pgvector

### 1. Clone and configure
```bash
git clone https://github.com/ShivamxRaj/Job-Discovery.git
cd Job-Discovery
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY (or GitHub Models token)
```

### 2. Run with Docker
```bash
docker-compose up -d
```

### 3. Run locally (development)

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

**Background workers** (separate terminal)
```bash
cd backend
celery -A app.services.celery_app.celery worker --loglevel=info
celery -A app.services.celery_app.celery beat --loglevel=info
```

---

## Key Features

### ✅ Multi-Source Job Ingestion
- RemoteOK, Adzuna, Arbeitnow, Lever
- Daily automated ingestion via Celery Beat (2AM UTC)
- Duplicate detection: exact hash + semantic similarity (pgvector cosine)

### ✅ Intelligent Data Normalization
- Canonical company resolution with alias table
- Hierarchical skill taxonomy (150+ skills with parent relationships)
- Granular salary parser with confidence scores
- Multi-signal job category classification

### ✅ Recommendation Engine
- Semantic search (pgvector)
- Company diversity re-ranking (configurable: max 2 per company in top-10)
- Score explainability stored per recommendation

### ✅ Resume Intelligence
- PDF/text upload with async AI parsing
- Structured profile extraction (skills, experience, education)
- Versioned resume history

### ✅ Background Processing
- Celery Beat schedules: ingestion, embedding, email digests, cleanup
- Embedding queue with 150/day GitHub Models free tier
- Automated daily embedding at 00:05 UTC

---

## Environment Variables

See `.env.example` for all required variables. Key ones:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/jobdb
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=github_pat_...   # GitHub Models token or OpenAI key
SECRET_KEY=your-jwt-secret
```

---

## Operational Notes

### Embedding Pipeline (TD-006)
- **Provider**: GitHub Models free tier (150 req/day)
- **Status**: Known Operational Limitation
- **Mitigation**: Celery Beat runs daily at 00:05 UTC, processing up to 150 PENDING jobs
- **Monitor**: `GET /api/v1/admin/queue-health` (admin auth required)
- **Upgrade trigger**: When ingestion volume consistently exceeds 150 jobs/day

---

## License

MIT
