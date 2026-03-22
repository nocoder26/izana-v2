# Izana Chat — Developer Guide

## What is this?
Fertility wellness companion app — AI chat, personalized plans, bloodwork analysis, partner support.

## Architecture
- **Frontend:** Next.js 15 (all client components), Tailwind CSS, Framer Motion, Zustand, Capacitor 8
- **Backend:** FastAPI, Python 3.12, Supabase (Postgres + pgvector + Auth), Groq (LLM), OpenAI (embeddings)
- **Task Queue:** Redis (Upstash) + arq for all heavy work (chat pipeline, plan generation)
- **Infra:** Netlify (frontend), Render (backend + worker + cron), Supabase (database)

## Critical Decisions (Section A5 + A6 in build guide)
1. **JWT auth** — verify Supabase tokens server-side, NOT X-User-ID header
2. **Task queue** — ALL swarm work runs in arq workers, SSE polls Redis streams
3. **Client-only** — no React Server Components (Capacitor compatibility)
9. **Compliance before streaming** — Swarm 7 runs on FULL response before any tokens stream
12. **Redis fallback** — if Redis down, run pipeline inline (slower but functional)

## Key Commands
```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload          # API server
arq app.workers.worker.WorkerSettings  # Task queue worker
pytest tests/ -v                       # Run tests (77 passing)

# Frontend
cd frontend
npm run dev                            # Dev server
npx next build                         # Production build
```

## Inviolable Rules
1. User NEVER sees a plan not approved by a nutritionist
2. App is completely anonymous — no real names, no email
3. Medical disclaimers on every clinical response
4. FIE is READ-ONLY on production data
5. Every component supports light AND dark mode
6. Every screen works at 375px width (iPhone SE)
