# PrepGenius

**Smart Unified System for Personalized Career Readiness**  
B.Tech IT Final-Year Project | Agentic AI, LLM Agents & Web Engineering

---

## Overview

PrepGenius is a unified AI-powered career-readiness platform for students preparing for campus placements. It connects scattered tools—roadmap planning, resume building, interview practice, and learning support—into one platform with a shared student profile, orchestration layer, and dashboard.

### Core Problems Solved
1. **Scattered tools** — roadmap, resume, interview prep, learning are disconnected
2. **Limited progress visibility** — no single place to see preparation status
3. **Generic recommendations** — tools ignore student's skills, target role, company type, study time
4. **Unverified AI answers** — general AI responses can be inaccurate

### Main Objectives
- Generate personalized, time-aware learning roadmaps
- Analyze resumes, estimate quality, identify skill gaps, build resumes from JD via guided Q&A
- Conduct voice-based technical/HR mock interviews with dynamic follow-ups and structured feedback
- Answer learning questions using RAG with citations; label unverified answers
- Track roadmap completion, resume quality, interview performance in one dashboard
- Connect modules: interview weak areas & resume skill gaps → roadmap adaptations

---

## Architecture

```
+-------------+     +------------------+     +-----------------+
|   React     |---->|    FastAPI       |---->|    TiDB Cloud   |
|  Frontend   |     |   Backend        |     |  (MySQL + VECTOR)|
+-------------+     +------------------+     +-----------------+
      |                    |                        |
      |                    v                        |
      |            +------------------+            |
      |            |  LangGraph       |            |
      |            |  Supervisor +    |            |
      |            |  Subgraphs       |            |
      |            +------------------+            |
      |                    |                        |
      v                    v                        v
+-------------+     +------------------+     +-----------------+
|   Clerk     |     |  NVIDIA Nemotron |     |     Tavily      |
|   Auth      |     |  3 Ultra + Groq  |     |   Web Search    |
+-------------+     +------------------+     +-----------------+
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, Tailwind CSS, Clerk React |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy 2.x, Alembic |
| **Database** | TiDB Cloud (MySQL-compatible + VECTOR) |
| **LLM** | NVIDIA Nemotron 3 Ultra (primary), Groq (fallback) |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (384-d) |
| **Orchestration** | LangGraph (supervisor + subgraphs) |
| **LLM Framework** | LangChain (prompt templates, structured output, retries) |
| **Vector Search** | TiDB VECTOR(384) + cosine distance |
| **Web Search** | Tavily API |
| **Auth** | Clerk (JWT issued to React, verified by FastAPI) |
| **Voice** | Browser Web Speech API (STT + TTS) |
| **PDF** | PyMuPDF (extract), ReportLab (export) |
| **Deployment** | Vercel (frontend), Render + Docker (backend) |

---

## Project Structure

```
PrepGenius/
├── frontend/                 # React + Vite + Tailwind
│   ├── src/
│   │   ├── auth/             # Clerk AuthContext
│   │   ├── components/       # SkillsManager, EducationManager
│   │   ├── pages/            # Login, Register, Profile
│   │   ├── layouts/          # DashboardLayout
│   │   └── services/         # API client
│   └── package.json
│
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── api/v1/           # REST endpoints
│   │   │   └── endpoints/    # auth, profile, roadmap, resume, learning
│   │   ├── modules/          # Feature modules
│   │   │   ├── profile/      # Student profile CRUD
│   │   │   ├── auth/         # Register, login, JWT
│   │   │   ├── roadmap/      # LangGraph subgraph + TiDB models
│   │   │   ├── resume/       # Analyzer (multi-agent) + Builder (turn-based)
│   │   │   └── learning/     # RAG, Tavily, citations, routing
│   │   ├── core/             # Config, security, DB session
│   │   ├── db/               # SQLAlchemy, Alembic
│   │   └── scripts/          # ingest_kb.py
│   ├── tests/                # 203 tests (unit + integration)
│   ├── pyproject.toml        # Dependencies (uv)
│   └── alembic/              # Migrations
│
├── docs/
│   └── PrepGenius_Roadmap_v2.md  # Complete implementation roadmap
│
└── README.md
```

---

## Implemented Features (Backend Complete)

| Module | Status | Key Features |
|--------|--------|--------------|
| **Authentication** | ✅ | Clerk JWT + dev mock mode, register/login, JWT tokens |
| **Student Profile** | ✅ | 36 roles, 3 company types, skills/education CRUD |
| **Roadmap** | ✅ | LangGraph subgraph, feasibility checks, versioning, task CRUD, adaptations |
| **Resume Analyzer** | ✅ | PDF upload, ATS scoring, LLM section analysis, job matching, PDF export |
| **Resume Builder** | ✅ | 7-section turn-based Q&A, JD parsing, keyword coverage, PDF export |
| **Learning Assistant (RAG)** | ✅ | KB models, ingestion CLI, TiDB vector retrieval, citations |
| **Query Routing + Tavily** | ✅ | KB models, ingestion CLI, TiDB vector retrieval, citations |

---

## Test Coverage

**203 tests passing, 0 warnings**

| Category | Tests |
|----------|-------|
| Roadmap (feasibility, schemas, graph, API) | 97 |
| Learning (routing, citations, retrieval, schemas) | 28 |
| Auth, Profile, Resume Analyzer, Builder | 55 |
| Retry behavior | 23 |

```bash
cd backend && uv run pytest --tb=short -q
```

---

## Getting Started

### Prerequisites
- Python 3.12+, Node 18+, uv, Docker (for TiDB local)
- Clerk account (or use `DEV_MOCK_AUTH=true`)

### Backend
```bash
cd backend
uv sync
cp .env.example .env  # Configure keys
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173 (proxies /api to :8000)
```

### Database (TiDB Cloud)
1. Create TiDB Cloud Starter cluster
2. Update `.env` with connection details
3. Run migrations: `uv run alembic upgrade head`

### Knowledge Base Ingestion
```bash
cd backend
uv run python -m app.scripts.ingest_kb --source-dir knowledge_base/
```

---

## API Endpoints (v1)

| Module | Endpoints |
|--------|-----------|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| **Profile** | `GET /profile`, `PUT /profile` |
| **Roadmap** | `POST /roadmap/generate`, `GET /roadmap`, `GET /roadmap/history`, `GET /roadmap/completion`, `PATCH /roadmap/tasks/{id}`, `POST /roadmap/adaptations` |
| **Resume Analyzer** | `POST /resumes/analyze`, `GET /resumes/analyses` |
| **Resume Builder** | `POST /resumes/builder/start`, `POST /resumes/builder/sessions/{id}/answer`, `POST /resumes/builder/sessions/{id}/approve`, `GET /resumes/builder/sessions/{id}/export` |
| **Learning** | `POST /learning/ask`, `GET /learning/history`, `GET /learning/history/{id}` |
| **Health** | `GET /health`, `GET /v1/models` |

---

## Roadmap Progress

| Phase | Module | Status |
|-------|--------|--------|
| 0 | Foundation, CI, Deployment | ✅ Complete (deploy pending) |
| 1 | Student Profile & Database | ✅ Complete |
| 2 | Personalized Roadmap | ✅ Complete (UI pending) |
| 3 | Resume Analyzer | 🟡 ~90% (PII redaction pending) |
| 4 | Resume Builder | ✅ Complete (UI pending) |
| 5 | Knowledge Base & RAG | ✅ Backend Complete |
| 6 | Query Routing + Tavily | ✅ Backend Complete |
| 7 | Voice Mock Interview | ❌ Not Started |
| 8 | Supervisor + Dashboard | 🟡 ~15% |
| 9 | Testing & Evaluation | 🟡 ~35% |
| 10 | Security, Deployment, Docs | 🟡 ~30% |
| 11 | Final Validation | ❌ Not Started |

See [docs/PrepGenius_Roadmap_v2.md](docs/PrepGenius_Roadmap_v2.md) for detailed checklist.

---

## Development

### Code Style
- Python: ruff, black (via uv)
- JavaScript: ESLint, Prettier
- Commits: Conventional Commits (feat:, fix:, chore:, docs:, test:, refactor:)

### Running Tests
```bash
# Backend
cd backend && uv run pytest --tb=short -q

# Frontend
cd frontend && npm run lint
```

---

## Deployment

| Service | Platform |
|---------|----------|
| Frontend | Vercel |
| Backend | Render (Docker) |
| Database | TiDB Cloud Starter |
| Auth | Clerk |

### Environment Variables (Backend)
```env
MYSQL_HOST=...
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DB=prepgenius
NVIDIA_API_KEY=...
GROQ_API_KEY=...
TAVILY_API_KEY=...
CLERK_SECRET_KEY=...
CLERK_PUBLISHABLE_KEY=...
CLERK_JWT_ISSUER=...
JWT_SECRET=...
DEV_MOCK_AUTH=true  # For local dev without Clerk
```

---

## License

B.Tech IT Final-Year Project — Educational Use

---

## Contributing

1. Create feature branch: `git checkout -b feat/your-feature`
2. Commit with conventional prefix: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
3. Push and create PR to `main`
4. Squash merge after review

---

**Built for campus placement preparation — turning scattered prep into a unified, evidence-backed journey.**