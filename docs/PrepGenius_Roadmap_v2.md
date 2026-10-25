# PrepGenius — Complete End-to-End Project Roadmap (v2)

**Project title:** PrepGenius — Smart Unified System for Personalized Career Readiness
**Project area:** Agentic AI, LLM Agents and Web Engineering
**Project type:** B.Tech Information Technology final-year project
**Document purpose:** Implementation roadmap, architecture guide, task checklist, testing plan and deployment plan.

> **Planning note:** This document describes the intended design. It does not claim that any milestone is complete. Scheduling and task ownership are intentionally not part of this document.

---

## Table of Contents

1. Project Vision and Scope
2. Locked Decisions
3. Supported Roles and Company Types
4. Functional Requirements
5. Technology Stack
6. High-Level Architecture
7. LangGraph and LangChain Design
8. Repository and Folder Structure
9. Implementation Phases
10. Module 1: Shared Student Profile
11. Module 2: Personalized Roadmap
12. Module 3: Resume Analyzer and Resume Builder
13. Module 4: Verified Learning Assistant (RAG)
14. Module 5: Voice-Based Mock Interview
15. Cross-Module Feedback Loops
16. Dashboard and Readiness Score
17. Database Design (TiDB / MySQL)
18. API Contract
19. Security and Reliability
20. Testing and Evaluation
21. Deployment and CI/CD
22. Definition of Done
23. Final Acceptance Checklist
24. Future Enhancements
25. Development Rules

---

## 1. Project Vision and Scope

PrepGenius is a unified AI-powered career-readiness platform for students preparing for campus placements. Students currently use separate tools for study planning, resume improvement, mock interviews and doubt-solving. PrepGenius connects these workflows through one shared student profile, one orchestration layer and one dashboard.

### 1.1 Core problems

1. **Scattered tools:** roadmap planning, resume building, interview practice and learning support are disconnected.
2. **Limited progress visibility:** there is no single place to see preparation status and weak areas.
3. **Generic recommendations:** most tools ignore the student's skills, target role, company type and available study time.
4. **Unverified AI answers:** general AI responses can be inaccurate or unsupported by evidence.

### 1.2 Main objectives

- Generate a personalized, time-aware learning roadmap.
- Analyze resumes, estimate resume quality, identify skill gaps, and build a resume from a job title and job description through guided question-and-answer.
- Conduct voice-based technical and HR mock interviews with dynamic follow-up questions and structured feedback.
- Answer learning questions using RAG with citations, and clearly label answers that are not evidence-backed.
- Track roadmap completion, resume quality and interview performance in one dashboard.
- Connect the modules: interview weak areas and resume skill gaps feed back into the roadmap.

### 1.3 MVP scope (build these first)

- Student sign-in and profile management.
- Roadmap generation, persistence, task completion and feedback-driven adaptation.
- PDF resume analysis, then guided resume builder with PDF export.
- RAG over a curated knowledge base, query routing (knowledge base / Tavily web search / direct), citations.
- Voice-based interview (browser speech-to-text and text-to-speech) with follow-ups, scoring and session summary.
- Dashboard with stored progress and an explainable readiness score.
- Authentication, authorization, logging, testing and deployment.

### 1.4 Outside the first release

- Native mobile application.
- AI avatar interviewers.
- Webcam-based body-language analysis.
- Live-coding platform integration.
- Automated job matching.
- Independent microservice deployment for each module.
- Server-side speech recognition or synthesis.
- OCR for scanned resumes.

---

## 2. Locked Decisions

| Area | Decision |
|---|---|
| Orchestration | LangGraph supervisor graph with one LangGraph subgraph per feature module |
| LLM calls | LangChain (prompt templates, structured output, retries, tools) inside every node that uses generative AI |
| LLM provider | Groq API; model name set through environment variable so it can be changed without code changes |
| Embeddings | Local HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Database | TiDB Cloud Starter (MySQL-compatible) for relational data and vector data |
| Vector storage | TiDB `VECTOR(384)` column with cosine distance; no FAISS, no Supabase, no pgvector |
| DB access | SQLAlchemy 2.x + Alembic, PyMySQL driver, TLS enabled |
| Web search | Tavily |
| Authentication | Clerk (token issued to React, verified by FastAPI) |
| Voice | Browser Web Speech API for both speech-to-text and text-to-speech |
| Resume parsing | PyMuPDF |
| Resume export | ReportLab (single-column, ATS-friendly PDF) |
| Frontend | React, JavaScript, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic v2 |
| Testing | pytest, HTTPX, Postman, DeepEval for RAG and answer evaluation |
| Deployment | Vercel (frontend), Render with Docker (backend), TiDB Cloud (database) |
| Dependency management | `pyproject.toml` with `uv` |
| Original resume PDFs | Not stored. Only extracted text and analysis results are saved |
| Knowledge-base ingestion | CLI script only; no public admin HTTP endpoint |

---

## 3. Supported Roles and Company Types

These definitions are used consistently by the roadmap, resume matching, interview and knowledge base.

### 3.1 Supported target roles (initial)

1. Backend Developer
2. Full-Stack Developer
3. Data Analyst
4. AI/ML Engineer

Each role has a JSON template in `modules/roadmap/role_templates/` listing core topics, skills, typical task hours and interview topics.

### 3.2 Company types

`company_type` is a profile field: `product`, `service` or `startup`. It is a deterministic input that changes the topic emphasis in the roadmap and the interview mix:

- `product`: heavier data structures and algorithms, system design basics.
- `service`: aptitude, CS fundamentals, communication.
- `startup`: project depth, practical full-stack or applied skills.

Target company names are stored as optional free-text context for prompts only. They do not drive any company-specific data logic.

---

## 4. Functional Requirements

### 4.1 Student and profile

- Sign up and sign in through Clerk.
- Student record is created automatically on the first authenticated API call.
- Profile fields: education, skills with proficiency, career goal, target role, company type, target companies (optional), weekly study hours, optional preparation deadline.
- All private data is scoped to the authenticated student. The client never sends a `student_id`.

### 4.2 Roadmap

- Generate a roadmap from profile data.
- Structure: phases, tasks, estimated hours, success criteria, topic tags.
- Validate schema and schedule feasibility with deterministic code.
- Save roadmap versions; exactly one version is active per student.
- Mark tasks complete or pending; edit task title, hours and due date.
- Calculate completion from persisted task data.
- Accept feedback-driven task additions (see section 15) only after student approval.

### 4.3 Resume

- Analyzer: accept a PDF with size and type validation; extract text; reject unreadable or scanned documents; detect sections; run deterministic checks and LLM analysis; optionally compare against a job title and job description; produce section-wise suggestions and an estimated score; save history; compare two analyses.
- Builder: take a job title and job description, ask the student section-by-section questions, draft each section only from the student's answers, let the student review and edit, assemble the resume and export a PDF.

### 4.4 Learning assistant

- Accept a student question.
- Route to knowledge-base retrieval, Tavily web search or direct prompting.
- Generate an answer from retrieved evidence.
- Return citations built from actual retrieved metadata.
- Label every answer with its grounding level.
- Decline or state limited evidence rather than inventing citations.
- Handle search-provider failures and timeouts.

### 4.5 Mock interview

- Choose role, interview type (`technical`, `hr`, `mixed`), topic and difficulty.
- Questions are spoken through text-to-speech; answers are captured through speech-to-text, shown as an editable transcript, then submitted.
- Text input is always available in the same screen and is the only input when the browser lacks speech support.
- Generate context-aware follow-up questions.
- Evaluate each answer with a documented rubric.
- Store every turn, score and feedback; show a session summary after the interview.

### 4.6 Dashboard

