# RAAHAT — Autonomous Continuity Engine

> **"When life breaks, RAAHAT keeps everything else from breaking."**

A production-quality hackathon prototype demonstrating a **real, functional multi-agent AI system** built with LangGraph, Google Gemini, RAG, and FastAPI.

---

## Architecture

```
User Event → SituationAgent → ImpactAgent → PlannerAgent
              ↓ (LangGraph)
           ExecuteAgent (Education/Insurance/Finance/Document/Communication)
              ↓
           VerificationAgent → [REPLAN if blocked] → ReplannerAgent
              ↓
           DeliverResult → ContinuityRestored
```

### Key Innovations

- **Dynamic Replanning**: When the insurance claim is rejected (missing discharge summary), the system detects this, creates new tasks to fetch the document, then retries — all autonomously
- **World Event Injection**: Inject "exam date moved" mid-workflow and watch the system replan in real-time
- **RAG-Grounded Decisions**: Every policy lookup is backed by real knowledge base documents (FAISS + sentence-transformers)
- **Deterministic Verification**: VerificationAgent uses programmatic rules — NOT the LLM — to verify task outcomes

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Build the knowledge base index
python ../scripts/ingest_knowledge.py

# Start the server (with reload)
uvicorn app.main:app --reload --port 8000
```

Or use the unified script:
```bash
python scripts/start.py
```

### 2. Configure LLM (optional)

```bash
cd backend
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

Without a key, the system runs with a **MockLLMProvider** that returns deterministic demo data — full workflow still executes.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Demo Flow

1. **Launch Demo** → System starts RAAHAT for hospitalization scenario
2. **Watch agents execute** → SituationAgent → ImpactAgent → PlannerAgent → ...
3. **Insurance claim REJECTED** → Missing discharge_summary → ReplannerAgent kicks in
4. **DocumentAgent fetches** discharge_summary from hospital
5. **Insurance claim RETRIED** → Succeeds ✅
6. **Click "Inject World Event"** → Exam date moved → System replans exam request
7. **Continuity Restored** ✅

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 2.5 Flash (with Mock fallback) |
| Agent Orchestration | LangGraph |
| RAG | sentence-transformers + FAISS |
| Backend | FastAPI + asyncio |
| Real-time | WebSocket |
| Persistence | SQLite (aiosqlite) |
| Frontend | Vite + React + TypeScript |
| Styling | Tailwind CSS + Framer Motion |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/session/start` | Create a new session |
| POST | `/api/event` | Submit a life event |
| GET | `/api/state/{session_id}` | Get full state |
| GET | `/api/tasks/{session_id}` | Get task execution plan |
| GET | `/api/agents/{session_id}` | Get agent statuses |
| GET | `/api/timeline/{session_id}` | Get event timeline |
| POST | `/api/events/inject` | Inject a world event |
| WS | `/ws/events/{session_id}` | Real-time event stream |
| GET | `/api/health` | Health check |

---

## Disclaimer

> SANDBOX MODE: All data is synthetic. No real APIs, no real money, no real health data. This is a demonstration system.
