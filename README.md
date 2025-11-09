# Automatiq.ai Product Recommendation Agent

Deliver a conversational assistant that recommends laptops and workstations from a curated 31-product catalogue. The system combines Retrieval-Augmented Generation (RAG) with Google's Gemini 2.5 Pro to provide grounded answers, multi-turn dialog, and real-time analytics.

```
┌──────────────────────────┐       ┌───────────────────────────┐
│ React + Vite Frontend    │       │ FastAPI Backend           │
│ - Chat UI (WebSocket)    │  WS   │ - REST + WebSocket APIs   │
│ - Metrics Dashboard      │◄──────┤ - RAG (NumPy cosine)      │
│ - React Query / Context  │       │ - Gemini LLM abstraction  │
└────────────┬─────────────┘       │ - Metrics + logging       │
             │ REST                └───────┬────────┬──────────┘
             ▼                            RAG      Metrics
    Browser Client                ┌────────┴────────┴──────────┐
                                  │ Products Catalog (JSON)     │
                                  │ Embedding Cache (npy)       │
                                  └─────────────────────────────┘
```

## Features

- **RAG pipeline** with Gemini embeddings and optional hybrid keyword scoring.
- **Gemini 2.5 Pro** abstraction with structured JSON outputs and streaming support.
- **Conversation tracking & metrics** (latency, recommendations, feedback) with exportable CSV.
- **Modern React UI** (Tailwind + shadcn-inspired components) featuring streaming chat, recommendation cards, and live dashboard.
- **Dockerised deployment** and local dev workflows.

## Getting Started

### 1. Clone

```bash
git clone <repo-url>
cd HOME_ASSIGNMENT_AUTOMATIQ_AI
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # PowerShell on Windows
pip install -r requirements.txt

copy .env.example .env           # Provide your Gemini API key
setx GEMINI_API_KEY "your-key"   # or use dotenv

uvicorn app.main:app --reload
```

API runs on `http://localhost:8000` (REST + WebSocket).

### 3. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

App is served on `http://localhost:5173` with API proxying.

### 4. Docker (Optional)

```bash
docker compose up --build
```

Frontend available at `http://localhost:5173`, backend at `http://localhost:8000`.

## Configuration

Backend reads environment variables in `backend/.env`:

| Variable              | Default                     | Description                                |
|-----------------------|-----------------------------|--------------------------------------------|
| `GEMINI_API_KEY`      | `None`                      | Google Gemini API key                      |
| `EMBEDDING_MODEL`     | `gemini-embedding-001`      | Embedding model identifier                 |
| `LLM_MODEL`           | `gemini-2.5-pro`            | Conversational model                       |
| `VECTOR_STORE_PATH`   | `backend/app/data/embeddings.npy` | Cached embeddings                    |
| `MAX_HISTORY_MESSAGES`| `6`                         | Tracked messages per side (user/assistant) |
| `RAG_TOP_K`           | `5`                         | Retrieval candidates passed to LLM         |
| `ENABLE_HYBRID_SEARCH`| `true`                      | Keyword bonus for exact spec matches       |
| `METRICS_STORAGE_DIR` | `backend/app/data/metrics`  | Session logs & CSV exports                 |

Without an API key, the backend falls back to deterministic hashed embeddings and heuristic responses so you can develop offline.

## API Overview

### Chat (`/api/chat`)

- `POST /message` – body `{ session_id, message, user_preferences? }` → returns `reply`, retrieved products, reasoning, timings.
- `POST /feedback` – body `{ session_id, message_id, feedback }`.
- `GET /history/{session_id}` – returns stored message history.
- `WebSocket /stream` – bidirectional streaming with chunked assistant replies and metadata.

### Metrics (`/api/metrics`)

- `GET /sessions` – list session IDs.
- `GET /session/{id}` – session-specific metrics.
- `GET /aggregate` – aggregate statistics across sessions.
- `GET /export` – CSV download of metrics.

## Frontend Highlights

- `ChatInterface` handles session lifecycle, streaming WebSocket connection, and recommendation rendering.
- `MessageList` auto-scrolls with streaming chunks; `MessageBubble` styles user vs. agent dialogue.
- `MetricsDashboard` uses React Query to fetch aggregates, session detail, and supports CSV export.
- Shared state managed via `ChatContext`; `services/api.ts` centralises REST + WebSocket helpers.

## Monitoring & Metrics

- Latencies (retrieval + LLM) captured for every turn.
- Recommendations and feedback tracked per session.
- Aggregate view surfaces total sessions, average turns, latency means, top SKUs, and sentiment ratio.
- Metrics persisted as JSON under `backend/app/data/metrics` and exportable via CSV.

## Design Decisions

- **RAG + Gemini**: ensures grounded recommendations from a constrained catalogue while leveraging Gemini’s dialog quality.
- **In-memory vectors**: NumPy cosine similarity keeps retrieval fast for a small catalogue; embeddings cached to disk to avoid regenerating.
- **Provider abstraction**: `GeminiProvider` implements `LLMProvider`, enabling future provider swaps (e.g., OpenAI, Claude).
- **Streaming-first UX**: WebSocket streaming mimics modern assistants and keeps the UI responsive.
- **Offline development**: deterministic hashing for embeddings & heuristic replies allow local testing without external calls.

## Testing & Sanity Checks

1. Start backend (`uvicorn app.main:app --reload`).
2. Start frontend (`npm run dev`).
3. Open `http://localhost:5173`:
   - Send a prompt; verify assistant responds and “Conversation Insights” counters update.
   - Confirm recommended products appear in sidebar.
4. Switch to Metrics view; aggregated cards should populate (turn count, latencies, feedback ratio). Select a session to inspect detail.

## Future Extensions

- Authentication & user profiles.
- Product comparison view / saved carts.
- Voice input and multimodal recommendations.
- CI/CD pipeline with linting, formatting, and contract tests.

## Repository Structure

```
backend/
  app/
    main.py
    config.py
    models.py
    routers/
    services/
    data/products.json
frontend/
  src/
    components/Chat
    components/Dashboard
    services/api.ts
docker-compose.yml
README.md
```

You’re ready to run `uvicorn` and `npm run dev`, or `docker compose up`, for the full stack experience. Enjoy building with Automatiq.ai!