- Roadmap completion, latest resume score and history, interview scores and trends.
- Readiness score with components and last-updated time.
- Weak areas and next actions derived from measured data.
- Explicit "not attempted" states for modules with no data.

---

## 5. Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, JavaScript, Tailwind CSS | UI, forms, dashboard, chat and interview experience |
| Voice (browser) | Web Speech API (`SpeechRecognition`, `speechSynthesis`) | Speech-to-text and text-to-speech |
| Authentication | Clerk | Identity, sign-in/sign-up, JWT issuance |
| Backend | Python, FastAPI | REST APIs, validation, authorization |
| Orchestration | LangGraph | Supervisor graph, module subgraphs, conditional routing, retry loops |
| LLM integration | LangChain (`langchain-groq`, prompt templates, structured output, retries, tools) | All generative AI calls inside graph nodes |
| LLM inference | Groq API | Generation, analysis, evaluation |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` via `sentence-transformers` | Chunk and query vectors |
| Database | TiDB Cloud Starter (MySQL-compatible) | Relational records and vector search |
| ORM / migrations | SQLAlchemy 2.x, Alembic, PyMySQL | Models, queries, schema versioning |
| Web search | Tavily (LangChain Tavily tool) | Current external information |
| PDF reading | PyMuPDF | Resume text extraction |
| PDF writing | ReportLab | Resume export |
| Validation | Pydantic v2 | Request, response and LLM-output validation |
| Rate limiting | slowapi | Per-user and per-IP limits |
| Testing | pytest, HTTPX, Postman, DeepEval | Unit, API, graph and RAG evaluation tests |
| Deployment | Vercel, Render, Docker | Hosting and containerization |
| CI/CD | GitHub Actions | Lint, test, deploy workflows |
| Error reporting | Sentry (free tier) | Backend and frontend error tracking |

### 5.1 Stack rules

- One primary LLM provider and one search provider (Tavily).
- Use deterministic Python for permissions, validation, scoring, schedule feasibility and file checks.
- Use the LLM only for interpretation, generation, evaluation and feedback.
- API keys live in backend environment variables only.
- Pin dependencies in `pyproject.toml`.
- Check current Groq limits, Tavily limits, TiDB free quota and Render free-tier conditions before relying on them.
- Keep the Groq model name and the prompt versions configurable.

---

## 6. High-Level Architecture

PrepGenius is a **modular monolith**: one FastAPI deployment with separated feature modules. Orchestration is done by LangGraph inside that one process. There are no separate microservices.

```text
Student
  |
  v
React Web App  --(sign-in)-->  Clerk
  |                              |
  |<------ session token --------+
  |
  | HTTPS request + Bearer token
  v
FastAPI Application
  |
  +--> Auth dependency (verify Clerk JWT, resolve student)
  +--> Request validation (Pydantic), rate limiting
  |
  +--> Non-AI endpoints (profile, task updates, exports, dashboard read, health)
  |         --> feature service --> repositories --> TiDB
  |
  +--> AI endpoints
            --> graph service
                  --> Supervisor graph (LangGraph)
                        +--> roadmap subgraph
                        +--> resume analyzer subgraph
                        +--> resume builder subgraph
                        +--> interview subgraph
                        +--> learning subgraph
                        +--> adaptation subgraph
                  --> validated result persisted to TiDB
            --> typed response

Shared infrastructure
  +--> TiDB Cloud (relational tables + VECTOR column)
  +--> Groq via LangChain
  +--> Local HuggingFace embedding model
  +--> Tavily search tool
```

The React dashboard reads saved records. It never runs agents itself.

### 6.1 Architecture principles

1. One FastAPI application, one deployment, clear module boundaries.
2. API routes are thin: authenticate, validate, authorize, call a service.
3. Every AI workflow is a LangGraph graph. Operations with no LLM or multi-step logic (profile CRUD, task status update, PDF export, dashboard read) call services directly.
4. The supervisor graph routes by `request_type` and invokes only the required subgraph. A resume request never touches roadmap, interview or learning nodes.
5. Each module owns its prompts, state schema, nodes, subgraph, service and tests.
6. LangChain is used inside nodes that call a model or tool; plain Python nodes handle everything deterministic.
7. Pydantic schemas validate every API boundary and every LLM output.
8. TiDB is the single source of truth for business records, vectors and workflow progress.
9. Authenticate and authorize before reading or writing student data.
10. Long operations log timing and return clear status or error responses.

---

## 7. LangGraph and LangChain Design

### 7.1 Supervisor graph

The supervisor graph is the single entry point for AI requests.

```text
START
  |
  v
validate_request (plain)
  |
  v
load_context (plain: only the profile fields this request type needs)
  |
  v
route_by_request_type (conditional edge)
  |
  +--> roadmap_generate     -> roadmap subgraph
  +--> roadmap_adapt        -> adaptation subgraph
  +--> resume_analyze       -> resume analyzer subgraph
  +--> resume_builder_turn  -> resume builder subgraph
  +--> interview_start      -> interview subgraph
  +--> interview_turn       -> interview subgraph
  +--> learning_ask         -> learning subgraph
  |
  v
validate_output (plain: Pydantic check)
  |
  v
persist_and_log (plain: TiDB writes, activity log)
  |
  v
END
```

Supervisor state:

- `request_type`
- `student_id`
- `profile_context` (only relevant fields)
- `input_data`
- `agent_output`
- `validation_errors`
- `execution_status` (`ok`, `failed`, `needs_input`)
- `error_category`

Each subgraph has its own typed state so one module's internals do not leak into another.

### 7.2 Node types

| Node type | Implementation | Examples |
|---|---|---|
| Deterministic node | Plain Python | auth-scoped loading, file validation, feasibility check, scoring, persistence |
| LLM node | LangChain prompt + Groq model + `with_structured_output(PydanticModel)` | gap analysis, plan generation, answer evaluation, follow-up generation |
| Tool node | LangChain tool | Tavily search, TiDB vector retriever |
| Router node | Conditional edge | request routing, follow-up or next question, retry or fail |

### 7.3 State persistence (decision: stateless turns)

- Every user turn (interview answer, resume builder answer) invokes the relevant subgraph once.
- The service loads the session state from TiDB, invokes the graph, and saves the updated state back to TiDB.
- No LangGraph checkpointer is used in the MVP. TiDB tables are the single source of truth.
- This makes interrupted sessions resumable, keeps the state inspectable in SQL, and avoids depending on a MySQL-compatible checkpointer.
- A checkpointer can be evaluated later as a future enhancement.

### 7.4 Reliability rules for LLM nodes

- Temperature 0 for scoring, evaluation and extraction nodes.
- Structured output validated by Pydantic; on validation failure, retry with the error message, at most 2 retries, then fail with an explicit error status.
- `with_retry` and request timeouts on every model and tool call.
- Prompt version and model name are stored with each persisted result.
- Retrieved text, web results and user documents are passed as delimited data, never as instructions.
- Token budget guard before every call (truncate or summarize context deterministically).

---

## 8. Repository and Folder Structure

Create files as they become necessary; do not create empty placeholder files for every item.

```text
PrepGenius/
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── layouts/
│       ├── services/            # API client
│       ├── hooks/
│       │   ├── useSpeechRecognition.js
│       │   └── useSpeechSynthesis.js
│       ├── voice/               # interview voice state machine
│       ├── auth/
│       └── utils/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py      # Clerk JWT verification
│   │   │   ├── rate_limit.py
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── routes/
│   │   │           ├── profile.py
│   │   │           ├── roadmap.py
│   │   │           ├── resume.py
│   │   │           ├── resume_builder.py
│   │   │           ├── interview.py
│   │   │           ├── learning.py
│   │   │           └── dashboard.py
│   │   ├── db/
│   │   │   ├── session.py       # engine, pooling, TLS
│   │   │   ├── models.py
│   │   │   └── repositories/    # one file per entity group
│   │   ├── graphs/
│   │   │   ├── supervisor.py
│   │   │   ├── state.py
│   │   │   └── graph_service.py
│   │   ├── modules/
│   │   │   ├── profile/
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── roadmap/
│   │   │   │   ├── role_templates/
│   │   │   │   ├── state.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── feasibility.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── tests/
│   │   │   ├── adaptation/
│   │   │   │   ├── state.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── tests/
│   │   │   ├── resume/
│   │   │   │   ├── analyzer/
│   │   │   │   │   ├── parser.py
│   │   │   │   │   ├── section_extractor.py
│   │   │   │   │   ├── checks.py
│   │   │   │   │   ├── scoring.py
│   │   │   │   │   ├── redaction.py
│   │   │   │   │   ├── state.py
│   │   │   │   │   ├── nodes.py
│   │   │   │   │   └── graph.py
│   │   │   │   ├── builder/
│   │   │   │   │   ├── sections.py
│   │   │   │   │   ├── state.py
│   │   │   │   │   ├── nodes.py
│   │   │   │   │   └── graph.py
│   │   │   │   ├── exporter.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── tests/
│   │   │   ├── learning/
│   │   │   │   ├── state.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── query_router.py
│   │   │   │   ├── web_search.py     # Tavily
│   │   │   │   ├── retrieval.py      # TiDB vector search
│   │   │   │   ├── citations.py
│   │   │   │   ├── ingestion.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── tests/
│   │   │   ├── interview/
│   │   │   │   ├── rubric.py
│   │   │   │   ├── state.py
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── tests/
│   │   │   └── dashboard/
│   │   │       ├── readiness.py
│   │   │       ├── weak_areas.py
│   │   │       ├── schemas.py
│   │   │       └── service.py
│   │   ├── shared/
│   │   │   ├── llm.py               # ChatGroq factory
│   │   │   ├── embeddings.py        # local HuggingFace model
│   │   │   └── exceptions.py
│   │   └── scripts/
│   │       └── ingest_kb.py         # knowledge-base ingestion CLI
│   ├── migrations/                  # Alembic
│   ├── tests/                       # API and cross-module integration tests
│   ├── pyproject.toml
│   └── Dockerfile
│
├── knowledge_base/                  # versioned source documents
├── docs/
├── .github/
│   └── workflows/
├── .env.example
├── .gitignore
└── README.md
```

### 8.1 Folder responsibilities

- `api/v1/routes/`: HTTP handlers, request validation, authorization, response mapping. No workflow logic.
- `graphs/`: supervisor graph, shared supervisor state, and the graph service that invokes it.
- `modules/<feature>/`: everything feature-specific (state, nodes, subgraph, prompts, schemas, service, tests).
- `modules/adaptation/`: the cross-module feedback workflow (section 15).
- `modules/dashboard/`: deterministic aggregation and readiness formula; no LLM calls.
- `shared/`: infrastructure used by several modules (LLM factory, embeddings, exceptions). Feature prompts and logic stay in their module.
- `db/`: engine, models, repositories.
- `scripts/`: operational CLIs such as knowledge-base ingestion.
- `migrations/`: Alembic versions.
- `docs/`: architecture decisions, API contract, data dictionary, rubrics, evaluation results, setup instructions.

### 8.2 Feature-module contract

```text
API route -> feature service -> graph service -> supervisor -> subgraph
          -> repositories (TiDB) -> validated response
```

Other modules do not import a module's internal helpers. Cross-module work goes through service interfaces or the adaptation module.

---
## 9. Implementation Phases

Build and validate one complete feature at a time. Every phase ends with passing tests, a deployable application and documentation updates. Durations are intentionally not included.

### Phase 0 — Foundation, CI and first deployment

- [ ] Freeze MVP scope and out-of-scope list.
- [ ] Create the GitHub repository and branch/PR conventions.
- [ ] Scaffold the React and FastAPI applications and the folder structure.
- [ ] Configure `.env.example`, settings loader and secrets handling.
- [ ] Create the TiDB Cloud Starter cluster; connect with SQLAlchemy over TLS; configure pooling (`pool_pre_ping`, `pool_recycle`).
- [ ] Set up Alembic and the first migration.
- [ ] Configure Clerk and backend JWT verification.
- [ ] Add logging, a health endpoint, rate limiting and the API error format.
- [ ] Set up GitHub Actions (lint and tests).
- [ ] Deploy a minimal frontend (Vercel) and backend (Render, Docker) with a protected test endpoint.
- [ ] Define API naming, response envelope and error format.

**Deliverable:** an authenticated frontend calls a deployed backend that reads and writes TiDB.
**Exit criteria:** the repository runs from documented setup instructions on another machine and the deployed smoke test passes.

### Phase 1 — Student profile and database

- [ ] Create `students` and `student_profiles` tables and migrations.
- [ ] Implement just-in-time student creation from the Clerk token.
- [ ] Build profile forms (education, skills with level, goal, target role, company type, target companies, weekly hours, optional deadline).
- [ ] Implement `GET /profile` and `PUT /profile` with server-side validation.
- [ ] Build the dashboard shell, navigation and loading, empty, success and error states.
- [ ] Test profile access isolation between two accounts.

**Exit criteria:** a student saves a profile, signs out, signs in again and retrieves the same data.

### Phase 2 — Personalized roadmap

- [ ] Define role templates for the four supported roles.
- [ ] Define roadmap, phase and task Pydantic schemas.
- [ ] Build the roadmap subgraph (section 11.2).
- [ ] Implement feasibility checks in `feasibility.py`.
- [ ] Persist roadmap versions, phases and tasks; maintain the single active version.
- [ ] Implement task status and edit endpoints; compute completion from persisted tasks.
- [ ] Build the roadmap UI.
- [ ] Test with profiles that differ in role, company type, skills and weekly hours.

**Exit criteria:** output is valid, relevant to the role, feasible under the time budget and editable.

### Phase 3 — Resume analyzer

- [ ] Add PDF upload with type and size validation.
- [ ] Extract text with PyMuPDF; reject empty, unreadable and scanned PDFs with a clear message.
- [ ] Detect sections; run deterministic checks.
- [ ] Redact contact PII before any LLM call.
- [ ] Add LLM section analysis, optional job-description matching and the documented scoring rubric.
- [ ] Generate editable improved content.
- [ ] Save analyses, list history, compare two analyses.
- [ ] Export improved content as PDF.

**Exit criteria:** invalid files are rejected safely, feedback is structured, scores are reproducible within the stated tolerance, and the student can review and export results.

### Phase 4 — Resume builder

- [ ] Define the fixed section order and per-section question strategy.
- [ ] Build the builder subgraph (section 12.4) with persisted session state.
- [ ] Draft each section only from the student's answers; mark unconfirmed claims.
- [ ] Add review, edit and approve per section.
- [ ] Assemble the resume, show job-description keyword coverage, export PDF.
- [ ] Allow re-running the analyzer on the built resume.

**Exit criteria:** a student can go from job title and job description to an exported resume containing only information they supplied.

### Phase 5 — Knowledge base and RAG

- [ ] Collect a curated set of trusted, licensed or open learning resources aligned with the four roles.
- [ ] Create `kb_documents` and `kb_chunks` tables with the `VECTOR(384)` column and vector index.
- [ ] Build `scripts/ingest_kb.py`: load, clean, chunk (configurable size and overlap), embed, upsert idempotently by content hash.
- [ ] Preserve title, URL, document ID, page, license and version metadata.
- [ ] Implement TiDB vector retrieval with a distance threshold.
- [ ] Generate grounded answers with citations built from retrieved metadata.
- [ ] Implement insufficient-evidence behavior.
- [ ] Prepare the evaluation question set with known supporting sources.

**Exit criteria:** citations are verifiable and the assistant declines when evidence is insufficient.

### Phase 6 — Query routing and Tavily web search

- [ ] Define the common evidence and response schema for all routes.
- [ ] Build the learning subgraph with router, retrieval, web search, direct and answer nodes.
- [ ] Route current-information questions to Tavily.
- [ ] Normalize, deduplicate and rank evidence; assemble context within the token budget.
- [ ] Add timeouts, bounded retries and graceful degradation when Tavily fails.
- [ ] Test routing on representative question categories.

**Exit criteria:** routing is testable, failures are handled, and source metadata is never lost.

### Phase 7 — Voice-based mock interview

- [ ] Define role-specific topic lists and question categories.
- [ ] Build the interview subgraph (section 14.2) with persisted turn state.
- [ ] Implement session creation, turn submission, early finish and summary.
- [ ] Implement the frontend voice state machine and the two voice hooks (section 14.4).
- [ ] Implement the text input path in the same screen.
- [ ] Implement the documented rubric and per-turn feedback storage.
- [ ] Build session summary and skill-wise performance views.
- [ ] Run the browser test matrix (section 20.8).

**Exit criteria:** a student completes a spoken interview in a supported browser, reviews it later, and the session appears in dashboard history.

### Phase 8 — Supervisor integration, feedback loops and dashboard

- [ ] Assemble the supervisor graph and register all subgraphs.
- [ ] Implement the adaptation subgraph and proposal/apply flow (section 15).
- [ ] Implement the readiness formula, score snapshots, weak areas and next actions.
- [ ] Build dashboard charts from saved records.
- [ ] Test end-to-end flows across all modules.

**Exit criteria:** updating a roadmap task or completing an interview changes the dashboard correctly, and an interview or resume result can produce an approved roadmap adaptation.

### Phase 9 — Testing and evaluation

- [ ] Unit-test deterministic logic and graph routing with fake chat models.
- [ ] Test API validation, authentication and authorization.
- [ ] Run Experiments A–E (section 20).
- [ ] Run DeepEval metrics on the RAG question set.
- [ ] Measure latency and failure rates.
- [ ] Record results and known limitations.

### Phase 10 — Security hardening, deployment and documentation

- [ ] Audit every endpoint for authorization.
- [ ] Verify cross-account isolation.
- [ ] Configure production CORS, request-size limits, upload validation and rate limits.
- [ ] Confirm secrets handling and the PII redaction path.
- [ ] Verify production Clerk domain and TiDB connection settings.
- [ ] Run deployed smoke tests.
- [ ] Complete architecture, API, schema and setup documentation.

### Phase 11 — Final validation

- [ ] Freeze scope and fix critical bugs.
- [ ] Run the full acceptance checklist.
- [ ] Collect evaluation evidence and charts.
- [ ] Finalize the report and diagrams.
- [ ] Prepare slides, demo script, sample data and a backup demo.
- [ ] Document limitations.
- [ ] Prepare viva questions and answers.

---

## 10. Module 1: Shared Student Profile

The profile is the common context for all modules.

### 10.1 Fields

- Education history.
- Skills with proficiency level (`beginner`, `intermediate`, `advanced`).
- Career goal.
- Target role (one of the supported roles).
- Company type (`product`, `service`, `startup`).
- Target companies (optional text).
- Weekly study hours.
- Optional preparation deadline.
- Created and updated timestamps.

Collect only what the application uses.

### 10.2 Implementation sequence

1. Create schema and migration.
2. Implement Pydantic request and response models.
3. Implement authenticated `GET` and `PUT` endpoints.
4. Build the React form.
5. Validate on the server.
6. Load the profile when the dashboard opens.
7. Test that a student cannot read or modify another student's profile.

### 10.3 Acceptance criteria

- [ ] Profile data persists across sessions.
- [ ] Invalid values are rejected.
- [ ] Ownership is enforced from the token, not from client-supplied IDs.
- [ ] Each graph receives only the profile fields it needs.
- [ ] The frontend handles loading and errors.

---

## 11. Module 2: Personalized Roadmap

### 11.1 Inputs

- Profile: target role, company type, skills, weekly hours, optional deadline.
- Role template for the target role.
- Planning horizon: until the preparation deadline if set, otherwise 12 weeks.

### 11.2 Roadmap subgraph

```text
validate_profile (plain)
   |
load_role_template (plain, adjusted by company_type)
   |
analyze_gaps (LLM: profile skills vs template -> structured gaps)
   |
generate_plan (LLM: phases and tasks -> Pydantic schema)
   |
validate_schema (plain)
   |
check_feasibility (plain)
   |-- fail and retries < 2 --> repair_plan (LLM with violation list) --> validate_schema
   |-- fail and retries exhausted --> fail with explicit error
   |
persist_roadmap (plain: new version, set active, deactivate previous)
   |
END
```

The LLM never sets `status`, `completed_at` or IDs; code sets them.

### 11.3 Feasibility rules (deterministic)

- Total estimated hours must not exceed `weekly_hours x planning_weeks`.
- Each task is between 0.5 and 8 estimated hours.
- Every task has a title, hours and success criteria.
- Every task maps to a topic in the role template or to a gap identified for the student.
- Phases are ordered and non-empty.

### 11.4 Versioning

- Generating a roadmap creates a new version and makes it active; previous versions stay stored and inactive.
- Dashboard completion always uses the active version.
- Progress belongs to one version; regenerating asks the student to confirm.
- A previous version can be re-activated.

### 11.5 Output shape (illustrative)

```json
{
  "title": "Backend Developer Preparation",
  "target_role": "Backend Developer",
  "phases": [
    {
      "name": "Core Foundations",
      "position": 1,
      "tasks": [
        {
          "title": "Revise SQL joins",
          "estimated_hours": 4,
          "success_criteria": "Solve practice queries involving joins",
          "topic_tags": ["sql", "joins"]
        }
      ]
    }
  ]
}
```

Final Pydantic models are defined before implementation. Status is stored in the database, not produced by the LLM.

### 11.6 Evaluation

- Do different profiles get meaningfully different plans?
- Are topics relevant to the role and company type?
- Are hours feasible?
- Are tasks specific and actionable?
- Does progress reflect persisted task statuses?

---

## 12. Module 3: Resume Analyzer and Resume Builder

### 12.1 Analyzer subgraph

```text
validate_file (plain: PDF signature, size limit, page limit)
   |
extract_text (plain: PyMuPDF)
   |
check_extractable (plain: reject empty, unreadable, likely scanned)
   |
deterministic_checks (plain: contact info, sections, length, extraction quality)
   |
redact_pii (plain: mask email, phone, address before any LLM call)
   |
identify_sections (plain heuristics)
   |
   +--> llm_section_analysis (LLM, structured)
   +--> jd_match (plain keyword overlap + LLM skill-gap analysis, only if job description given)
   |
compute_score (plain, scoring.py)
   |
generate_improvements (LLM: only from evidence in the resume)
   |
persist_analysis (plain; original PDF is not stored)
   |
END
```

Contact checks run on the raw text before redaction.

### 12.2 Scoring (proposed starting rubric, documented in `scoring.py`)

| Component | Points | Source |
|---|---|---|
| Contact information present | 10 | deterministic |
| Expected sections present | 15 | deterministic |
| Extraction quality and length sanity | 10 | deterministic |
| Job-description keyword overlap | 15 | deterministic (only when a job description is provided) |
| Section content quality | 50 | LLM, rubric per section, temperature 0 |

When no job description is provided, the keyword component is removed and the score is renormalized to 100. The score is an internal estimate, not a guarantee of passing any company's screening system. The database field is named `resume_score`.

### 12.3 Rules for LLM analysis

- Return structured feedback for education, skills, projects, experience or internships, achievements, summary and role alignment.
- Every claim about the student must be supported by text from the submitted resume.
- Never invent projects, skills, grades or achievements.
- Store prompt version and model name with each analysis.

### 12.4 Builder subgraph (turn-based)

Inputs: `job_title` and `job_description` (both required).

Fixed section order: `contact`, `education`, `skills`, `projects`, `experience`, `achievements`, `summary` (summary is drafted last).

```text
start_session (plain)
   |
parse_job_description (LLM: required skills and keywords, structured)
   |
generate_question (LLM: targeted question for the current section using the job keywords and earlier answers)
   |   <--- student answers (one request per answer) --->
validate_answer (plain: non-empty, minimum length)
   |
check_completeness (LLM: need follow-up? max 2 follow-ups per section)
   |-- yes --> generate_question
   |-- no  --> draft_section (LLM: bullets only from the student's answers, flag unconfirmed claims)
                    |
              student reviews, edits and approves the section (plain: save approved text)
                    |
              next section or finish
   |
assemble_resume (plain)
   |
keyword_coverage (plain: coverage of job-description keywords)
   |
END (export through ReportLab, optional re-analysis through the analyzer)
```

Every turn loads and saves session state in `resume_builder_sessions`.

### 12.5 Builder rules

- Draft only from information the student provided; never fabricate metrics, employers or tools.
- Mark any statement that goes beyond the student's answer as needing confirmation.
- The student approves each section before it enters the final resume.
- The export template is single-column, plain-text-friendly and ATS-friendly.

### 12.6 Acceptance criteria

- [ ] Invalid files are rejected.
- [ ] Empty and unreadable text is handled.
- [ ] Section-wise feedback is available.
- [ ] Job matching is optional in the analyzer.
- [ ] Scores are explainable and reproducible within tolerance.
- [ ] Builder drafts contain only student-provided facts.
- [ ] Exported content can be reviewed before download.
- [ ] Previous analyses can be compared.

---

## 13. Module 4: Verified Learning Assistant (RAG)

### 13.1 Knowledge base ingestion (CLI)

```text
Trusted source documents (versioned in knowledge_base/)
   |
Load and clean
   |
Chunk with metadata (size and overlap configurable)
   |
Embed locally (all-MiniLM-L6-v2, 384-d)
   |
Upsert into kb_chunks (VECTOR(384)) keyed by content hash
```

- Run `python -m app.scripts.ingest_kb` against TiDB. Re-running is idempotent.
- Each document records title, URL, license, version and indexed time.
- Only content with a usable license or the owner's permission enters the knowledge base.

### 13.2 Learning subgraph

```text
validate_question (plain)
   |
route_query (router node)
   |
   +--> knowledge_base --> retrieve_chunks (TiDB cosine search, top-k, distance threshold)
   +--> web            --> tavily_search (timeout, max results)
   +--> direct         --> (no evidence)
   |
normalize_evidence (plain: common Evidence schema)
   |
dedupe_and_rank (plain)
   |
assemble_context (plain: token budget)
   |
generate_answer (LLM)
   |
build_citations (plain: from actual Evidence objects)
   |
END
```

### 13.3 Routing

- Rule-based first: current-information signals ("latest", "recent", "news", "this year", salary or hiring trends, a version number) go to `web`; subject questions that match role topics go to `knowledge_base`.
- If the rules are ambiguous, an LLM classification node decides.
- If knowledge-base retrieval returns nothing under the distance threshold, the subgraph may fall back to `web` once; otherwise it returns an insufficient-evidence response.
- `direct` is used only for generic questions that need no evidence.

### 13.4 Response schema

```json
{
  "answer": "...",
  "route": "knowledge_base | web | direct",
  "grounding": "knowledge_base | web | none",
  "verified": true,
  "insufficient_evidence": false,
  "citations": [
    {"index": 1, "title": "...", "url": "...", "page": 12, "excerpt": "..."}
  ]
}
```

- `verified` is true only for answers grounded in knowledge-base evidence with citations.
- Web answers carry `grounding: web` and are shown as "web-sourced".
- Direct answers carry `grounding: none` and are shown as "unverified".

### 13.5 Citation rules

- Citations are built by code from retrieved metadata, never typed by the LLM.
- The LLM only refers to evidence by index; code maps indices to sources.
- Page numbers appear only when known; original URLs are preserved.
- A citation string is not proof that the source supports the claim; show the excerpt.
- If evidence is insufficient, say so instead of inventing support.

### 13.6 Evaluation

Use a fixed question set with known supporting sources. Measure with DeepEval where applicable:

- Retrieval relevance (contextual relevancy and recall).
- Answer faithfulness to the retrieved evidence.
- Citation correctness.
- Abstention when evidence is insufficient.
- Latency and failure behavior.
- Comparison against direct prompting with the same model.

---

## 14. Module 5: Voice-Based Mock Interview

### 14.1 Session setup

- Select role, interview type (`technical`, `hr`, `mixed`), topic and difficulty.
- Default session: 5 main questions with at most 1 follow-up per question (maximum 10 turns). Both limits are configurable.
- Feedback is stored per turn and revealed in the session summary at the end, as in a real interview.

### 14.2 Interview subgraph (one invocation per student answer)

```text
load_session (plain: session and turns from TiDB)
   |
validate_answer (plain: empty, too short, unintelligible -> ask the student to repeat, do not score)
   |
evaluate_answer (LLM, structured, temperature 0, rubric in rubric.py)
   |
decide_next (router)
   |-- weak or incomplete answer and no follow-up used yet --> generate_followup (LLM, uses the previous answer)
   |-- main question count not reached --> generate_next_question (LLM)
   |-- session complete --> summarize_session (LLM) + compute_overall (plain) + extract_weak_topics (plain)
   |
persist_turn (plain: ordered turn record, scores, feedback)
   |
END
```

Starting a session uses the same subgraph with `interview_start`, which generates the first question.

### 14.3 Rubric (documented in `rubric.py`, versioned)

Per-turn dimensions, each scored 0–10 by the evaluator:

- Technical correctness (technical questions only).
- Relevance to the question.
- Completeness of explanation.
- Clarity and structure of communication.
- Use of examples or reasoning.

Proposed weights (adjust and document before evaluation):

| Dimension | Technical | HR |
|---|---|---|
| Technical correctness | 0.35 | not applicable |
| Relevance | 0.20 | 0.30 |
| Completeness | 0.20 | 0.25 |
| Communication | 0.15 | 0.25 |
| Examples or reasoning | 0.10 | 0.20 |

Turn and session scores are normalized to 0–100. Communication is judged from the transcript text only. The system does not claim to measure confidence, emotion or tone.

### 14.4 Voice implementation (Web Speech API)

Browser support is limited: speech recognition works reliably in Chrome and Edge. The design must therefore be explicit and defensive.

**Capability detection on page load**

- Detect `SpeechRecognition` / `webkitSpeechRecognition` and `speechSynthesis`.
- Require a secure context (HTTPS, or localhost in development).
- If speech recognition is unavailable, show a clear message ("Voice answers work in Chrome or Edge") and keep text input active. Text input is always present in the same screen.

**Voice state machine (single source of truth in `frontend/src/voice/`)**

```text
idle
  -> speaking_question   (text-to-speech plays the question)
  -> listening           (speech recognition active after speech ends)
  -> reviewing           (editable transcript; student can re-record, edit or send)
  -> submitting          (request in flight)
  -> speaking_question   (next question) or finished
errors: mic_denied, no_speech, recognition_error, network_error, synthesis_error
```

**Reliability rules**

- Never run recognition while speech synthesis is playing (prevents the microphone from capturing the question).
- Cancel any speech and stop recognition on navigation, unmount and tab visibility loss.
- Speech synthesis: wait for `voiceschanged`, select one voice by a fixed preference rule (preferred language, then any English voice, then default), and store the choice. Split long questions into sentence-sized utterances to avoid cut-off playback.
- Speech recognition: tap-to-start microphone; end on silence or manual stop; show interim results; always let the student edit the transcript before submitting.
- Handle microphone permission states (granted, denied, prompt) with recovery instructions.
- Handle `no-speech`, `audio-capture`, `not-allowed` and `network` errors with a retry action and a switch to text input.
- Show a one-time privacy notice: the browser may send audio to its speech provider.
- Provide a replay-question button and a mute toggle.

### 14.5 Acceptance criteria

- [ ] The interview session persists and can be revisited.
- [ ] Questions and answers remain in the correct order (`turn_index`).
- [ ] Follow-ups use the previous answer as context.
- [ ] Empty or unintelligible answers are handled without scoring.
- [ ] Feedback explains each score.
- [ ] Voice input and spoken questions work in Chrome and Edge.
- [ ] Text input works when speech is unavailable.
- [ ] Voice state machine passes the browser test matrix.

---

## 15. Cross-Module Feedback Loops

These flows make the system unified instead of five separate tools.

### 15.1 Adaptation subgraph

```text
load_source (plain: interview weak topics or resume skill gaps)
   |
load_active_roadmap (plain)
   |
propose_tasks (LLM: reinforcement tasks, structured, topic tags matched to the role template)
   |
check_feasibility (plain: remaining hours vs weekly budget; cap on added tasks)
   |
save_proposal (plain: roadmap_adaptations row, status = proposed)
   |
END
```

### 15.2 Flow

1. A completed interview produces weak topics; a resume analysis produces skill gaps.
2. The student requests an adaptation from the interview or resume result.
3. The system returns a stored proposal with new tasks (`source = interview` or `resume`).
4. The student reviews and approves the proposal.
5. Approved tasks are added to the active roadmap; hours are re-validated.
6. The dashboard reflects the updated roadmap.

Proposals are stored server-side so the client cannot tamper with them. Nothing is added without approval.

---

## 16. Dashboard and Readiness Score

### 16.1 Readiness formula

Computed by plain Python in `readiness.py`:

```text
Components (each 0 to 100):
  L = completed task hours / total task hours of the active roadmap x 100
  V = resume_score of the latest analysis
  I = mean overall_score of the last 3 completed interview sessions

Base weights:
  w_L = 0.40, w_V = 0.30, w_I = 0.30

Readiness R = sum(w_k x component_k for attempted components)
              / sum(w_k for attempted components)
```

- A component with no data is "not attempted" and is excluded; it is never treated as zero.
- The dashboard shows how many of the three components are included.
- If no component is attempted, readiness is `null` and the UI shows "Not enough data".
- The learning assistant is informational and does not contribute to the score.
- The weights are a proposed starting point, not validated values.
- Readiness is an internal progress indicator, not a placement prediction.

### 16.2 Weak areas and next actions

- Weak areas come from stored data: interview topic scores, resume section scores below a threshold, roadmap topics with no completed tasks.
- Next actions are generated by deterministic rules from the weakest component and weak areas (for example: "Resume score is the lowest component: re-run the analyzer after editing" or "Request a roadmap adaptation from your last interview").
- No LLM is needed for the dashboard.

### 16.3 Dashboard elements

- Roadmap completion and pending versus completed tasks.
- Latest resume score and score history.
- Latest interview score and score history.
- Readiness score with component breakdown, "not attempted" markers and last-updated time (from `score_snapshots`).
- Weak areas and next actions.
- Recent activity.

---
## 17. Database Design (TiDB / MySQL)

TiDB is the single database for relational data and vectors. IDs are UUIDs stored as `CHAR(36)`. All timestamps are UTC.

| Table | Key fields and purpose |
|---|---|
| `students` | `id`, `clerk_user_id` (unique), `email`, `name`, `created_at` |
| `student_profiles` | `student_id` (PK/FK), `education` (JSON), `skills` (JSON: name, level), `career_goal`, `target_role`, `company_type`, `target_companies` (JSON), `weekly_hours`, `prep_deadline`, `updated_at` |
| `roadmaps` | `id`, `student_id`, `version`, `is_active`, `title`, `target_role`, `total_estimated_hours`, `source` (generated or adapted), `prompt_version`, `model`, `created_at`; unique (`student_id`, `version`) |
| `roadmap_phases` | `id`, `roadmap_id`, `position`, `name`, `description` |
| `roadmap_tasks` | `id`, `roadmap_id`, `phase_id`, `position`, `title`, `estimated_hours`, `success_criteria`, `topic_tags` (JSON), `status` (pending or completed), `completed_at`, `due_date`, `source` (generated, interview or resume) |
| `roadmap_adaptations` | `id`, `roadmap_id`, `source_type` (interview or resume), `source_id`, `proposed_tasks` (JSON), `status` (proposed, applied, rejected), `created_at` |
| `resume_analyses` | `id`, `student_id`, `job_title`, `job_description`, `extracted_text` (redacted), `sections` (JSON), `deterministic_checks` (JSON), `section_scores` (JSON), `resume_score`, `score_breakdown` (JSON), `feedback` (JSON), `improved_content` (JSON), `prompt_version`, `model`, `created_at` |
| `resume_builder_sessions` | `id`, `student_id`, `job_title`, `job_description`, `status`, `current_section`, `answers` (JSON), `drafts` (JSON), `approved_sections` (JSON), `created_at`, `updated_at` |
| `interview_sessions` | `id`, `student_id`, `role`, `interview_type`, `topic`, `difficulty`, `status` (in_progress, completed, abandoned), `overall_score`, `weak_topics` (JSON), `summary` (JSON), `rubric_version`, `model`, `started_at`, `ended_at` |
| `interview_turns` | `id`, `session_id`, `turn_index`, `parent_turn_id`, `kind` (question or follow_up), `question`, `answer`, `input_mode` (voice or text), `scores` (JSON), `feedback` (JSON), `topic_tags` (JSON), `created_at`; unique (`session_id`, `turn_index`) |
| `learning_queries` | `id`, `student_id`, `question`, `route`, `grounding`, `verified`, `answer`, `citations` (JSON), `created_at` |
| `kb_documents` | `id`, `title`, `source_url`, `license`, `version`, `content_hash`, `indexed_at` |
| `kb_chunks` | `id`, `document_id`, `chunk_index`, `page`, `text`, `metadata` (JSON), `embedding` (`VECTOR(384)`) with a cosine vector index |
| `score_snapshots` | `id`, `student_id`, `learning_completion`, `resume_score`, `interview_score`, `readiness`, `components_included`, `created_at` |
| `activity_logs` | `id`, `student_id`, `event_type`, `ref_id`, `created_at` |

### 17.1 Database rules

- Enforce foreign keys and indexes; add indexes on `student_id`, `(session_id, turn_index)` and `(roadmap_id, status)`.
- Every user-owned query filters by the authenticated `student_id`.
- Never trust a client-supplied `student_id`.
- Use Alembic migrations for every schema change.
- Configure the engine with TLS, `pool_pre_ping` and `pool_recycle` because the serverless database drops idle connections.
- Verify the vector index DDL and distance-function syntax against the current TiDB documentation when writing the migration.
- Do not log secrets or unnecessary personal data.
- Define retention: students can delete their analyses, builder sessions, interview transcripts and learning history (`DELETE /me/data`).
- Original resume PDFs are not stored. Only the redacted extracted text and analysis results are saved.

---

## 18. API Contract

All endpoints are under `/api/v1` and require authentication except `GET /health`. Names are proposals; freeze request and response schemas before frontend integration.

| Method | Endpoint | Purpose | Graph request type |
|---|---|---|---|
| GET | `/health` | Health check | none |
| GET | `/me` | Current student (created on first call) | none |
| DELETE | `/me/data` | Delete the student's stored module data | none |
| GET | `/profile` | Get profile | none |
| PUT | `/profile` | Create or update profile | none |
| POST | `/roadmaps` | Generate a roadmap | `roadmap_generate` |
| GET | `/roadmaps` | List roadmap versions | none |
| GET | `/roadmaps/{roadmap_id}` | Get one roadmap with phases and tasks | none |
| POST | `/roadmaps/{roadmap_id}/activate` | Re-activate a version | none |
| PATCH | `/roadmaps/tasks/{task_id}` | Update status, title, hours or due date | none |
| POST | `/roadmaps/active/adaptations` | Create an adaptation proposal from an interview or resume result | `roadmap_adapt` |
| POST | `/roadmaps/adaptations/{adaptation_id}/apply` | Apply an approved proposal | none |
| POST | `/resumes/analyze` | Analyze an uploaded PDF (optional job title and description) | `resume_analyze` |
| GET | `/resumes/analyses` | List analysis history | none |
| GET | `/resumes/analyses/{analysis_id}` | Get one analysis | none |
| GET | `/resumes/analyses/compare` | Compare two analyses (`a`, `b` query parameters) | none |
| PUT | `/resumes/analyses/{analysis_id}/improved-content` | Save edited improved content | none |
| POST | `/resumes/analyses/{analysis_id}/export` | Export improved resume as PDF | none |
| POST | `/resume-builder/sessions` | Start a builder session (job title, job description) | `resume_builder_turn` |
| POST | `/resume-builder/sessions/{session_id}/answers` | Submit an answer, receive the next question or section draft | `resume_builder_turn` |
| POST | `/resume-builder/sessions/{session_id}/sections/{section}/approve` | Approve or edit a section draft | none |
| GET | `/resume-builder/sessions/{session_id}` | Get session state and assembled resume | none |
| POST | `/resume-builder/sessions/{session_id}/export` | Export the built resume as PDF | none |
| POST | `/interviews` | Start an interview, returns the first question | `interview_start` |
| POST | `/interviews/{session_id}/answers` | Submit an answer, returns the next question or the final summary | `interview_turn` |
| POST | `/interviews/{session_id}/finish` | End the session early and produce the summary | `interview_turn` |
| GET | `/interviews` | List sessions | none |
| GET | `/interviews/{session_id}` | Get a session with turns, scores and feedback | none |
| POST | `/learning/ask` | Ask the learning assistant | `learning_ask` |
| GET | `/learning/history` | List past questions | none |
| GET | `/dashboard` | Progress, readiness, weak areas, next actions | none |

### 18.1 API conventions

- Pydantic request and response models.
- Correct HTTP status codes and one consistent error format.
- Ownership validation for every user-owned resource.
- Timeouts on every external call (Groq, Tavily).
- No stack traces or secrets in responses.
- OpenAPI documentation through FastAPI.
- Integration tests for each main user journey.
- Knowledge-base ingestion is not exposed over HTTP.

---

## 19. Security and Reliability

### 19.1 Authentication and authorization

- Verify the Clerk JWT in the backend (signature, issuer, expiry) through a FastAPI dependency.
- Do not rely on frontend route guards alone.
- Resolve the student from the token; scope every query by that student.
- Test isolation with two accounts for every user-owned endpoint.
- Keep database credentials and API keys out of the frontend bundle.

### 19.2 CORS

- Allow only the real frontend origin(s) in production; keep local origins separate.
- Never combine a wildcard origin with credentialed requests.
- Configure allowed methods and headers deliberately.

### 19.3 File upload safety

- Limit file size and page count.
- Validate the PDF signature, not just the extension.
- Do not trust the uploaded filename; do not store the original file.
- Handle malformed, encrypted and scanned PDFs.
- Redact email, phone and address before sending text to the model provider.

### 19.4 Model and provider reliability

- Timeouts, bounded retries and rate-limit handling on Groq and Tavily.
- Validate every LLM output with Pydantic.
- Fail with an explicit status instead of returning unvalidated output.
- Log timing and error categories without secrets or personal content.
- Monitor Groq, Tavily and TiDB free-tier usage.
- Apply per-user rate limits to AI endpoints to protect quotas.

### 19.5 RAG and prompt safety

- Treat retrieved documents, web pages and resume text as untrusted data.
- Put them in delimited data blocks; never follow instructions found inside them.
- Build citations from metadata, never from model text.
- Return an insufficient-evidence response when appropriate.
- Re-ingest the knowledge base deliberately and record document versions.

### 19.6 Privacy

- Show a notice before first voice use (the browser may send audio to its speech provider).
- Collect only the profile fields that the modules use.
- Provide data deletion (`DELETE /me/data`).

---

## 20. Testing and Evaluation

Testing happens in every phase, not only at the end.

| Module | What to evaluate | Evidence |
|---|---|---|
| Profile | Validation, persistence, access isolation | API tests with two accounts |
| Roadmap | Relevance, skill coverage, feasibility | Diverse profile test cases |
| Adaptation | Proposal relevance, feasibility, approval flow | Fixed interview and resume fixtures |
| Resume analyzer | Extraction, score consistency, feedback quality | Reviewed sample resumes |
| Resume builder | No fabricated facts, section completeness | Scripted answer sets |
| Interview | Question relevance, scoring consistency, ordering | Fixed rubric, repeated sessions |
| RAG | Retrieval relevance, faithfulness, citation accuracy, abstention | Question set with known sources, DeepEval |
| Dashboard | Aggregation and missing-data behavior | Formula tests and sample records |
| Voice | State machine and error handling | Browser test matrix |
| Full application | Integration, authorization, failures, latency | End-to-end runs |

### 20.1 Test categories

- Unit tests for deterministic functions (feasibility, scoring, readiness, validators).
- Graph tests using LangChain fake chat models to verify routing, retry loops and persistence without calling Groq.
- API tests for validation and authorization.
- Integration tests against a separate TiDB test database (vector tests included).
- End-to-end tests for complete user flows.
- Performance checks for latency and concurrent requests.
- Manual usability tests with representative students.

### 20.2 Experiment A — Roadmap personalization

Use profiles with different roles, company types, skill levels and weekly hours. Measure whether plans change appropriately and respect the time budget.

### 20.3 Experiment B — Resume analysis

Use representative resumes and job descriptions. Compare section checks with manually reviewed results. Measure score consistency across repeated runs and recommendation relevance.

### 20.4 Experiment C — Resume builder

Run scripted answer sets. Verify drafts contain only supplied facts and that job-description keyword coverage improves.

### 20.5 Experiment D — Mock interviews

Run repeated sessions with the same answers. Compare rubric scores and feedback across runs. Claim improvement only if the data supports it.

### 20.6 Experiment E — RAG versus direct prompting

Use questions with known answers and supporting documents. Compare RAG and direct prompting with the same model. Measure retrieval relevance, faithfulness, citation accuracy and unsupported claims.

### 20.7 Experiment F — End-to-end integration

1. Create a profile.
2. Generate a roadmap.
3. Complete roadmap tasks.
4. Analyze a resume.
5. Build a resume from a job description.
6. Complete a voice interview.
7. Apply an adaptation from the interview result.
8. Ask learning questions.
9. Verify that the dashboard reflects all saved results.

### 20.8 Voice browser test matrix

| Browser | Expected behavior |
|---|---|
| Chrome (desktop) | Full voice input and spoken questions |
| Edge (desktop) | Full voice input and spoken questions |
| Chrome (Android) | Test and document actual behavior |
| Firefox | Clear unsupported-voice message, text input works |
| Safari | Test and document actual behavior; fall back to text if needed |

Record the setup, test-set size, scoring criteria, results and limitations in the final report.

---

## 21. Deployment and CI/CD

### 21.1 Deployment architecture

```text
Browser
   |
   v
React Frontend (Vercel)  -->  Clerk
   |
   v
FastAPI Backend (Render, Docker)
   |
   +--> TiDB Cloud Starter (relational + vector)
   +--> Groq API
   +--> Tavily API
   +--> Local HuggingFace embedding model (inside the backend image)
```

### 21.2 Docker and embedding model

- Install CPU-only PyTorch and `sentence-transformers` to keep the image small.
- Download the embedding model during the Docker build so it is not fetched at cold start.
- Verify memory use on the chosen Render instance with the model loaded; if the instance cannot hold it, switch to a smaller embedding option before launch (a change to the embedding model requires re-ingesting the knowledge base and updating the vector dimension).
- Run Alembic migrations as a pre-deploy step.
- Run `ingest_kb.py` from a local machine or CI job against TiDB; it is not part of the web process.

### 21.3 Deployment sequence

1. Ensure the application works locally.
2. Create production environment variables.
3. Configure TiDB connectivity (TLS) and run migrations.
4. Configure Clerk for the production domain.
5. Deploy the backend and test the health endpoint.
6. Run knowledge-base ingestion against production TiDB.
7. Deploy the frontend.
8. Add the production frontend origin to CORS.
9. Test sign-in, profile, each module, uploads, citations, voice interview and dashboard.
10. Configure logs and Sentry.
11. Document free-tier constraints.

### 21.4 CI/CD

A GitHub Actions workflow should:

- Install dependencies with `uv`.
- Run formatting and lint checks.
- Run unit and graph tests (fake models, no secrets).
- Run API tests that do not need production secrets.
- Run TiDB-dependent tests only where test credentials are configured.
- Report failures before merge.
- Deploy only through an explicitly configured workflow.

### 21.5 Deployment caveats

- Free tiers may sleep, limit resources or change policies.
- TiDB Starter and Groq enforce usage quotas; monitor them.
- Test the deployed environment separately from local development.
- Keep all provider keys on the backend.

---

## 22. Definition of Done

A module is done when:

- [ ] The main user workflow works end to end.
- [ ] Inputs and outputs have defined schemas.
- [ ] Data persists in TiDB where required.
- [ ] Authentication and ownership checks work.
- [ ] Errors and provider failures are handled.
- [ ] Loading, empty and error states exist in the UI.
- [ ] Unit, graph and integration tests pass.
- [ ] Logs support debugging without exposing secrets.
- [ ] The feature is documented.
- [ ] Someone other than the original developer can run and test it.

---

## 23. Final Acceptance Checklist

### Platform

- [ ] Authentication works.
- [ ] Profile data persists.
- [ ] User-owned data is isolated.
- [ ] Dashboard loads actual database values.
- [ ] Supervisor graph routes each AI request type to the correct subgraph.

### Roadmap

- [ ] Roadmap is personalized by role, company type and skills.
- [ ] Hours are validated.
- [ ] Tasks can be completed, reopened and edited.
- [ ] Progress is calculated from persisted records.
- [ ] Versions are stored and one is active.
- [ ] Adaptation proposals require approval.

### Resume

- [ ] PDF validation works.
- [ ] Extraction errors and scanned PDFs are handled.
- [ ] Section-wise feedback is available.
- [ ] Optional job-description matching works.
- [ ] Analysis history and comparison work.
- [ ] Builder asks section-wise questions and drafts only supplied facts.
- [ ] Resume export works for analyzer and builder.

### RAG and web search

- [ ] Knowledge-base ingestion is idempotent.
- [ ] TiDB vector retrieval works.
- [ ] Source metadata is preserved.
- [ ] Citations refer to real sources.
- [ ] Insufficient evidence is handled.
- [ ] Tavily failures are handled.
- [ ] Answers are labeled verified, web-sourced or unverified.
- [ ] RAG has been compared against direct prompting.

### Interview and voice

- [ ] Sessions persist and can be revisited.
- [ ] Turns are ordered correctly.
- [ ] Follow-ups use prior answers.
- [ ] Spoken questions and voice answers work in Chrome and Edge.
- [ ] Text input works without speech support.
- [ ] Scores and feedback are available per rubric.

### Integration and deployment

- [ ] Results are saved to TiDB.
- [ ] Readiness handles missing component scores.
- [ ] Feedback loops (interview or resume to roadmap) work.
- [ ] Production CORS is configured.
- [ ] Secrets are not exposed.
- [ ] Deployment smoke tests pass.
- [ ] Documentation and demonstration materials are ready.

---

## 24. Future Enhancements

Consider only after the core system is stable and evaluated:

- Evaluate a LangGraph checkpointer for TiDB/MySQL.
- Server-side speech recognition and synthesis for consistent cross-browser voice.
- OCR for scanned resumes.
- Persistent long-term learning memory.
- Advanced retrieval, hybrid search and reranking.
- Additional model providers and fallback routing.
- Background workers for long-running tasks.
- Resume layout analysis; builder prefill from an existing analysis.
- Additional interview modalities.
- Job matching and application tracking.
- Mobile application.
- Recommendations based on longitudinal outcomes.

---

## 25. Development Rules

1. **Build a working vertical slice first:** authentication, profile persistence, then one complete roadmap flow.
2. **Keep deterministic logic deterministic:** permissions, validation, scheduling constraints, scoring and arithmetic never depend on LLM compliance.
3. **Validate all model outputs:** requested structure is not guaranteed structure.
4. **Use citations honestly:** a citation must point to actual retrieved evidence.
5. **Persist business records in TiDB:** graph state is never the only record of a roadmap, analysis or interview.
6. **Avoid unnecessary agent calls:** route each request only to the subgraph it needs.
7. **Keep the project deployable throughout development.**
8. **Evaluate your claims:** back personalization, score consistency and citation quality with recorded test results.
9. **Protect student data:** authentication, authorization, PII redaction, retention and deletion.
10. **Document decisions:** architecture choices, prompt versions, rubric versions, test results and known limitations.

---

## Final Recommendation

Implementation order:

1. **Foundation:** React, FastAPI, Clerk, TiDB, CI and first deployment.
2. **Shared profile:** profile module and persistence.
3. **Roadmap:** subgraph, feasibility checks, versions and task tracking.
4. **Resume analyzer, then resume builder.**
5. **Learning:** knowledge base, TiDB vector retrieval, Tavily routing, citations.
6. **Voice interview:** subgraph, rubric, voice state machine.
7. **Supervisor, feedback loops and dashboard.**
8. **Validation:** security, testing, evaluation, deployment and documentation.

**Success criterion:** a student can sign in, build a profile, generate a roadmap, analyze or build a resume, practice a spoken interview, ask evidence-backed learning questions, turn weak areas into approved roadmap tasks, and see saved results reflected in one dashboard.
