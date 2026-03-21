# IZANA CHAT — COMPLETE BUILD GUIDE FOR CLAUDE CODE
## From Empty Directory to Deployed Product

**Date:** March 21, 2026
**Version:** Final (Consolidated — this is the ONE document)
**Audience:** Claude Code — a developer who has never seen this product before

---

> **READ THIS FIRST:**
> This document contains everything you need to build Izana from scratch.
> It explains WHAT the product is, HOW it looks, HOW it works, and HOW to build it.
> You do not need any other document. If something isn't specified here, ask.

---

# SECTION A: WHAT IS IZANA?

## A1. Product Summary

Izana Chat is a **fertility wellness companion app**. It helps women going through fertility treatments (IVF, IUI, egg freezing, natural conception, or exploring options) by providing:

1. **An AI chatbot** that answers fertility questions using a curated knowledge base of 236 clinical documents, with cited sources
2. **Personalised daily plans** — nutrition (meals), exercise (video), and meditation (audio) — tailored to the user's treatment phase, preferences, allergies, and wellness profile
3. **Every plan is reviewed by a real human nutritionist** before the user sees it (this is the non-negotiable rule)
4. **Bloodwork analysis** — upload a blood test PDF/photo, get personalised biomarker interpretation
5. **Daily check-ins** — mood tracking with AI-powered insights
6. **Partner support** — a connected partner gets their own app with coaching on how to support
7. **Provider reports** — shareable medical summary PDFs for the user's doctor

The app is **completely anonymous**. Users sign up with a pseudonym (e.g., "BraveOcean42"), not their real name or email. No personally identifiable information is collected.

## A2. Treatment Types & Phases

Users are on one of five treatment paths. Each path has distinct phases that change what content, plans, and check-ins the user receives:

```
IVF:
  PREPARING (14d) → BASELINE (14d) → STIMS (10d) → TRIGGER (36h) →
  RETRIEVAL (1d) → FERTILIZATION (5d) → TRANSFER (1d) → TWW (14d) →
  BETA (3d) → OUTCOME → RECOVERY (14d) → BETWEEN_CYCLES (30d)

IUI:
  PREPARING → MEDICATION → TRIGGER → PROCEDURE_DAY → TWW → BETA →
  OUTCOME → RECOVERY

Natural Conception:
  FOLLICULAR → FERTILE_WINDOW → TWW → BETA

Egg Freezing:
  PREPARING → STIMS → TRIGGER → RETRIEVAL → RECOVERY

Exploring:
  LEARNING → CONSIDERING (indefinite, educational content only)
```

## A3. The 11 AI Swarms (Backend Brain)

The chatbot runs on a pipeline of 11 specialised AI agents ("swarms"). Each has a specific job:

| # | Name | Job | Model |
|---|------|-----|-------|
| 0 | Polyglot | Translate user input to English (if needed) | llama-3.3-70b |
| 1 | Gatekeeper | Classify: is this fertility-related? Is it safe? | llama-3.3-70b |
| 2 | BloodworkExtractor | OCR + extract biomarker values from images/PDFs | Groq Vision → OpenAI fallback |
| 3 | ClinicalBrain | RAG: search 236 clinical docs, return relevant passages | text-embedding-3-small + pgvector |
| 4 | ChatResponseCurator | Generate the final clinical response with citations | llama-3.3-70b |
| 5 | BloodworkAnalyser | Interpret biomarker values against reference ranges | llama-3.3-70b |
| 6 | BloodworkResponseCurator | Format analysis in patient-friendly language | llama-3.3-70b |
| 7 | ComplianceChecker | Add medical disclaimers, check tone, verify citations | llama-3.1-8b |
| 8 | GapAgent | Detect when the knowledge base can't answer a question | llama-3.1-8b |
| 9 | ContextAgent | Summarise conversation context for the next response | llama-3.1-8b |
| 10 | SentimentAgent | Analyse emotional tone to adapt Izana's responses | llama-3.1-8b |

**Chat pipeline order:** User message → Swarm 0 (translate) → Swarm 1 (gate) → Swarm 9 (context) → Swarm 3 (RAG) → Swarm 4 (respond) → Swarm 7 (compliance) → Swarm 0 (translate back) → **Stream approved text token-by-token** → Response

> **IMPORTANT (Decision 9):** Swarm 7 (compliance) runs on the COMPLETE response from Swarm 4 BEFORE any tokens are streamed to the user. The user never sees unchecked medical content. The search animation ("Crafting your answer...") covers this additional ~0.5s of latency.

## A4. Inviolable Rules

These rules can NEVER be violated, no matter what:

```
╔══════════════════════════════════════════════════════════════════╗
║ 1. User NEVER sees any plan not approved by a nutritionist.    ║
║ 2. All injection tracking is REMOVED from current scope.       ║
║ 3. Chat is the interface for EVERYTHING.                       ║
║ 4. Every personalised plan requires nutritionist approval.     ║
║ 5. The app is completely anonymous — no real names, no email.  ║
║ 6. Medical disclaimers appear on every clinical response.      ║
║ 7. FIE (analytics engine) is READ-ONLY on production data.    ║
║ 8. Every component must support light AND dark mode.           ║
║ 9. Every screen must work at 375px width (iPhone SE).          ║
║ 10. prefers-reduced-motion must be respected everywhere.       ║
╚══════════════════════════════════════════════════════════════════╝
```

## A5. Architectural Decisions (from CEO-Level Plan Review)

The following 11 architectural decisions were made during a rigorous pre-build review. They override any conflicting specification elsewhere in this document. Claude Code MUST implement these decisions — they address critical security vulnerabilities, concurrency bottlenecks, and silent failure modes.

```
╔══════════════════════════════════════════════════════════════════════╗
║                 11 ARCHITECTURAL DECISIONS                          ║
║                 (Override any conflicting spec)                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  DECISION 1: SERVER-SIDE JWT VERIFICATION                           ║
║  The X-User-ID header pattern is ELIMINATED. Every authenticated    ║
║  API request must include an Authorization: Bearer <token> header.  ║
║  FastAPI extracts the Supabase access_token, verifies its signature ║
║  using the Supabase JWT secret, and extracts the user_id from the   ║
║  'sub' claim. This prevents user impersonation attacks.             ║
║                                                                     ║
║  DECISION 2: TASK QUEUE FOR HEAVY WORK (Redis + arq)               ║
║  The 11-swarm chat pipeline takes 10-30 seconds per request. Under  ║
║  50 concurrent users, a single process will queue and timeout. ALL  ║
║  swarm pipeline work (chat, plan generation, bloodwork analysis)    ║
║  runs in a background task queue using Redis + arq. The SSE         ║
║  endpoint polls task results rather than running the pipeline       ║
║  inline. Redis is a REQUIRED infrastructure dependency.             ║
║                                                                     ║
║  DECISION 3: FULL CLIENT-SIDE ARCHITECTURE (No Server Components)  ║
║  ALL React components are client components. No React Server        ║
║  Components. Landing page SEO is handled via static metadata in     ║
║  layout.tsx + pre-rendered HTML. This eliminates the conflict       ║
║  between Next.js App Router server components and Capacitor 8       ║
║  static export.                                                     ║
║                                                                     ║
║  DECISION 4: TASK QUEUE + RENDER CRON FOR BACKGROUND JOBS          ║
║  All scheduled jobs (evening summaries, phase transition checks,    ║
║  FIE extraction, cache refresh, nudge delivery) are triggered by   ║
║  Render Cron Jobs hitting authenticated HTTP endpoints that         ║
║  enqueue work into the same Redis + arq task queue from Decision 2.║
║  One infrastructure, one pattern for all async work.                ║
║                                                                     ║
║  DECISION 5: UNIVERSAL RETRY WRAPPER IN swarm_base.py              ║
║  Every swarm inherits a retry-once-then-fallback pattern from      ║
║  the abstract base class: try the LLM call → validate the output   ║
║  schema → if validation fails, retry once with a stricter prompt → ║
║  if still fails, return a typed per-swarm fallback value. All      ║
║  failures are logged with full context (input, model, error).      ║
║  This addresses 10 unrescued LLM error paths (empty responses,     ║
║  malformed JSON, refusals, validation errors).                     ║
║                                                                     ║
║  DECISION 6: PSEUDONYM LOOKUP ALWAYS RETURNS SAME RESPONSE         ║
║  The GET /auth/lookup endpoint always returns 200 with the email   ║
║  pattern {pseudonym}@users.izana.ai REGARDLESS of whether the      ║
║  pseudonym exists. Login failure is indistinguishable between       ║
║  "wrong pseudonym" and "wrong password." Rate limit: 10 req/min/IP.║
║  This prevents pseudonym enumeration (only ~13,000 combinations).  ║
║                                                                     ║
║  DECISION 7: SERVER-SIDE SIGNUP TRANSACTION                        ║
║  The entire signup flow is a single backend call: POST /auth/signup ║
║  { pseudonym, password, gender, avatar, timezone }. The backend    ║
║  creates the Supabase auth user, inserts the profile row, creates  ║
║  the gamification record, and generates the recovery phrase in a   ║
║  single transaction. If ANY step fails, nothing is created. This   ║
║  eliminates the partial-state bug where auth exists but profile    ║
║  doesn't.                                                          ║
║                                                                     ║
║  DECISION 8: TESTS WRITTEN ALONGSIDE EACH STAGE                   ║
║  Every stage's VERIFY step includes real test files (pytest for    ║
║  backend, Vitest for frontend). Test infrastructure (fixtures,     ║
║  mock Groq client, mock Supabase) is set up in Stage 1. Tests     ║
║  accumulate across stages and catch regressions. Stage 22 focuses  ║
║  on E2E Playwright tests and deployment, NOT unit/integration      ║
║  tests (those are already written by then).                        ║
║                                                                     ║
║  DECISION 9: COMPLIANCE CHECK RUNS BEFORE TOKEN STREAMING          ║
║  The original pipeline streamed tokens (Step 8) BEFORE running     ║
║  the compliance check (Step 9). This meant users could see         ║
║  unchecked medical content. The corrected pipeline order:          ║
║  Swarm 4 generates full response → Swarm 7 checks/modifies it →   ║
║  THEN stream the approved text token-by-token via SSE. The search  ║
║  animation phases cover the additional ~0.5s latency.              ║
║                                                                     ║
║  DECISION 10: CHAT TRACES TABLE FOR OBSERVABILITY                  ║
║  A new chat_traces table logs every swarm call: trace_id,          ║
║  message_id, swarm_id, input_text, output_text, model, tokens_in, ║
║  tokens_out, latency_ms, error, created_at. The swarm_base.py     ║
║  handles tracing automatically. Enables full reconstruction of     ║
║  any chat response for debugging "Izana gave wrong advice" reports.║
║  Also enables token cost tracking per request.                     ║
║                                                                     ║
║  DECISION 11: ENVIRONMENT-VARIABLE FEATURE FLAGS                   ║
║  Add boolean env vars to config.py: FEATURE_BLOODWORK_ENABLED,    ║
║  FEATURE_PARTNER_ENABLED, FEATURE_FIE_ENABLED (already exists),   ║
║  FEATURE_PUSH_ENABLED. API routers check these before processing.  ║
║  Disabled features return human-friendly "Coming soon" messages.   ║
║  This allows fine-grained production control without full rollback.║
║                                                                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

## A6. Engineering Review Decisions (9 Additional)

The following 9 decisions were made during an intensive engineering review. They cover execution-level concerns: resilience, testing strategy, data quality, and performance. Combined with Section A5, there are **20 total architectural decisions**.

```
╔══════════════════════════════════════════════════════════════════════╗
║              9 ENGINEERING REVIEW DECISIONS                         ║
║           (Supplement to A5, same override authority)               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  DECISION 12: UPSTASH REDIS + INLINE FALLBACK                      ║
║  Use Upstash Redis (managed, multi-region, auto-failover) for the  ║
║  task queue. Additionally, if redis.ping() fails, the POST         ║
║  /chat/stream endpoint falls back to running the swarm pipeline    ║
║  INLINE (synchronous, slower, but functional). Background jobs     ║
║  simply skip their run and retry on next cron trigger. This        ║
║  prevents Redis from being a single point of total app failure.    ║
║                                                                     ║
║  DECISION 13: PHASE SKIP WITH CONFIRMATION                         ║
║  Phase transitions allow non-sequential jumps (e.g., Stims →       ║
║  Retrieval, skipping Trigger). If the user selects a non-next      ║
║  phase, show a confirmation: "That skips the trigger phase. Are    ║
║  you sure?" On confirm, auto-create intermediate chapters with     ║
║  status='completed' and summary_text='Phase skipped by user'.      ║
║                                                                     ║
║  DECISION 14: RECOVERY PHRASE REGENERATION                          ║
║  Add POST /recovery/regenerate (User Auth, requires current        ║
║  password). Generates a new recovery phrase, replaces the old      ║
║  hash in DB, returns the new phrase ONCE. Add a "Generate new      ║
║  recovery phrase" button in You tab → Privacy & data. Prevents     ║
║  permanent account loss if the user loses their original phrase.   ║
║                                                                     ║
║  DECISION 15: COMPLETE GAMIFICATION POINT SCHEDULE                  ║
║  Points: Meal logged = 10, Exercise done = 15, Meditation done =   ║
║  10, Check-in = 10, Streak bonus = 5/day, All-5-done bonus = 10.  ║
║  Levels: L1 Beginner (0), L2 Committed (100), L3 Dedicated (300), ║
║  L4 Warrior (600), L5 Champion (1000). Badge criteria stored as    ║
║  JSONB: {"type":"streak","threshold":7}. See Section A6.1 below.  ║
║                                                                     ║
║  DECISION 16: CHAT MESSAGE LIMIT = 2000 CHARACTERS                 ║
║  The original 500-char limit is too short for fertility questions   ║
║  that include medication names, dosages, and bloodwork values.     ║
║  Increase to 2000 chars. Frontend shows a live character counter.  ║
║  Backend validates in sanitize_input().                             ║
║                                                                     ║
║  DECISION 17: HUMAN-READABLE SWARM FILE NAMES                      ║
║  Rename all swarm files from numeric (swarm_0_polyglot.py) to     ║
║  descriptive (translator.py, gatekeeper.py, clinical_brain.py,    ║
║  response_curator.py, bloodwork_extractor.py, bloodwork_analyser.py║
║  bloodwork_curator.py, compliance_checker.py, gap_detector.py,    ║
║  context_builder.py, sentiment_analyser.py). Each class keeps its ║
║  swarm_id field as "swarm_0_polyglot" etc. for trace compatibility.║
║                                                                     ║
║  DECISION 18: TYPE-SAFE i18n                                       ║
║  en.ts defines the base type: export const en = {...} as const;    ║
║  export type TranslationKeys = typeof en. All other translation    ║
║  files must satisfy TranslationKeys. TypeScript catches missing    ║
║  keys at BUILD time, preventing blank text in non-English UIs.     ║
║                                                                     ║
║  DECISION 19: DETERMINISTIC MOCK GROQ CLIENT FOR TESTS             ║
║  Create tests/mocks/mock_groq.py with fixture responses per swarm: ║
║  gatekeeper returns {safe:true}, curator returns a fixed response, ║
║  polyglot returns input unchanged. All tests run without API calls.║
║  Tests are deterministic, fast, and cover retry/fallback paths.    ║
║                                                                     ║
║  DECISION 20: 90-DAY CHAT TRACES RETENTION                         ║
║  chat_traces grows at ~2.4M rows/month (~10GB/month with TEXT     ║
║  columns). A weekly data lifecycle job deletes rows older than 90  ║
║  days. If deeper forensics are needed, export to cold storage      ║
║  before deletion. Add to the Render Cron schedule (Sunday 2am UTC).║
║                                                                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

### A6.1 Gamification Point Schedule (Decision 15)

```
╔══════════════════════════════════════════════════════════════════════╗
║                    GAMIFICATION POINT SCHEDULE                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  POINTS PER ACTION:                                                 ║
║  ┌──────────────────────┬────────┬──────────────────────────────┐   ║
║  │ Action               │ Points │ Notes                        │   ║
║  ├──────────────────────┼────────┼──────────────────────────────┤   ║
║  │ Meal logged (each)   │ 10     │ Max 3 per day (30 total)     │   ║
║  │ Exercise completed   │ 15     │ Must complete >50% of content│   ║
║  │ Meditation completed │ 10     │ Must complete >90% of content│   ║
║  │ Daily check-in       │ 10     │ Once per day only            │   ║
║  │ Streak bonus (daily) │ 5      │ Added on top of check-in pts │   ║
║  │ All-5-done bonus     │ 10     │ 3 meals + exercise + medit.  │   ║
║  │ Bloodwork upload     │ 25     │ Per upload, max 1/week       │   ║
║  │ Partner connected    │ 50     │ One-time                     │   ║
║  └──────────────────────┴────────┴──────────────────────────────┘   ║
║                                                                     ║
║  MAX DAILY POINTS: 30 + 15 + 10 + 10 + 5 + 10 = 80                ║
║                                                                     ║
║  LEVEL THRESHOLDS:                                                  ║
║  ┌─────────┬──────────────┬────────────┬───────────────────────┐   ║
║  │ Level   │ Name         │ Points     │ Days at max (~80/day) │   ║
║  ├─────────┼──────────────┼────────────┼───────────────────────┤   ║
║  │ 1       │ Beginner     │ 0          │ 0                     │   ║
║  │ 2       │ Committed    │ 100        │ ~2 days               │   ║
║  │ 3       │ Dedicated    │ 300        │ ~4 days               │   ║
║  │ 4       │ Warrior      │ 600        │ ~8 days               │   ║
║  │ 5       │ Champion     │ 1000       │ ~13 days              │   ║
║  │ 6       │ Radiant      │ 2000       │ ~25 days              │   ║
║  │ 7       │ Luminous     │ 4000       │ ~50 days              │   ║
║  └─────────┴──────────────┴────────────┴───────────────────────┘   ║
║                                                                     ║
║  BADGE CRITERIA (badges.criteria JSONB schema):                     ║
║  ┌────────────────────┬──────────────────────────────────────────┐  ║
║  │ Badge              │ Criteria JSON                            │  ║
║  ├────────────────────┼──────────────────────────────────────────┤  ║
║  │ First Steps        │ {"type":"checkin","count":1}             │  ║
║  │ Wellness Warrior   │ {"type":"streak","threshold":7}          │  ║
║  │ Two Week Titan     │ {"type":"streak","threshold":14}         │  ║
║  │ Monthly Master     │ {"type":"streak","threshold":30}         │  ║
║  │ Iron Will          │ {"type":"streak","threshold":60}         │  ║
║  │ Century Club       │ {"type":"streak","threshold":100}        │  ║
║  │ Nutrition Pro      │ {"type":"meal_adherence","pct":0.9,      │  ║
║  │                    │  "days":7}                               │  ║
║  │ Movement Maven     │ {"type":"exercise_streak","threshold":7} │  ║
║  │ Calm Mind          │ {"type":"meditation_streak","threshold":7}│  ║
║  │ Knowledge Seeker   │ {"type":"questions_asked","count":20}    │  ║
║  │ Blood Detective    │ {"type":"bloodwork_uploads","count":3}   │  ║
║  │ Together Strong    │ {"type":"partner_connected"}             │  ║
║  │ Perfect Day        │ {"type":"all_5_done","count":1}          │  ║
║  │ Perfect Week       │ {"type":"all_5_done","count":7}          │  ║
║  └────────────────────┴──────────────────────────────────────────┘  ║
║                                                                     ║
║  GRIEF MODE: All point awards suppressed. Streak hidden. Badges    ║
║  hidden. Actions logged but NOT scored. On resumption: streak      ║
║  resets to 1 (no "lost your streak" message), points resume.       ║
╚══════════════════════════════════════════════════════════════════════╝
```

### A6.2 Obvious Fixes from Engineering Review

These fixes do not require decisions — they are implementation requirements:

```
╔══════════════════════════════════════════════════════════════════════╗
║              IMPLEMENTATION REQUIREMENTS (No Decision Needed)       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  SECURITY:                                                          ║
║  • Account lockout: After 5 failed login attempts for a pseudonym  ║
║    within 15 minutes, block further attempts. Store counter in     ║
║    Redis. Return "Too many login attempts. Try again in 15 min."   ║
║  • Pseudonym keyspace expansion: 24 adjectives × 24 nouns ×       ║
║    3-digit numbers (100-999) = 518,400 combinations. Current       ║
║    12×12×90 = 12,960 is too small for 5,000+ users.               ║
║  • Recovery phrase input validation: Validate exact format          ║
║    (XXXX-XXXX-XXXX-XXXX, 19 chars) before hashing. Prevents DoS. ║
║  • Partner invite codes: Use secrets.token_urlsafe(16) — NOT UUID. ║
║    Short, shareable, 128-bit random.                               ║
║                                                                     ║
║  DATABASE INDEXES:                                                  ║
║  • approval_queue: CREATE INDEX idx_approval_queue_status_priority  ║
║    ON approval_queue(status, priority, created_at);                 ║
║  • meal_logs: ADD UNIQUE constraint on (user_id, meal_type,        ║
║    logged_at::date) to prevent double-logging via offline sync.    ║
║  • chat_logs.message_id: Add index if TEXT type is kept.           ║
║                                                                     ║
║  PERFORMANCE:                                                       ║
║  • Evening summary: Batch DB queries per data type (one query for  ║
║    all users' meals, one for activities, etc.), NOT per-user.      ║
║  • RAG embedding: Parallelize 3 query embeddings with              ║
║    asyncio.gather() — 3x speedup on embedding step.               ║
║  • Landing page cache: Process 11 languages in parallel (3-4      ║
║    concurrent). Set cron timeout to 15 minutes (33 pipeline runs). ║
║  • Swarm prompts: Cache with @alru_cache(ttl=3600) in worker.     ║
║    Invalidate on admin prompt update.                              ║
║  • Supabase connection pool: Use PgBouncer port 6543 in prod.     ║
║  • SWR cache config per endpoint:                                   ║
║    - /profile: 5-minute cache                                      ║
║    - /chapters/active: 30-second auto-refresh                      ║
║    - /plan-status: 30-second polling (no SWR cache)                ║
║    - /content/library: 1-hour cache                                ║
║  • Media player: Debounce position saves to 60 seconds (not 30).  ║
║  • Offline IndexedDB: Limit to 5MB, evict oldest messages first.  ║
║                                                                     ║
║  CODE QUALITY:                                                      ║
║  • Feature flag as FastAPI dependency, not per-route check:         ║
║    bloodwork_router = APIRouter(                                    ║
║      dependencies=[Depends(require_feature("bloodwork"))]           ║
║    )                                                                ║
║  • Redis stream TTL: await redis.expire(f"chat:{task_id}", 300)   ║
║    Auto-delete orphaned streams after 5 minutes.                   ║
║  • User deletion mid-chat: Worker catches ForeignKeyViolation and  ║
║    silently discards the result if user no longer exists.           ║
║  • Nutritionist edit auto-save: Modifications stored in            ║
║    sessionStorage on every keystroke. Persisted on submit.         ║
║  • HEIC support: Add pillow-heif to pip install. Accept HEIC in   ║
║    file type validation alongside PDF, JPG, PNG.                   ║
║  • Pagination on /chapters/{id}/messages: Add ?page=1&per_page=100║
║    with cursor-based pagination for large chapters.                ║
║  • Chat message limit: Validate max 2000 chars (Decision 16) in   ║
║    both frontend (live counter) and backend (sanitize_input).      ║
║  • Embedding dimension assertion: assert len(embedding) == 384    ║
║    before every storage. Prevents silent search corruption.        ║
║                                                                     ║
║  DATA FLOW:                                                         ║
║  • Weekly group boundary: ISO weeks (Monday-Sunday) adjusted to   ║
║    user timezone. Week 1 starts on Monday of chapter started_at.   ║
║  • Mood trend calculation: Linear regression slope over last 14    ║
║    days of emotion_logs.mood (encoded: great=5, good=4, okay=3,   ║
║    low=2, struggling=1). Positive=improving, near-zero=stable.    ║
║  • Plan meal variety: nutrition_plan.meals stores 5-7 options per  ║
║    meal_type. Frontend selects: options[day_count % options.length].║
║    No backend call needed for daily rotation.                      ║
║  • Content contraindication: Filter by phase (not health conds).  ║
║    treatment_phases @> ARRAY[phase] AND intensity <= fitness_level.║
║  • Grief mode Day 0-2: Plan card hidden entirely. Day 3+: only    ║
║    shown if user opts in via "Show me a recovery plan."            ║
║  • Search algorithm (Journey tab): Supabase full-text search      ║
║    (tsvector) on chat_logs.content filtered by user_id.            ║
║  • DPO training_eligible: Default true. Admin can set false.      ║
║                                                                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

# SECTION B: HOW THE APP LOOKS AND FEELS

## B1. Design Philosophy: Luxury Wellness

Izana should feel like a luxury wellness brand, not a medical app. Think Headspace meets a high-end fertility clinic's private waiting room. Warm, calm, confident. Never clinical, never cold, never generic.

**Three words:** Warm. Breathing. Personal.

- **Warm:** Warm paper backgrounds (never pure white), warm text (never pure black), bronze accents
- **Breathing:** Generous whitespace, one interactive element visible at a time, smart collapsing
- **Personal:** "Your stims · day 8" not "Phase: Stims". Every piece of copy uses "you/your"

## B2. Color Palette

### Light Mode
| Token | Value | Use |
|-------|-------|-----|
| `--brand-primary` | `#4A3D8F` | Deep amethyst. Buttons, active states, user message bubbles |
| `--brand-secondary` | `#C4956A` | Warm bronze. Streaks, achievements, premium accents |
| `--brand-accent` | `#7BA68E` | Sage green. Success states, completed items, health indicators |
| `--canvas-base` | `#FAF9F7` | Warm paper. Main background (NOT pure white) |
| `--canvas-elevated` | `#FFFFFF` | Cards, modals, input fields |
| `--canvas-sunken` | `#F3F1ED` | Izana's message bubbles, secondary backgrounds |
| `--text-primary` | `#2A2433` | Warm near-black. Headings, body text |
| `--text-secondary` | `#6B6278` | Warm grey. Secondary info, labels |
| `--text-tertiary` | `#9B93A8` | Muted lavender. Timestamps, hints, placeholders |
| `--border-default` | `#E8E4DF` | Warm border. Cards, dividers, inputs |
| `--brand-primary-bg` | `#EEEDFE` | Light amethyst. Selected states, active tab pills |

### Dark Mode
| Token | Value | Use |
|-------|-------|-----|
| `--canvas-base` | `#1A171F` | Deep warm charcoal (NOT pure black) |
| `--canvas-elevated` | `#242029` | Cards, modals |
| `--canvas-sunken` | `#1E1B24` | Izana's message bubbles |
| `--brand-primary` | `#8B7FC7` | Lighter amethyst for contrast |
| `--text-primary` | `#F0EDE8` | Warm off-white |
| `--text-secondary` | `#A09BAA` | Muted |
| `--border-default` | `#3A3540` | Subtle border |

### Semantic Colors
| Token | Value | Use |
|-------|-------|-----|
| `--success` | `#3D7A56` | Completed items, positive indicators |
| `--warning` | `#B8860B` | Deadlines, urgent items |
| `--error` | `#C75454` | Errors, critical alerts, logout |
| `--celebration-primary` | `#4A3D8F` | Confetti color 1 |
| `--celebration-secondary` | `#C4956A` | Confetti color 2 |

### Theme Switching
- Toggle: `localStorage["izana_theme"]` = "system" | "light" | "dark"
- Apply `data-theme` attribute on `<html>` element
- Default: "system" (follows OS preference via `prefers-color-scheme`)

## B3. Typography

| Role | Font | Fallback | Use |
|------|------|----------|-----|
| Body / UI | Inter | system-ui, sans-serif | All text, inputs, labels, messages |
| Display / Headers | DM Serif Display | Georgia, serif | Landing page headline, section headers in Journey tab |
| Mono / Data | JetBrains Mono | monospace | Recovery phrase, biomarker values, stats |

**Sizes:**
- Body: 14px (mobile), 16px (desktop). Line-height: 1.5
- Chat messages: 13px (mobile), 14px (desktop). Line-height: 1.5
- Captions/labels: 10–11px
- Headers: 15–17px (in-app), 20–24px (landing page)
- **MINIMUM 16px on all input fields** (prevents iOS zoom on focus)

**Font loading:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=DM+Serif+Display&family=JetBrains+Mono:wght@400;500&display=swap');
```

## B4. Motion & Animation

### Easing Functions
```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);         /* Primary — most transitions */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);   /* Celebrations only — bounce */
```

### Duration Scale
```css
--duration-instant: 100ms;   /* Opacity changes, color transitions */
--duration-fast: 150ms;      /* Button states, icon changes */
--duration-normal: 250ms;    /* Card entrances, section reveals */
--duration-slow: 400ms;      /* Page transitions, accordions */
--duration-celebration: 600ms; /* Confetti, milestone animations */
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  /* Exception: opacity fades still work (they don't cause motion sickness) */
  .fade-transition {
    transition-duration: 150ms !important;
  }
}
```

### Specific Animations (Framer Motion)

**Card entrance (every chat card):**
```tsx
<motion.div
  initial={{ opacity: 0, y: 12 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
/>
```

**Staggered plan items (breakfast → lunch → dinner → exercise → meditation):**
```tsx
{items.map((item, i) => (
  <motion.div
    key={item.id}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: i * 0.1, duration: 0.25 }}
  />
))}
```

**Mood emoji bounce on select:**
```tsx
<motion.button
  whileTap={{ scale: 1.3 }}
  transition={{ type: "spring", stiffness: 400, damping: 15 }}
/>
```

**Check-in collapse after submission:**
```tsx
<motion.div
  animate={{ height: isCollapsed ? 36 : "auto", opacity: isCollapsed ? 0.6 : 1 }}
  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
/>
```

**Accordion expand/collapse (weekly groups):**
```tsx
<motion.div
  animate={{ height: isOpen ? "auto" : 0 }}
  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
  style={{ overflow: "hidden" }}
/>
```

**Bottom-sheet modal (signup):**
```tsx
<motion.div
  initial={{ y: "100%" }}
  animate={{ y: 0 }}
  exit={{ y: "100%" }}
  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
/>
```

**Confetti (canvas-confetti):**
```tsx
// Normal celebration (plan approved, badge earned, streak milestone)
confetti({
  particleCount: 80,
  spread: 70,
  colors: ['#4A3D8F', '#C4956A', '#E8DFF0'],
  origin: { y: 0.6 },
  gravity: 1.2,
});

// Positive pregnancy outcome ONLY (bigger celebration)
confetti({
  particleCount: 150,
  spread: 90,
  colors: ['#4A3D8F', '#C4956A', '#7BA68E', '#E8DFF0'],
  origin: { y: 0.6 },
  gravity: 1.0,
});
```

**Streak fire pulse (chapter header):**
```css
.streak-fire {
  animation: streak-pulse 2s ease-in-out infinite;
}
@keyframes streak-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
```

**Grief mode — disable all celebrations:**
```css
[data-grief-mode="true"] {
  --brand-primary: #6B6278;
  --brand-secondary: #9B93A8;
  .streak-indicator,
  .points-display,
  .badge-celebration { display: none; }
  .celebration-overlay { display: none !important; }
}
```

## B5. Navigation: 3 Tabs

The app has a bottom navigation bar with exactly 3 tabs. **Text only — no icons.**

| Tab | Label | Content | Default |
|-----|-------|---------|---------|
| 1 | **Today** | Active phase chat view. This is the main screen. | ✅ Always default |
| 2 | **Journey** | Timeline of past phases, bloodwork upload/results, doctor report sharing, mood trends | |
| 3 | **You** | Profile (avatar, pseudonym, stats), partner, content library, achievements, settings, privacy, logout | |

**Active tab styling:**
```css
.tab-active {
  background: var(--brand-primary-bg); /* #EEEDFE */
  border-radius: 16px;
  padding: 4px 16px;
  color: var(--brand-primary);
  font-weight: 500;
}
.tab-inactive {
  color: var(--text-tertiary);
  font-size: 9px;
}
```

**There are NO icons in the bottom nav.** Just the three words. The active one gets a pill background. This is intentional — it's warmer and less clinical than icon-based navigation.

---

# SECTION C: COMPLETE USER JOURNEY (Every Screen)

This section describes every screen the user sees, in order, from opening the app for the first time to their daily rhythm. Each screen includes exact layout, microcopy, and interaction details.

## C1. Landing Page (Screen 1)

**Concept:** The app IS the chat from the very first pixel. There is no separate "landing page." The user opens Izana and sees a chat interface where Izana introduces herself.

**Layout (within first 100vh — no scrolling needed):**

```
┌─────────────────────────────────┐
│  [✦ izana]              [EN ▾]  │  ← Top bar: logo + language
├─────────────────────────────────┤
│                                 │
│  ✦  "Your fertility journey     │  ← Izana's first message (DM Serif)
│     is unique. Your support     │
│     should be too."             │
│                                 │
│     I'm Izana — I create        │  ← Body text (Inter)
│     personalised nutrition,     │
│     exercise and meditation     │
│     plans, reviewed by a real   │
│     nutritionist, that adapt    │
│     to every phase of your      │
│     treatment.                  │
│                                 │
│     Try me — ask anything ↓     │
│                                 │
│  [What to eat during IVF?]      │  ← Suggested questions (tappable)
│  [Is my AMH normal?]            │
│  [Help with TWW anxiety]        │
│                                 │
│  [Anonymous] [Nutritionist      │  ← Trust badges (compact pills)
│   reviewed] [11 languages]      │
│                                 │
├─────────────────────────────────┤
│ [Start my journey—free & anon]  │  ← Primary CTA button
│ [Ask about your fertility...]▶  │  ← Chat input (works for preview)
│ Already have an account? Log in │  ← Text link
├─────────────────────────────────┤
│     Today    Journey    You     │  ← Bottom nav (greyed out pre-auth)
└─────────────────────────────────┘
```

**Interactions:**
- Tapping a suggested question → runs the preview chat pipeline (Swarm 0→1→3→4→7, rate limited 1 per IP per 10 minutes)
- Typing in chat input → same preview pipeline
- After receiving a response, the CTA changes to "Want advice personalised to YOUR treatment? Start my journey"
- Tapping "Start my journey" → signup modal slides up from bottom
- Tapping "Log in" → login modal slides up from bottom

**Microcopy:**
- CTA button: "Start my journey — free & anonymous"
- Chat input placeholder: "Ask about your fertility journey..."
- Trust badges: "Anonymous" · "Nutritionist reviewed" · "11 languages"
- Login link: "Already have an account? Log in"

## C2. Signup Modal (Screen 2)

**Concept:** A bottom-sheet modal that slides up over the dimmed landing page chat. Avatar + name on one row to save space. One screen, no scrolling.

**Layout:**

```
┌─────────────────────────────────┐
│  ░░░░ (dimmed chat behind) ░░░░ │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│                                 │
├──── ▬▬▬ drag handle ▬▬▬ ────────┤  ← Bottom sheet starts here
│                                 │
│  [🦋 avatar]  BraveOcean42      │  ← Avatar (52px, selected) + name
│               ↻ new             │     Tap avatar = cycle options
│                                 │
│  🦋 🌸 🌟 🌹 💎 🌺             │  ← Avatar row (horizontal scroll)
│                                 │
│  Sex:  [F] [M]   Password:     │  ← Side by side
│                   [••••••••]    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Create my account       │    │  ← Primary button
│  └─────────────────────────┘    │
│  Anonymous · Terms & Privacy    │  ← Caption
└─────────────────────────────────┘
```

**Details:**
- Pseudonym auto-generated: {Adjective}{Noun}{3-digit number} (expanded keyspace per A6.2)
  - Adjectives (24): Hopeful, Radiant, Brave, Serene, Vibrant, Gentle, Resilient, Luminous, Graceful, Steadfast, Tranquil, Fierce, Bright, Joyful, Calm, Warm, Bold, Pure, Free, Noble, Swift, Wise, True, Kind
  - Nouns (24): Sunrise, Bloom, Journey, River, Meadow, Horizon, Garden, Aurora, Coral, Haven, Ocean, Willow, Phoenix, Ember, Crystal, Breeze, Harbor, Summit, Valley, Lotus, Petal, Starlight, Moonbeam, Cascade
  - Numbers: 100-999 (3-digit)
  - Total combinations: 24 × 24 × 900 = **518,400** unique pseudonyms
  - Examples: BraveOcean427, HopefulBloom173, LuminousRiver831
- Tapping "new" regenerates the pseudonym
- Tapping the large avatar cycles through options OR tap one in the row below
- Avatars: 🦋 🌸 🌟 🌹 💎 🌺 🌷 🍃 ✨ 🌙 (each with a gradient background)
- Sex selector: "F" and "M" compact toggle (explains: "for bloodwork ranges")
- Password: min 8 chars, show/hide toggle
- "Create my account" → Creates Supabase user with `{pseudonym}@users.izana.ai`
- On success → modal dismisses → recovery phrase modal appears

**Signup Flow (Decision 7 — Server-Side Transaction):**
```
1. Frontend calls: POST /api/v1/auth/signup {
     pseudonym, password, gender, avatar, timezone
   }
2. Backend (in a single transaction):
   a. Create Supabase auth user: supabase.auth.admin.create_user({ email: `${pseudonym}@users.izana.ai`, password })
   b. Insert profile row (pseudonym, gender, avatar, timezone)
   c. Create gamification record (0 points, 0 streak)
   d. Generate recovery phrase (16-char: XXXX-XXXX-XXXX-XXXX)
   e. Store SHA-256(phrase + salt) in recovery_phrases table
3. If ANY step fails → roll back everything (delete auth user if created)
4. On success → return { user_id, access_token, recovery_phrase }
5. Frontend shows recovery phrase to user once
6. Frontend stores the access_token for subsequent API calls

IMPORTANT: The recovery phrase is returned in the signup response
and NEVER stored in plaintext. Only the SHA-256 hash is persisted.
```

## C3. Recovery Phrase (Screen 3)

**Layout:**

```
┌─────────────────────────────────┐
│              🔑                  │
│   Save your recovery phrase     │
│                                 │
│   Since Izana is anonymous,     │
│   this is your only way back    │
│   in. Keep it somewhere safe.   │
│                                 │
│  ┌───────────────────────────┐  │
│  │   ABCD-EFGH-IJKL-MNOP    │  │  ← Monospace, large, centered
│  └───────────────────────────┘  │
│                                 │
│  [  Copy to clipboard  ]        │  ← Secondary button
│                                 │
│                                 │
│  ┌─────────────────────────┐    │
│  │ I've saved it — continue │    │  ← Primary button
│  └─────────────────────────┘    │
└─────────────────────────────────┘
```

- Recovery phrase is generated once and shown once
- SHA-256 hash with salt stored in DB — the phrase itself is never stored
- "Copy to clipboard" → toast: "Copied ✓"
- "I've saved it — continue" → enter the chat for onboarding

## C4. Conversational Onboarding (Screens 4–6)

**Concept:** Onboarding happens INSIDE the chat. The user is now in the "Today" tab with header "Getting started." Instead of 14 individual questions, we group them into 3 themed rounds.

**Why 3 rounds:** 14 individual conversational messages feels tedious. 3 grouped cards feel like a quick quiz. Each round is one multi-select card with 3–5 questions. Total: ~13 taps across 3 rounds (under 3 minutes).

**IMPORTANT: No mood check at signup.** The first mood check happens the next morning at the user's timezone-appropriate time. On signup day, we just collect profile info.

### Round 1: Treatment & You

```
┌─────────────────────────────────┐
│  Getting started                │  ← Header (no phase yet)
│  ─────────────── 1 of 3        │  ← Progress bar
├─────────────────────────────────┤
│                                 │
│  ✦  Round 1: Your treatment     │  ← Izana message
│                                 │
│     Quick taps — this helps     │
│     personalise everything.     │
│                                 │
│  ┌─────────────────────────┐    │  ← Card with grouped questions
│  │ Treatment type           │    │
│  │ [IVF] [IUI] [Natural]   │    │
│  │ [Egg freezing] [Explore] │    │
│  │                          │    │
│  │ Where are you now?       │    │  ← Appears after treatment tap
│  │ [Preparing] [Stims]      │    │     Options vary by treatment
│  │ [Retrieval] [TWW]        │    │
│  │                          │    │
│  │ What day? (if stims)     │    │  ← Appears conditionally
│  │ [Day picker: 1-15+]      │    │
│  │                          │    │
│  │ Age range                │    │
│  │ [18-25] [26-30] [31-35]  │    │
│  │ [36-40] [41+]            │    │
│  │                          │    │
│  │     [Next round →]       │    │
│  └─────────────────────────┘    │
│                                 │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

After Round 1 completes:
- Izana responds: "IVF stims day 8 — you're in the home stretch. Let me learn a bit more about your lifestyle."
- Header updates to "Your stims · day 8"
- Progress bar moves to 2 of 3

### Round 2: Lifestyle

```
│  ✦  Round 2: Your lifestyle     │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Health conditions        │    │
│  │ [PCOS] [Endo] [Thyroid]  │    │
│  │ [Diabetes] [None]        │    │
│  │                          │    │
│  │ Activity level           │    │
│  │ [Low] [Moderate] [Active]│    │
│  │                          │    │
│  │ Smoking                  │    │
│  │ [Never] [Former] [Yes]   │    │
│  │                          │    │
│  │ Alcohol                  │    │
│  │ [None] [Occasional]      │    │
│  │ [Moderate]               │    │
│  │                          │    │
│  │ Sleep                    │    │
│  │ [<6h] [6-7h] [7-8h]     │    │
│  │ [8-9h] [>9h]            │    │
│  │                          │    │
│  │ Stress                   │    │
│  │ [Rarely] [Sometimes]     │    │
│  │ [Often] [Always]         │    │
│  │                          │    │
│  │     [Next round →]       │    │
│  └─────────────────────────┘    │
```

After Round 2: "Great — these details help me create the right nutrition balance for you. One more round about food preferences."

### Round 3: Food & Exercise Preferences

```
│  ✦  Round 3: Food & movement    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Allergies                │    │
│  │ [Dairy] [Gluten] [Nuts]  │    │
│  │ [Soy] [Eggs] [None]     │    │
│  │                          │    │
│  │ Dietary style            │    │
│  │ [Vegetarian] [Vegan]     │    │
│  │ [Pescatarian] [Keto]     │    │
│  │ [No restrictions]        │    │
│  │                          │    │
│  │ Cuisines you love        │    │
│  │ [Mediterranean] [Indian] │    │
│  │ [Asian] [Latin]          │    │
│  │ [Middle Eastern]         │    │
│  │ [Western]                │    │
│  │                          │    │
│  │ Exercise preferences     │    │
│  │ [Yoga] [Walking]         │    │
│  │ [Pilates] [Swimming]     │    │
│  │ [Light gym] [Stretching] │    │
│  │                          │    │
│  │ Exercise time per day    │    │
│  │ [10 min] [20 min]        │    │
│  │ [30 min] [45 min+]       │    │
│  │                          │    │
│  │  [Finish setup ✓]        │    │
│  └─────────────────────────┘    │
```

## C5. Grand Reveal (Screen 7)

After Round 3 completes, confetti fires and Izana shows the grand reveal directly in the chat:

```
┌─────────────────────────────────┐
│  Your stims · day 8     🔥 1   │  ← Header is now fully active
├─────────────────────────────────┤
│                                 │
│  (onboarding messages above,    │
│   collapsed to summary line)    │
│                                 │
│  ✦  You're all set,             │  ← Izana's grand reveal message
│     BraveOcean42 ✨              │
│                                 │
│     I'm creating your plan      │
│     now — a nutritionist will   │
│     review it. I'll let you     │
│     know the moment it's ready. │
│                                 │
│     In the meantime, I'm here   │
│     for anything you need.      │
│                                 │
│  [🩸 Upload bloodwork]          │  ← Immediate action buttons
│  [🧘 Try a meditation]          │
│  [What to expect in stims?]     │
│                                 │
├─────────────────────────────────┤
│ [Ask anything about your        │  ← Chat input with shadow text
│  fertility journey...]       ▶  │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

**What happens in the background at this moment:**
1. Profile is saved with all wellness data
2. Cycle is created (treatment_type, started_at)
3. First chapter/phase record created (phase from onboarding, day from user input)
4. Treatment journey created
5. AI plan generation triggered → queued in approval_queue with priority="normal"
6. Nutritionist notified (push + email)
7. User gamification record created (0 points, 1 streak)

## C6. The Gap Period (Hours 0–24)

Between signup and plan approval, the user has a functional chatbot but no meal plan yet.

**What the user CAN do:**
- Ask any fertility question → full swarm pipeline runs
- Upload bloodwork → get biomarker analysis
- Browse content library (meditation, exercise)
- Play a meditation directly from the suggestion chip

**What the user CANNOT see:**
- Any specific meal recommendations (the plan isn't approved yet)
- The "Your day" plan card doesn't appear until the plan is approved

**What the user sees instead:**
```
✦  While your plan is being prepared, here are some
   general stims-day tips:

   • Stay hydrated — aim for 2–3 litres of water
   • Protein-rich foods support follicle development
   • Gentle movement like walking is ideal right now
   • Avoid high-impact exercise during stims

   Your personalised plan will be much more specific
   to your preferences. I'll let you know as soon as
   it's ready!

   [🧘 Try the stims visualisation (10 min)]
```

**Plan status (if user asks "where's my plan?"):**
```
✦  Your plan is currently being reviewed by our
   nutrition team. This usually takes a few hours.
   I'll notify you the moment it's ready!
```

## C7. Plan Delivery (Screen 8)

When the nutritionist approves the plan, the user gets a push notification. Opening the app shows:

```
┌─────────────────────────────────┐
│  Your stims · day 8     🔥 1   │
├─────────────────────────────────┤
│                                 │
│  ✦  Your personalised plan is   │  ← Celebration message
│     ready! 🎉                   │
│                                 │
│     Your nutritionist reviewed  │
│     and approved a plan for     │
│     your IVF stims, dairy-free  │
│     Mediterranean preferences,  │
│     and moderate activity level.│
│                                 │
│  ┌─────────────────────────┐    │  ← Plan card (tabbed)
│  │ [Nutrition] Exercise     │    │
│  │           Meditation     │    │
│  │                          │    │
│  │ 🌅 Avocado toast + eggs  │    │     Breakfast (active — next action)
│  │    folate-rich · protein │    │
│  │              [Done]      │    │
│  │                          │    │
│  │ ☀️ Salmon quinoa bowl     │    │     Lunch (dimmed — upcoming)
│  │    omega-3 · anti-inflam │    │
│  │                          │    │
│  │ 🌙 Bone broth + sweet    │    │     Dinner (dimmed)
│  │    potato                │    │
│  │    collagen · gentle     │    │
│  └─────────────────────────┘    │
│                                 │
├─────────────────────────────────┤
│ [Ask anything...]            ▶  │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

**Plan card details:**
- 3 tabs: Nutrition | Exercise | Meditation
- Nutrition tab: shows today's meals with brief nutritional reason
- Exercise tab: shows the assigned video with [▶ Play] button
- Meditation tab: shows the assigned audio with [▶ Play] button
- Each item has a "Done" button (one tap to mark complete)
- Progress bar at bottom: "0 of 5 done" with a thin line that fills as items complete

## C8. Daily Morning Flow (Screen 9 — the core loop)

Every morning, when the user opens the app, they see:

```
┌─────────────────────────────────┐
│  Your stims · day 9     🔥 2   │
├─────────────────────────────────┤
│                                 │
│  yesterday · 🙂 · 3/4 done  ▸  │  ← Collapsed yesterday
│                                 │
│        today · day 9            │  ← Day marker
│                                 │
│  ✦  Good morning ✨              │  ← Izana's greeting
│     Day 9 — you might hear     │
│     about trigger timing soon.  │
│     How are you feeling?        │
│                                 │
│  [😊] [🙂] [😐] [😢]           │  ← Mood: 1 tap. That's it.
│  tap how you feel               │
│                                 │
├─────────────────────────────────┤
│ [Ask anything...]            ▶  │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

**After tapping a mood emoji:**

1. Izana responds conversationally: "Feeling good — that's great for day 9! 🙂"
2. Optional "+log symptoms" link appears below response
3. "Your day" plan card slides in below Izana's response
4. The plan shows the NEXT action prominently, others dimmed

**Throughout the day:**
- As user marks items "Done" → toast: "Breakfast logged ✓ +10 points"
- Completed items collapse/dim
- User can ask questions at any time → conversation flows below the plan
- When user sends a message, the morning section collapses to: "morning · 🙂 good · 2/4 done ▸"
- Conversation takes over the screen

**Evening (8-9pm, timezone-adjusted):**
Izana sends the evening summary:

```
✦  Beautiful day, BraveOcean42 ✨

┌─────────────────────────────┐
│ day 9 — done                │
│                             │
│ Check-in     great 😊 ✓     │
│ Meals        3/3 ✓          │
│ Yoga         20 min ✓       │
│ Meditation   skipped        │
│                             │
│ +55 points   🔥 8-day streak │
└─────────────────────────────┘

Try the 10-min visualisation before bed —
it might help with the trigger timing
nerves. Sleep well ❤️
```

## C9. Phase Transition (Screen 10)

When the user approaches the end of a phase (at ~80% of expected duration), Izana asks conversationally:

```
✦  Day 10 — many people get their trigger
   shot around now. Any news from your
   clinic today?

   [Yes, I've had my trigger shot]
   [Not yet, still stimming]
   [I'm not sure]
```

If user confirms transition:
1. Current phase chapter closes (summary generated)
2. New phase chapter opens (header updates: "Your trigger · day 1")
3. New plan generation triggered → nutritionist queue (URGENT_PHASE_CHANGE priority)
4. Interim tips shown while new plan is reviewed
5. Toast: "Moving to your trigger phase ✨"

## C10. Journey Tab (Screen 11)

```
┌─────────────────────────────────┐
│  Your journey                   │  ← Header
├─────────────────────────────────┤
│                                 │
│  [🩸 Bloodwork] [📊 Trends]     │  ← Quick action buttons
│  [🩺 Doctor]                    │
│                                 │
│  IVF CYCLE 1                    │  ← Cycle label
│                                 │
│  ● Stims           day 10 →    │  ← Active (purple dot, purple border)
│    Mar 13 — present             │
│    🔥 8  mood: good  85%        │
│                                 │
│  ● Baseline         14 days ✓  │  ← Complete (green dot)
│    Feb 27 — Mar 12              │
│                                 │
│  ● Preparing        10 days ✓  │
│    Feb 17 — Feb 26              │
│                                 │
│  ● Getting started         ✓   │
│    Feb 16                       │
│                                 │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

- Tapping a past phase → opens it in read-only mode (all messages visible, no input)
- Tapping "Bloodwork" → bloodwork upload + results view
- Tapping "Trends" → mood/emotion charts over time
- Tapping "Doctor" → share modal for provider portal

## C11. You Tab (Screen 12)

```
┌─────────────────────────────────┐
│  [🦋] BraveOcean42              │  ← Avatar + name
│       IVF · Cycle 1 · Level 2  │
├─────────────────────────────────┤
│                                 │
│  [142 pts] [8 streak] [3 🏅]   │  ← Stats row
│                                 │
│  ┌─────────────────────────┐    │
│  │ Partner      Connected ✓│    │
│  │ Content library        ›│    │
│  │ Achievements           ›│    │
│  │ Settings               ›│    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Privacy & data          ›│    │
│  │ About Izana             ›│    │
│  │ Log out                  │    │  ← Red text
│  └─────────────────────────┘    │
│                                 │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

## C12. Partner's View (Screen 13)

The partner signs up through a shared invite link (WhatsApp/SMS/copy). They get an abbreviated onboarding (name, avatar, sex, password only — no wellness questions). Their view:

```
┌─────────────────────────────────┐
│  Supporting stims · day 10      │  ← "Supporting" not "Your"
├─────────────────────────────────┤
│                                 │
│  ✦  Your partner is on day 10   │
│     of stims — they might get   │
│     trigger timing news today.  │
│     They're feeling good and    │
│     keeping up with their plan. │
│                                 │
│     Things you can do today:    │
│                                 │
│  [💬 Send encouragement]        │
│  [🧘 Couples meditation]        │
│  [❓ Ask about supporting stims]│
│                                 │
├─────────────────────────────────┤
│ [Ask anything...]            ▶  │
├─────────────────────────────────┤
│     Today    Journey    You     │
└─────────────────────────────────┘
```

**Partner data visibility (configurable by primary user):**
- Mood: visible by default
- Phase: visible by default
- Symptoms: hidden by default
- Plan adherence: hidden by default
- Bloodwork: never visible to partner

---

# SECTION D: MICROCOPY REFERENCE

Every piece of user-facing text. Claude Code should use these exact strings.

## D1. Loading States (Never a Spinner)

| Context | Microcopy | Animation |
|---------|-----------|-----------|
| Chat response streaming | "Understanding..." → "Searching clinical literature..." → "Found 4 relevant sources..." → "Crafting your answer..." | Each phase gets a subtle ✓ |
| Plan loading | "Preparing your day..." | Items fade in with 100ms stagger |
| Bloodwork analysis | "Reading your results..." → "Comparing with reference ranges..." | Warm gradient progress bar |
| Content video loading | "Loading your session..." | Thumbnail visible, play button pulses |
| App startup | "Welcome back..." | Max 1 second, then content |
| Report generation | "Preparing your doctor's report..." | Step-by-step checkmarks |

## D2. Empty States

| Context | Copy |
|---------|------|
| No plan yet | "Your personalised plan is being crafted by our nutrition team. While you wait — ask me anything or try a meditation." |
| No bloodwork | "Upload your bloodwork and I'll give you personalised insights about every biomarker. It takes under 2 minutes." |
| No check-in today | "Good morning! How are you feeling?" + mood emojis |
| No partner | "Going through this together? Connect your partner and they'll get their own Izana with daily support tips." |
| Search — no results | "I couldn't find that in your journey. Try different words, or ask me directly." |
| Content — none for phase | "New content for this phase is coming soon. In the meantime, try our universal meditation." |

## D3. Button Labels

| Generic (NEVER use) | Izana (ALWAYS use) |
|---------------------|-------------------|
| Submit | Done ✓ |
| Cancel | Not now |
| Delete | Remove |
| OK | Got it |
| Continue | Let's go / Continue → / Next round → |
| Sign up | Start my journey |
| Log in | Welcome back |
| Upload | Upload my results |
| Skip | Skip for now |
| Close | ✕ (icon only) |
| Error: Try again | Let's try that again |

## D4. Error Messages

| Error | User sees |
|-------|-----------|
| Network | "I lost my connection for a moment. Trying again..." |
| Server (500) | "Something unexpected happened on my end. I'm working on it." |
| Rate limited (429) | "I need a moment to catch up. Try again in a few seconds." |
| File too large | "That file is a bit large for me. Could you try one under 5MB?" |
| Invalid file | "I can read PDFs and images (JPEG, PNG). Could you try one of those?" |
| Session expired | "Your session has ended. Let's get you back in." → redirect to login |
| Offline | "This needs an internet connection. I'll have it ready when you're back online." |
| Plan not ready | "Your plan is still being reviewed. I'll let you know the moment it's ready!" |

## D5. Toast Notifications

| Trigger | Toast | Style |
|---------|-------|-------|
| Meal done | "Breakfast logged ✓ +10 points" | Success (sage green) |
| Exercise done | "Yoga complete! 20 min ✓" | Success |
| Meditation done | "10 minutes of calm. Beautiful. ✓" | Success |
| Check-in done | "Check-in done — thank you ✓" | Success |
| 7-day streak | "7-day streak! 🔥" | Celebration (bronze + confetti) |
| Badge earned | "New badge: Wellness Warrior 🏅" | Celebration |
| Plan approved | "Your personalised plan has arrived! 🎉" | Celebration |
| Partner connected | "Your partner is here! 🎉" | Celebration |
| Copied | "Copied ✓" | Neutral (2 seconds) |
| Offline queue | "Saved — will sync when connected" | Info |
| Sync complete | "All caught up ✓" | Success (2 seconds) |

## D6. Input Placeholders

| Field | Placeholder |
|-------|-------------|
| Chat (normal) | "Ask anything..." |
| Chat (landing) | "Ask about your fertility journey..." |
| Chat (grief mode) | "I'm here whenever you're ready..." |
| Search | "Search your journey..." |
| Password | "At least 8 characters" |
| Recovery code | "XXXX-XXXX-XXXX-XXXX" |

---

# SECTION E: EDGE CASES & GUARDRAILS

## E1. Grief Mode

When the user records a NEGATIVE outcome, CHEMICAL pregnancy, MISCARRIAGE, or ECTOPIC:

**Day 0:** Pure empathy. No gamification. No plan updates. Colors muted. Celebrations disabled.
**Day 1:** "I'm here whenever you're ready. No pressure."
**Day 3:** "When you're ready, I have some options for you." Offer: recovery plan, talk about what happened, take a break
**Day 5+:** Actions logged but not scored. No streaks shown. No points.
**Resumption:** User-initiated opt-back-in only. Streak resets gracefully (no "you lost your streak!" message).

## E2. Disengagement Sensing

| Days silent | Behavior |
|-------------|----------|
| 1 day | Normal |
| 2 days | Softer tone. Meal/activity nudges pause. |
| 3–5 days | Only critical nudges (phase transition). Everything else pauses. |
| 5+ days | Complete silence. No messages sent. |
| Return | "Welcome back! How are you today?" (no guilt, no "where were you") |

## E3. Plan Pending Edge Cases

| Scenario | Handling |
|----------|----------|
| Plan pending > 4 hours | Escalation: any nutritionist can review |
| Plan pending > 24 hours | Admin alert. User gets extended general tips. |
| Phase transition while plan pending | Cancel old plan, generate new with URGENT priority |
| Treatment type switch (IUI→IVF) | Close cycle, open new cycle, cancel pending plan |
| User asks about specific meals before plan | "Your personalised plan isn't ready yet. Here are some general tips for your phase..." |

## E4. Offline Behavior

- IndexedDB cache: today's plan, last 2 days messages, check-in template
- Offline actions queued: meal logs, check-ins, content completions
- Videos NOT cached offline
- Amber banner: "You're offline — some features may be limited"
- On reconnect: sync with exponential backoff, toast "All caught up ✓"

## E5. Positive Outcome

1. Celebration (big confetti)
2. Partner notification
3. New plan generated (POSITIVE_OUTCOME priority, early pregnancy nutrition)
4. New phase opens: "Your early pregnancy"
5. "Share with your doctor" prompt
6. Gamification continues but transitions to pregnancy milestones

---

# SECTION F: TECH STACK & ARCHITECTURE

## TECH STACK DECISION

After analyzing the requirements (11-swarm AI pipeline, real-time SSE streaming, 11-language i18n, video streaming, offline support, mobile-first with App Store deployment), here is the recommended stack:

### Frontend
| Choice | Reason |
|--------|--------|
| **Next.js 15** (App Router) | Stable, static export for Capacitor |
| **React 19** | **All client components** (Decision 3: no server components). Landing page SEO via static metadata in layout.tsx |
| **TypeScript 5.x** (strict) | Type safety across 150+ components |
| **Tailwind CSS 4** | Utility-first, works with CSS custom properties for theming |
| **Capacitor 8** | Native iOS/Android from same codebase, App Store deployment |
| **Framer Motion 12** | Luxury micro-interactions (master spec Section 14) |
| **SWR 2** | Client-side data fetching with revalidation |
| **hls.js** | Video/audio streaming from Cloudflare Stream |
| **Zustand** | Lightweight state management (replaces complex context chains) |

### Backend
| Choice | Reason |
|--------|--------|
| **FastAPI** (latest) | Async Python, perfect for AI workloads, SSE support |
| **Python 3.12** | Latest stable, performance improvements |
| **Pydantic v2** | Fast validation, settings management |
| **Supabase** (client) | Already set up, RLS, pgvector, auth |
| **Groq SDK** | Already have keys, fast inference |
| **OpenAI SDK** | Embeddings (text-embedding-3-small) |
| **Redis + arq** | **(Decision 2)** Task queue for swarm pipeline, plan generation, all background jobs. Required dependency. |
| **PyJWT** | **(Decision 1)** Server-side Supabase JWT verification for authentication |

### Infrastructure (Already Available)
| Service | Status |
|---------|--------|
| Supabase (database + auth) | ✅ Ready |
| Groq API keys | ✅ Ready |
| Domain (chat.izana.ai) | ✅ Ready |
| Knowledge base PDFs (236 docs) | ✅ Ready |
| Exercise videos + meditation audios | ✅ Produced |
| **Upstash Redis** (task queue + caching) | ❌ Need to set up — use Upstash (Decision 12: managed, multi-region, auto-failover) |
| Cloudflare Stream | ❌ Need to set up |
| Netlify (frontend hosting) | ❌ Need to set up |
| Render (backend hosting + worker + cron) | ❌ Need to set up |

---

## BUILD ORDER (22 STAGES)

```
Stage 1:  Repository setup + project scaffolding
Stage 2:  Database schema (all migrations)
Stage 3:  Backend core (config, auth, database client, exceptions)
Stage 4:  Swarm pipeline (11 agents + support services)
Stage 5:  RAG engine (embeddings, vector search, knowledge base)
Stage 6:  Chat API (REST + SSE streaming)
Stage 7:  Bloodwork pipeline (upload, OCR, extraction, analysis)
Stage 8:  Backend API — all remaining endpoints
Stage 9:  Background jobs + nudge engine
Stage 10: Frontend shell (layout, routing, design system, theme)
Stage 11: Landing page + preview chat
Stage 12: Identity creation + onboarding
Stage 13: Chat interface + chapter model + weekly groups
Stage 14: Card system (all 11 card types)
Stage 15: Content CMS + Cloudflare Stream + media player
Stage 16: Nutritionist portal
Stage 17: Admin dashboard (8 tabs)
Stage 18: Partner system
Stage 19: Provider portal + reports
Stage 20: FIE pipeline
Stage 21: Offline support + PWA + Capacitor
Stage 22: Testing + deployment

Each stage has a VERIFY step. Do not proceed to the next stage
until the current stage's VERIFY step passes.
```

---

## STAGE 1: REPOSITORY SETUP

### 1.1 Create Monorepo Structure

```bash
mkdir izana && cd izana
git init

# Create directory structure
mkdir -p frontend backend

# Frontend (Next.js 15)
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
# When prompted: Yes to all defaults

# Install frontend dependencies
npm install @supabase/ssr @supabase/supabase-js axios swr zustand
npm install framer-motion lucide-react @radix-ui/react-dialog @radix-ui/react-accordion @radix-ui/react-tabs @radix-ui/react-select @radix-ui/react-checkbox @radix-ui/react-slider @radix-ui/react-tooltip @radix-ui/react-scroll-area
npm install sonner recharts react-markdown remark-gfm react-dropzone canvas-confetti class-variance-authority clsx tailwind-merge
npm install hls.js idb  # Video streaming + IndexedDB for offline
npm install -D vitest @testing-library/react @playwright/test

cd ../backend

# Backend (FastAPI)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings python-dotenv python-multipart
pip install supabase groq openai instructor tiktoken
pip install langchain langchain-community langchain-openai langchain-text-splitters
pip install pypdf pillow pillow-heif reportlab  # pillow-heif for iPhone HEIC photos (A6.2)
pip install redis arq tenacity async-lru   # arq = async task queue (Decision 2)
pip install PyJWT cryptography             # JWT verification (Decision 1)
pip install pywebpush py-vapid
pip install bleach httpx bcrypt            # bcrypt for nutritionist password hashing
pip install prometheus-fastapi-instrumentator prometheus-client
pip install gunicorn pytest pytest-asyncio httpx faker

cd ..
```

### 1.2 Project Structure

Claude Code: Create this exact directory structure. Create empty `__init__.py` files in every Python package directory.

```
izana/
├── frontend/                    # Next.js 15 app
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── chat/
│   │   │   │   └── page.tsx     # Main chat interface
│   │   │   ├── admin/
│   │   │   │   └── page.tsx     # Admin dashboard
│   │   │   ├── nutritionist/
│   │   │   │   ├── login/page.tsx
│   │   │   │   ├── queue/page.tsx
│   │   │   │   └── review/[planId]/page.tsx
│   │   │   ├── logout/page.tsx
│   │   │   ├── privacy/page.tsx
│   │   │   ├── terms/page.tsx
│   │   │   └── about/page.tsx
│   │   ├── components/
│   │   │   ├── ui/              # Base UI primitives (button, input, card, etc.)
│   │   │   ├── chat/            # Chat-specific components
│   │   │   │   ├── ChatInterface.tsx
│   │   │   │   ├── ChatMessageList.tsx
│   │   │   │   ├── ChapterHeader.tsx
│   │   │   │   ├── WeeklyGroup.tsx
│   │   │   │   ├── DaySeparator.tsx
│   │   │   │   ├── MediaPlayer.tsx
│   │   │   │   └── cards/       # All 11 card types
│   │   │   │       ├── ChatCard.tsx          # Polymorphic renderer
│   │   │   │       ├── CheckInCard.tsx
│   │   │   │       ├── PlanCard.tsx
│   │   │   │       ├── SummaryCard.tsx
│   │   │   │       ├── WeeklySummaryCard.tsx
│   │   │   │       ├── TransitionCard.tsx
│   │   │   │       ├── PartnerCard.tsx
│   │   │   │       ├── CelebrationCard.tsx
│   │   │   │       ├── BloodworkCard.tsx
│   │   │   │       ├── ContentCard.tsx
│   │   │   │       └── PlanStatusCard.tsx
│   │   │   ├── landing/         # Landing page components
│   │   │   │   ├── LandingPage.tsx
│   │   │   │   ├── PreviewChat.tsx
│   │   │   │   └── SocialProofStrip.tsx
│   │   │   ├── identity/        # Auth components
│   │   │   │   ├── IdentityCreator.tsx
│   │   │   │   └── RecoveryPhrase.tsx
│   │   │   ├── onboarding/      # Conversational onboarding
│   │   │   │   └── ConversationalOnboarding.tsx
│   │   │   ├── navigation/      # Navigation components
│   │   │   │   ├── BottomNav.tsx
│   │   │   │   └── ChapterTimeline.tsx
│   │   │   ├── sharing/         # Provider portal sharing
│   │   │   │   └── ShareModal.tsx
│   │   │   ├── bloodwork/       # Bloodwork upload pipeline
│   │   │   │   └── TrustModal.tsx
│   │   │   ├── admin/           # Admin dashboard components
│   │   │   │   ├── DashboardTab.tsx
│   │   │   │   ├── AnalyticsTab.tsx
│   │   │   │   ├── FeedbackTab.tsx
│   │   │   │   ├── TrainingTab.tsx
│   │   │   │   ├── HealthTab.tsx
│   │   │   │   ├── PromptsTab.tsx
│   │   │   │   ├── ContentManagerTab.tsx
│   │   │   │   └── PlanQueueTab.tsx
│   │   │   ├── nutritionist/    # Nutritionist portal components
│   │   │   │   ├── NutritionistQueue.tsx
│   │   │   │   ├── PlanReviewEditor.tsx
│   │   │   │   └── NutritionistSidebar.tsx
│   │   │   └── offline/         # Offline support
│   │   │       ├── OfflineQueue.tsx
│   │   │       └── OfflineBanner.tsx
│   │   ├── hooks/               # Custom React hooks
│   │   │   ├── useStreamingChat.ts
│   │   │   ├── useChapter.ts
│   │   │   ├── useWeeklyGroups.ts
│   │   │   ├── useProfile.ts
│   │   │   ├── useConversationalOnboarding.ts
│   │   │   ├── useOfflineQueue.ts
│   │   │   ├── usePlanStatus.ts
│   │   │   ├── useTheme.ts
│   │   │   ├── useMediaPlayer.ts
│   │   │   ├── useTranslation.ts
│   │   │   ├── useLanguage.ts
│   │   │   ├── useOnlineStatus.ts
│   │   │   ├── usePushNotifications.ts
│   │   │   ├── usePersonalizedQuestions.ts
│   │   │   ├── useConversationSearch.ts
│   │   │   └── useDebounce.ts
│   │   ├── lib/                 # Utilities and configuration
│   │   │   ├── api.ts           # API client functions (60+ endpoints)
│   │   │   ├── api-client.ts    # Generic ApiClient class with retry
│   │   │   ├── supabase/
│   │   │   │   ├── client.ts    # Browser Supabase client
│   │   │   │   └── server.ts    # Server Supabase client
│   │   │   ├── theme.ts         # CSS variable management
│   │   │   ├── offline-store.ts # IndexedDB wrapper
│   │   │   ├── cloudflare-player.ts  # hls.js config
│   │   │   ├── chapter-utils.ts # Week grouping, day counting
│   │   │   ├── utils.ts         # cn() helper
│   │   │   ├── greeting.ts      # Time-based greeting
│   │   │   ├── translations/    # i18n files (Decision 18: type-safe)
│   │   │   │   ├── en.ts       # BASE TYPE: export const en = {...} as const;
│   │   │   │   │               #   export type TranslationKeys = typeof en;
│   │   │   │   ├── es.ts       # const es: TranslationKeys = {...} — TS catches missing keys
│   │   │   │   ├── it.ts
│   │   │   │   ├── hi.ts
│   │   │   │   ├── ta.ts
│   │   │   │   ├── te.ts
│   │   │   │   ├── ml.ts
│   │   │   │   ├── kn.ts
│   │   │   │   ├── ko.ts
│   │   │   │   ├── ja.ts
│   │   │   │   └── zh.ts
│   │   │   └── wellness-config.ts
│   │   ├── stores/              # Zustand stores
│   │   │   ├── chat-store.ts
│   │   │   ├── chapter-store.ts
│   │   │   ├── user-store.ts
│   │   │   └── theme-store.ts
│   │   └── styles/
│   │       └── globals.css      # Design system CSS custom properties
│   ├── public/
│   │   ├── manifest.json        # PWA manifest
│   │   ├── sw.js                # Service worker
│   │   └── icons/               # App icons (72x72 to 512x512)
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── capacitor.config.ts      # Capacitor config (Stage 21)
│   └── tsconfig.json
│
├── backend/                     # FastAPI app
│   ├── app/
│   │   ├── main.py              # FastAPI app entry, middleware, routes
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings (all env vars)
│   │   │   ├── database.py      # Supabase client singleton
│   │   │   ├── auth.py          # JWT verification + Admin API key (Decision 1)
│   │   │   ├── exceptions.py    # 23+ custom exceptions
│   │   │   ├── model_config.py  # LLM model registry + fallback chains
│   │   │   ├── validators.py    # Input sanitization, PII detection
│   │   │   ├── biomarker_config.py  # Reference ranges
│   │   │   ├── logging_config.py    # Structured JSON logging
│   │   │   ├── metrics.py       # Prometheus business metrics
│   │   │   ├── timeouts.py      # Operation timeout config
│   │   │   └── correlation.py   # Request correlation IDs
│   │   ├── models/              # Pydantic models
│   │   │   ├── enums.py         # Treatment, phase, status enums
│   │   │   ├── chat.py          # Chat request/response
│   │   │   ├── schemas.py       # Bloodwork panels (88+ fields)
│   │   │   ├── journey.py       # Journey, chapter, cycle models
│   │   │   ├── companion.py     # Symptoms, emotions, check-ins
│   │   │   ├── nutrition.py     # Plans, meals, activities
│   │   │   ├── admin.py         # Queue, review, modification
│   │   │   ├── content.py       # Content assets
│   │   │   └── retrieval.py     # RAG output models
│   │   ├── api/                 # API routers (one file per domain)
│   │   │   ├── auth_routes.py    # POST /auth/signup, GET /auth/lookup (Decision 7)
│   │   │   ├── chat.py          # Chat SSE streaming (polls task queue) (Decision 2)
│   │   │   ├── preview.py       # Preview chat (no auth)
│   │   │   ├── chapters.py      # Chapter CRUD
│   │   │   ├── bloodwork.py     # Upload, extraction, analysis
│   │   │   ├── companion.py     # Check-ins, outcomes, recovery
│   │   │   ├── nutrition.py     # Plans, meals, activities, dashboard
│   │   │   ├── coach.py         # Partner, gamification, goals
│   │   │   ├── content.py       # Content library endpoints
│   │   │   ├── content_admin.py # Content CMS (admin)
│   │   │   ├── plan_status.py   # Plan queue status polling
│   │   │   ├── push.py          # Web push subscriptions
│   │   │   ├── privacy.py       # GDPR endpoints
│   │   │   ├── reports.py       # Provider portal + PDF reports
│   │   │   ├── translate.py     # UI translation
│   │   │   ├── admin.py         # Admin dashboard endpoints
│   │   │   ├── admin_health.py  # Swarm health monitoring
│   │   │   ├── admin_models.py  # LLM model status
│   │   │   ├── admin_analytics.py  # Gaps, citations, sentiment
│   │   │   ├── admin_prompts.py # Prompt editor
│   │   │   ├── admin_dpo.py     # DPO training data
│   │   │   ├── nutritionist.py  # Nutritionist portal API
│   │   │   ├── resilience.py    # Health checks, circuit breakers
│   │   │   └── jobs.py          # Background job triggers
│   │   ├── services/            # Business logic
│   │   │   ├── groq_client.py            # Multi-key LLM client with rotation
│   │   │   ├── swarm_base.py            # Abstract base (retry wrapper, tracing — Decision 5, 10)
│   │   │   ├── translator.py            # Swarm 0: Translation (swarm_id="swarm_0_polyglot")
│   │   │   ├── gatekeeper.py            # Swarm 1: Safety + topic classification
│   │   │   ├── bloodwork_extractor.py   # Swarm 2: Bloodwork OCR
│   │   │   ├── clinical_brain.py        # Swarm 3: RAG engine
│   │   │   ├── response_curator.py      # Swarm 4: Response generation
│   │   │   ├── bloodwork_analyser.py    # Swarm 5: Biomarker interpretation
│   │   │   ├── bloodwork_curator.py     # Swarm 6: Patient-friendly formatting
│   │   │   ├── compliance_checker.py    # Swarm 7: Medical disclaimers
│   │   │   ├── gap_detector.py          # Swarm 8: Knowledge gap detection
│   │   │   ├── context_builder.py       # Swarm 9: Conversation context
│   │   │   ├── sentiment_analyser.py    # Swarm 10: Sentiment analysis
│   │   │   #  (Decision 17: files named by function, not number.
│   │   │   #   Each class keeps swarm_id for trace compatibility.)
│   │   │   ├── swarm_health.py          # Per-swarm metrics
│   │   │   ├── vision_client.py         # OCR (Groq → OpenAI fallback)
│   │   │   ├── pdf_handler.py           # PDF text extraction
│   │   │   ├── storage.py               # Supabase file storage
│   │   │   ├── cache_service.py         # Redis + in-memory cache
│   │   │   ├── circuit_breaker.py       # Resilience pattern
│   │   │   ├── health_monitor.py        # System health checks
│   │   │   ├── reasoning_chain.py       # Chain-of-thought builder
│   │   │   ├── question_generator.py    # Personalized questions
│   │   │   ├── chapter_service.py       # Chapter lifecycle
│   │   │   ├── cycle_service.py         # Multi-cycle management
│   │   │   ├── journey_service.py       # Journey management
│   │   │   ├── plan_service.py          # Plan lifecycle
│   │   │   ├── plan_generation.py       # AI plan generation pipeline
│   │   │   ├── nudge_service.py         # Notification scheduling
│   │   │   ├── disengagement_service.py # Silence detection
│   │   │   ├── phase_transition.py      # Transition prompt scheduling
│   │   │   ├── gamification_service.py  # Points, streaks, badges
│   │   │   ├── partner_service.py       # Partner linking + coaching
│   │   │   ├── content_admin_service.py # Content CMS operations
│   │   │   ├── cloudflare_stream.py     # Video/audio upload + streaming
│   │   │   ├── report_generator.py      # PDF report generation
│   │   │   ├── data_lifecycle.py        # Tiered archival
│   │   │   ├── email_service.py         # SendGrid/SMTP
│   │   │   ├── webpush_service.py       # Web Push Protocol
│   │   │   ├── recovery_phrase.py       # Account recovery
│   │   │   ├── hitl_service.py          # Human-in-the-loop workflow
│   │   │   └── notification_service.py  # Multi-channel dispatch
│   │   ├── workers/             # Task queue workers (Decision 2, 4)
│   │   │   ├── __init__.py
│   │   │   ├── worker.py        # arq worker entry point
│   │   │   ├── chat_tasks.py    # Chat pipeline task
│   │   │   ├── plan_tasks.py    # Plan generation task
│   │   │   ├── bloodwork_tasks.py  # Bloodwork analysis task
│   │   │   └── scheduled_tasks.py  # Cron-triggered tasks (evening summary, etc.)
│   │   ├── services/fie/        # Fertility Intelligence Engine (isolated)
│   │   │   ├── __init__.py
│   │   │   ├── feature_extractor.py
│   │   │   ├── training_generator.py
│   │   │   ├── insight_engine.py
│   │   │   ├── model_trainer.py
│   │   │   ├── feedback_provider.py
│   │   │   ├── anonymizer.py
│   │   │   └── feature_config.py
│   │   ├── swarms/              # Nutrition-specific swarms
│   │   │   ├── nutrition_swarm_0.py     # Input validation
│   │   │   ├── nutrition_swarm_1.py     # Profile analysis
│   │   │   └── nutrition_swarm_2.py     # Plan generation
│   │   └── jobs/                # Background tasks
│   │       ├── chapter_jobs.py
│   │       ├── nutrition_jobs.py
│   │       ├── companion_jobs.py
│   │       ├── data_lifecycle.py
│   │       └── fie_jobs.py
│   ├── supabase/
│   │   └── migrations/          # SQL migration files
│   ├── knowledge_base/          # 236 clinical PDFs (already available)
│   ├── scripts/
│   │   ├── ingest_docs.py       # Knowledge base ingestion
│   │   ├── seed_phase_durations.py
│   │   ├── seed_phase_content.py
│   │   ├── seed_badges.py
│   │   └── seed_symptoms.py
│   ├── tests/                  # (Decision 8: tests written per stage)
│   │   ├── conftest.py         # Shared fixtures, mock clients
│   │   ├── mocks/
│   │   │   ├── mock_groq.py    # (Decision 19) Deterministic fixture responses per swarm:
│   │   │   │                   #   gatekeeper → {safe:true, is_fertility_related:true}
│   │   │   │                   #   curator → fixed clinical response with sources
│   │   │   │                   #   polyglot → returns input unchanged
│   │   │   │                   #   compliance → returns input + disclaimer appended
│   │   │   │                   #   Also: mock_groq_empty (returns ""), mock_groq_timeout
│   │   │   ├── mock_supabase.py # Mock Supabase client (DB + Auth + Storage)
│   │   │   └── mock_openai.py  # Mock OpenAI embeddings (returns fixed 384-dim vector)
│   │   ├── fixtures/
│   │   ├── test_auth.py        # Stage 3: JWT verification tests
│   │   ├── test_swarms.py      # Stage 4: Swarm unit tests
│   │   ├── test_rag.py         # Stage 5: RAG search tests
│   │   ├── test_chat_pipeline.py # Stage 6: Chat pipeline integration tests
│   │   ├── test_bloodwork.py   # Stage 7: Bloodwork pipeline tests
│   │   ├── test_plans.py       # Stage 8: Plan lifecycle tests
│   │   └── test_*.py           # Additional per-stage tests
│   └── requirements.txt
│
├── .gitignore
├── README.md
└── IZANA_MASTER_SPECIFICATION.md  # The master spec document
```

### VERIFY STAGE 1:
```bash
# Frontend starts
cd frontend && npm run dev  # Should open on localhost:3000

# Backend starts
cd ../backend && source venv/bin/activate
uvicorn app.main:app --reload  # Should open on localhost:8000

# Both show default pages without errors

# Redis connection (Decision 2) — requires Redis running locally or Upstash URL
python -c "import redis; r = redis.from_url('redis://localhost:6379'); r.ping(); print('Redis OK')"

# Test infrastructure (Decision 8) — pytest discovers test files
cd backend && pytest --collect-only  # Should find conftest.py and initial test files
cd ../frontend && npx vitest --run --reporter=verbose 2>/dev/null || echo "No frontend tests yet — OK for Stage 1"
```

---

## STAGE 2: DATABASE SCHEMA

### 2.1 Core Principle
All database changes are SQL migration files. Create them in `backend/supabase/migrations/` with sequential numbering.

### 2.2 Migration Files

Claude Code: Create each of these as a separate SQL file. Execute them against your Supabase project in order.

**File: `001_core_tables.sql`**

```sql
-- ═══════════════════════════════════════════
-- CORE TABLES
-- ═══════════════════════════════════════════

-- Profiles (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  pseudonym TEXT UNIQUE NOT NULL,
  gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
  treatment_path TEXT,
  language TEXT DEFAULT 'en',
  avatar TEXT DEFAULT 'Phoenix',
  timezone TEXT DEFAULT 'UTC',
  
  -- Consent
  consent_timestamp TIMESTAMPTZ,
  consent_version TEXT DEFAULT '2.0',
  
  -- Bloodwork
  core_fertility_json JSONB DEFAULT '{}',
  extended_bloodwork_json JSONB DEFAULT '{}',
  bloodwork_analysis_json JSONB DEFAULT '[]',
  report_history JSONB DEFAULT '[]',
  
  -- Wellness profile
  age_range TEXT,
  health_conditions TEXT[] DEFAULT '{}',
  height_cm DECIMAL,
  weight_kg DECIMAL,
  bmi DECIMAL,
  fitness_level TEXT,
  smoking_status TEXT,
  alcohol_consumption TEXT,
  sleep_duration TEXT,
  sleep_quality TEXT,
  stress_level TEXT,
  hydration TEXT,
  digestion_issues TEXT[] DEFAULT '{}',
  
  -- Nutrition preferences
  allergies TEXT[] DEFAULT '{}',
  dietary_restrictions TEXT[] DEFAULT '{}',
  food_preferences TEXT[] DEFAULT '{}',
  food_dislikes TEXT,
  exercise_time_minutes INTEGER,
  exercise_preferences TEXT[] DEFAULT '{}',
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their profile" ON profiles
  FOR ALL USING (auth.uid() = id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

**File: `002_cycles_chapters.sql`**

```sql
-- ═══════════════════════════════════════════
-- CYCLES & CHAPTERS (Guided Journey core)
-- ═══════════════════════════════════════════

CREATE TABLE cycles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  treatment_type TEXT NOT NULL,
  cycle_number INTEGER NOT NULL DEFAULT 1,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  outcome TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their cycles" ON cycles
  FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_cycles_user ON cycles(user_id);

-- Treatment journeys
CREATE TABLE treatment_journeys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  cycle_id UUID REFERENCES cycles(id),
  treatment_type TEXT NOT NULL,
  phase TEXT NOT NULL,
  stim_day INTEGER,
  is_active BOOLEAN DEFAULT true,
  started_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  cycle_start_date DATE,
  expected_retrieval_date DATE,
  expected_transfer_date DATE,
  outcome TEXT,
  outcome_date DATE,
  outcome_emotions TEXT[],
  outcome_notes TEXT
);

ALTER TABLE treatment_journeys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their journeys" ON treatment_journeys
  FOR ALL USING (auth.uid() = user_id);

-- Chapters (the core of the Guided Journey model)
CREATE TABLE chapters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  journey_id UUID REFERENCES treatment_journeys(id),
  cycle_id UUID REFERENCES cycles(id),
  phase TEXT NOT NULL,
  day_count INTEGER DEFAULT 1,
  week_count INTEGER DEFAULT 1,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  expected_duration_days INTEGER,
  status TEXT NOT NULL DEFAULT 'active' 
    CHECK (status IN ('active', 'completed', 'grief', 'positive')),
  plan_snapshot_id UUID, -- FK added after personalized_plans table created
  summary_text TEXT,
  grief_mode BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their chapters" ON chapters
  FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_chapters_user_active ON chapters(user_id) WHERE status = 'active';
CREATE INDEX idx_chapters_user ON chapters(user_id);

-- Phase durations config (admin-editable)
CREATE TABLE phase_durations (
  id SERIAL PRIMARY KEY,
  treatment_type TEXT NOT NULL,
  phase TEXT NOT NULL,
  avg_days INTEGER NOT NULL,
  min_days INTEGER NOT NULL,
  max_days INTEGER NOT NULL,
  transition_prompt_template TEXT,
  soft_checkin_pct DECIMAL DEFAULT 0.8,
  transition_prompt_pct DECIMAL DEFAULT 1.0,
  followup_interval_days INTEGER DEFAULT 2,
  UNIQUE(treatment_type, phase)
);
```

**File: `003_chat_logs.sql`**

```sql
-- ═══════════════════════════════════════════
-- CHAT LOGS (with chapter + card support)
-- ═══════════════════════════════════════════

CREATE TABLE chat_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chapter_id UUID REFERENCES chapters(id),
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  message_type TEXT DEFAULT 'text' CHECK (message_type IN (
    'text', 'checkin_card', 'plan_card', 'summary_card', 
    'transition_card', 'partner_card', 'celebration_card', 
    'bloodwork_card', 'content_card', 'plan_status_card', 
    'week_summary_card'
  )),
  card_data JSONB,
  week_number INTEGER,
  retain BOOLEAN DEFAULT false, -- Medical cards retained permanently
  sources JSONB DEFAULT '[]',
  suggested_followups TEXT[] DEFAULT '{}',
  message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE chat_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their chat logs" ON chat_logs
  FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_chat_logs_user ON chat_logs(user_id, created_at DESC);
CREATE INDEX idx_chat_logs_chapter ON chat_logs(chapter_id, week_number);

-- Chat summaries
CREATE TABLE chat_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chapter_id UUID REFERENCES chapters(id),
  session_id TEXT,
  summary_text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE chat_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their summaries" ON chat_summaries
  FOR ALL USING (auth.uid() = user_id);

-- Chat logs archive (for completed cycles)
CREATE TABLE chat_logs_archive (
  LIKE chat_logs INCLUDING ALL
);
ALTER TABLE chat_logs_archive ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their archived logs" ON chat_logs_archive
  FOR ALL USING (auth.uid() = user_id);

-- Weekly chapter summaries
CREATE TABLE chapter_summaries_weekly (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID NOT NULL REFERENCES chapters(id),
  week_number INTEGER NOT NULL,
  summary_text TEXT,
  stats JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(chapter_id, week_number)
);
```

**File: `004_companion.sql`**

```sql
-- ═══════════════════════════════════════════
-- COMPANION: Check-ins, Symptoms, Emotions
-- ═══════════════════════════════════════════

CREATE TABLE symptom_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symptoms TEXT[] NOT NULL,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);

ALTER TABLE symptom_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their symptom logs" ON symptom_logs
  FOR ALL USING (auth.uid() = user_id);

CREATE TABLE emotion_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  mood TEXT NOT NULL CHECK (mood IN ('great', 'good', 'okay', 'low', 'struggling')),
  anxiety INTEGER CHECK (anxiety BETWEEN 1 AND 5),
  hope INTEGER CHECK (hope BETWEEN 1 AND 5),
  energy INTEGER CHECK (energy BETWEEN 1 AND 5),
  overwhelm INTEGER CHECK (overwhelm BETWEEN 1 AND 5),
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);

ALTER TABLE emotion_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their emotion logs" ON emotion_logs
  FOR ALL USING (auth.uid() = user_id);

-- Phase-specific symptoms (seeded data)
CREATE TABLE phase_symptoms (
  id SERIAL PRIMARY KEY,
  phase TEXT NOT NULL,
  category TEXT NOT NULL, -- physical, emotional, medication_side_effect, warning
  symptom TEXT NOT NULL,
  severity_default TEXT DEFAULT 'mild',
  UNIQUE(phase, symptom)
);

-- Phase-specific content/tips (seeded data)
CREATE TABLE phase_content (
  id SERIAL PRIMARY KEY,
  phase TEXT NOT NULL,
  day_in_phase INTEGER,
  content_type TEXT DEFAULT 'tip',
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  treatment_type TEXT,
  language TEXT DEFAULT 'en'
);

-- Population insights (aggregated, anonymized)
CREATE TABLE population_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phase TEXT NOT NULL,
  day_in_phase INTEGER,
  insight_type TEXT NOT NULL,
  insight_text TEXT NOT NULL,
  sample_size INTEGER,
  percentage DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Outcome tracking
-- (handled via treatment_journeys.outcome fields)

-- Partner links
CREATE TABLE partner_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  partner_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  invite_code TEXT UNIQUE,
  invite_expires_at TIMESTAMPTZ,
  visibility_settings JSONB DEFAULT '{"mood": true, "phase": true, "symptoms": false, "plan_adherence": false}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE partner_links ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see their partner links" ON partner_links
  FOR ALL USING (auth.uid() = primary_user_id OR auth.uid() = partner_user_id);

-- Recovery phrases
CREATE TABLE recovery_phrases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  phrase_hash TEXT NOT NULL, -- SHA-256 with salt
  salt TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE recovery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pseudonym TEXT NOT NULL,
  ip_address TEXT,
  attempted_at TIMESTAMPTZ DEFAULT now(),
  success BOOLEAN DEFAULT false
);
```

**File: `005_nutrition_plans.sql`**

```sql
-- ═══════════════════════════════════════════
-- NUTRITION PLANS & APPROVAL WORKFLOW
-- ═══════════════════════════════════════════

CREATE TABLE personalized_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nutrition_plan JSONB NOT NULL DEFAULT '{}',
  exercise_plan JSONB NOT NULL DEFAULT '{}',
  mental_health_plan JSONB NOT NULL DEFAULT '{}',
  exercise_content_ids UUID[] DEFAULT '{}',
  meditation_content_ids UUID[] DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'PENDING_NUTRITIONIST' CHECK (status IN (
    'GENERATING', 'PENDING_NUTRITIONIST', 'IN_REVIEW', 
    'APPROVED', 'MODIFIED', 'REJECTED', 'EXPIRED'
  )),
  source TEXT DEFAULT 'ai_generated' CHECK (source IN ('ai_generated', 'nutritionist_modified')),
  parent_plan_id UUID REFERENCES personalized_plans(id),
  version INTEGER DEFAULT 1,
  treatment_type TEXT,
  phase TEXT,
  generation_context JSONB, -- What data the AI used to generate
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE personalized_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their plans" ON personalized_plans
  FOR ALL USING (auth.uid() = user_id);

-- Add FK from chapters to plans
ALTER TABLE chapters ADD CONSTRAINT fk_chapters_plan 
  FOREIGN KEY (plan_snapshot_id) REFERENCES personalized_plans(id);

-- Approval queue
CREATE TABLE approval_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN (
    'PENDING', 'ASSIGNED', 'IN_REVIEW', 'COMPLETED'
  )),
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN (
    'normal', 'urgent_phase_change', 'positive_outcome'
  )),
  assigned_to UUID,
  adaptation_context JSONB,
  deadline TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Plan modifications (for DPO training)
CREATE TABLE plan_modifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  section TEXT NOT NULL, -- nutrition, exercise, mental_health
  field_path TEXT NOT NULL,
  ai_original TEXT,
  human_modified TEXT,
  reason TEXT,
  category TEXT,
  severity TEXT CHECK (severity IN ('minor', 'moderate', 'major', 'critical')),
  could_cause_harm BOOLEAN DEFAULT false,
  training_eligible BOOLEAN DEFAULT true,
  reviewer_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Plan review history
CREATE TABLE plan_review_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  action TEXT NOT NULL, -- approve, modify, reject
  reviewer_id UUID,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Meal logs
CREATE TABLE meal_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  meal_type TEXT NOT NULL, -- breakfast, lunch, dinner, snack
  description TEXT,
  followed_plan BOOLEAN,
  satisfaction INTEGER CHECK (satisfaction BETWEEN 1 AND 5),
  offline_sync BOOLEAN DEFAULT false,
  logged_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their meal logs" ON meal_logs
  FOR ALL USING (auth.uid() = user_id);

-- Activity logs
CREATE TABLE activity_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  activity_type TEXT NOT NULL, -- exercise, meditation, walk, yoga
  content_id UUID, -- FK to wellness_content if from plan
  duration_minutes INTEGER,
  completion_pct DECIMAL DEFAULT 100,
  offline_sync BOOLEAN DEFAULT false,
  logged_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their activity logs" ON activity_logs
  FOR ALL USING (auth.uid() = user_id);

-- Nutritionist/admin users
CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'NUTRITIONIST' CHECK (role IN ('NUTRITIONIST', 'ADMIN')),
  password_hash TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**File: `006_content_gamification.sql`**

```sql
-- ═══════════════════════════════════════════
-- CONTENT LIBRARY & GAMIFICATION
-- ═══════════════════════════════════════════

-- Wellness content (exercise videos + meditation audios)
CREATE TABLE wellness_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  content_type TEXT NOT NULL CHECK (content_type IN (
    'exercise_video', 'meditation_audio', 'breathing_exercise', 
    'yoga_video', 'article', 'audio_guide'
  )),
  duration_seconds INTEGER,
  cloudflare_stream_id TEXT,
  thumbnail_url TEXT,
  
  -- Plan integration
  intensity TEXT CHECK (intensity IN ('gentle', 'light', 'moderate', 'active')),
  plan_eligible BOOLEAN DEFAULT false,
  treatment_phases TEXT[] DEFAULT '{}',
  treatment_types TEXT[] DEFAULT '{}',
  contraindications TEXT[] DEFAULT '{}',
  categories TEXT[] DEFAULT '{}',
  partner_suitable BOOLEAN DEFAULT false,
  grief_appropriate BOOLEAN DEFAULT false,
  early_pregnancy_safe BOOLEAN DEFAULT false,
  
  -- Translations
  translations JSONB DEFAULT '{}',
  
  -- Admin
  is_active BOOLEAN DEFAULT true,
  sort_order INTEGER DEFAULT 0,
  version INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Content progress tracking
CREATE TABLE content_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_id UUID NOT NULL REFERENCES wellness_content(id),
  progress_pct DECIMAL DEFAULT 0,
  position_seconds INTEGER DEFAULT 0,
  completed BOOLEAN DEFAULT false,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, content_id)
);

ALTER TABLE content_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their progress" ON content_progress
  FOR ALL USING (auth.uid() = user_id);

-- Content ratings
CREATE TABLE content_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_id UUID NOT NULL REFERENCES wellness_content(id),
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, content_id)
);

ALTER TABLE content_ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their ratings" ON content_ratings
  FOR ALL USING (auth.uid() = user_id);

-- Gamification
CREATE TABLE user_gamification (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  total_points INTEGER DEFAULT 0,
  level INTEGER DEFAULT 1,
  level_name TEXT DEFAULT 'Beginner',
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  couple_streak INTEGER DEFAULT 0,
  level_progress DECIMAL DEFAULT 0,
  version INTEGER DEFAULT 1, -- Optimistic locking
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_gamification ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their gamification" ON user_gamification
  FOR ALL USING (auth.uid() = user_id);

-- Badge definitions
CREATE TABLE badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL, -- streak, nutrition, exercise, couple, special
  criteria JSONB NOT NULL,
  icon TEXT,
  sort_order INTEGER DEFAULT 0
);

-- User badges
CREATE TABLE user_badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  badge_id UUID NOT NULL REFERENCES badges(id),
  earned_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, badge_id)
);

ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their badges" ON user_badges
  FOR ALL USING (auth.uid() = user_id);

-- Couple goals
CREATE TABLE couple_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_user_id UUID NOT NULL REFERENCES auth.users(id),
  partner_user_id UUID REFERENCES auth.users(id),
  goal_type TEXT NOT NULL,
  target INTEGER NOT NULL,
  progress_primary INTEGER DEFAULT 0,
  progress_partner INTEGER DEFAULT 0,
  deadline DATE,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**File: `007_feedback_training.sql`**

```sql
-- ═══════════════════════════════════════════
-- FEEDBACK, DPO, & TRAINING DATA
-- ═══════════════════════════════════════════

CREATE TABLE dpo_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  message_id TEXT,
  score INTEGER CHECK (score IN (0, 1)),
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dpo_feedback_details (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  message_id TEXT,
  query TEXT,
  response TEXT,
  issues TEXT[] DEFAULT '{}',
  feedback_text TEXT,
  preferred_response TEXT,
  quality_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_data_pairs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chosen TEXT NOT NULL,
  rejected TEXT NOT NULL,
  query TEXT,
  preference_strength DECIMAL,
  source TEXT DEFAULT 'user_feedback',
  validated BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dpo_analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  total_feedback INTEGER DEFAULT 0,
  helpful_count INTEGER DEFAULT 0,
  not_helpful_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_export_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exported_by TEXT,
  record_count INTEGER,
  format TEXT DEFAULT 'jsonl',
  filters JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**File: `008_system_tables.sql`**

```sql
-- ═══════════════════════════════════════════
-- SYSTEM: RAG, Admin, Monitoring, Push, Nudges
-- ═══════════════════════════════════════════

-- RAG knowledge base (for pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(384), -- BAAI/bge-small-en-v1.5 dimensions
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Vector search function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Admin prompts (editable swarm prompts)
CREATE TABLE admin_prompts (
  id SERIAL PRIMARY KEY,
  swarm_id TEXT UNIQUE NOT NULL,
  swarm_name TEXT NOT NULL,
  prompt_text TEXT NOT NULL,
  version INTEGER DEFAULT 1,
  updated_at TIMESTAMPTZ DEFAULT now(),
  updated_by TEXT
);

-- Knowledge gaps
CREATE TABLE knowledge_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_type TEXT NOT NULL, -- chat, bloodwork, retrieval_empty, low_confidence
  query TEXT NOT NULL,
  context JSONB,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'reviewed', 'addressed', 'dismissed')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Citation logs
CREATE TABLE citation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id TEXT,
  document_id UUID REFERENCES documents(id),
  relevance_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Compliance logs
CREATE TABLE compliance_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id TEXT,
  checks JSONB NOT NULL, -- {tone, language, citations, disclaimer}
  passed BOOLEAN,
  fix_attempts INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Swarm health logs
CREATE TABLE swarm_health_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  swarm_id TEXT NOT NULL,
  call_count INTEGER DEFAULT 0,
  error_count INTEGER DEFAULT 0,
  avg_latency_ms DECIMAL,
  p95_latency_ms DECIMAL,
  status TEXT DEFAULT 'healthy',
  recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Push subscriptions
CREATE TABLE push_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subscription JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their subscriptions" ON push_subscriptions
  FOR ALL USING (auth.uid() = user_id);

-- Nudge queue
CREATE TABLE nudge_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nudge_type TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'push' CHECK (channel IN ('push', 'email', 'in_app', 'chat_card')),
  scheduled_for TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
  message_template TEXT,
  message_data JSONB,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Notifications
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT,
  read BOOLEAN DEFAULT false,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their notifications" ON notifications
  FOR ALL USING (auth.uid() = user_id);

-- Provider portal shares
CREATE TABLE provider_shares (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  token TEXT UNIQUE NOT NULL,
  include_bloodwork BOOLEAN DEFAULT true,
  include_checkins BOOLEAN DEFAULT true,
  include_timeline BOOLEAN DEFAULT true,
  include_adherence BOOLEAN DEFAULT true,
  valid_days INTEGER DEFAULT 7,
  max_views INTEGER DEFAULT 10,
  current_views INTEGER DEFAULT 0,
  expires_at TIMESTAMPTZ NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- PHI audit log
CREATE TABLE phi_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  share_token TEXT,
  action TEXT NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  accessed_at TIMESTAMPTZ DEFAULT now()
);

-- Bloodwork snapshots
CREATE TABLE bloodwork_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  biomarkers JSONB NOT NULL,
  trend_data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE bloodwork_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their snapshots" ON bloodwork_snapshots
  FOR ALL USING (auth.uid() = user_id);

-- Questionnaire state machine
CREATE TABLE questionnaire_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  current_step TEXT NOT NULL,
  responses JSONB DEFAULT '{}',
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  UNIQUE(user_id)
);

ALTER TABLE questionnaire_states ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their questionnaire" ON questionnaire_states
  FOR ALL USING (auth.uid() = user_id);
```

**File: `009_fie_schema.sql`**

```sql
-- ═══════════════════════════════════════════
-- FERTILITY INTELLIGENCE ENGINE (isolated schema)
-- ═══════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS fie;

CREATE TABLE fie.feature_store (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT UNIQUE NOT NULL,
  treatment_type TEXT NOT NULL,
  cycle_number INTEGER,
  features_demographic JSONB,
  features_biomarker JSONB,
  features_behavioral JSONB,
  features_treatment JSONB,
  outcome TEXT,
  outcome_binary INTEGER,
  cycle_completed BOOLEAN DEFAULT false,
  data_quality_score DECIMAL,
  extracted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.training_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT NOT NULL,
  feature_vector JSONB NOT NULL,
  target_outcome INTEGER NOT NULL,
  treatment_type TEXT NOT NULL,
  quality_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_type TEXT NOT NULL,
  treatment_type TEXT,
  phase TEXT,
  description TEXT NOT NULL,
  statistical_significance DECIMAL,
  effect_size DECIMAL,
  sample_size INTEGER,
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  actionable BOOLEAN DEFAULT false,
  insight_data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.model_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  treatment_type TEXT,
  algorithm TEXT,
  features_used TEXT[],
  training_samples INTEGER,
  metrics JSONB,
  model_artifact_path TEXT,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.export_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exported_by TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  treatment_type_filter TEXT,
  quality_threshold DECIMAL,
  format TEXT DEFAULT 'jsonl',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**File: `010_chat_traces.sql`** (Decision 10 — Observability)

```sql
-- ═══════════════════════════════════════════
-- CHAT TRACES: Per-swarm call logging for
-- debugging, cost tracking, and observability
-- (Decision 10 from architectural review)
-- ═══════════════════════════════════════════

CREATE TABLE chat_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id UUID NOT NULL,           -- Groups all swarm calls for one user message
  message_id TEXT,                  -- Links to chat_logs.message_id
  swarm_id TEXT NOT NULL,           -- e.g., 'swarm_0_polyglot', 'swarm_4_curator'
  input_text TEXT,                  -- What was sent to the LLM (truncated to 2000 chars)
  output_text TEXT,                 -- What the LLM returned (truncated to 2000 chars)
  model TEXT,                       -- e.g., 'llama-3.3-70b-versatile'
  tokens_in INTEGER,
  tokens_out INTEGER,
  latency_ms INTEGER,
  error TEXT,                       -- NULL on success, error message on failure
  retry_count INTEGER DEFAULT 0,    -- How many retries before success/failure
  fallback_used BOOLEAN DEFAULT false, -- Was the fallback model or value used?
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chat_traces_trace ON chat_traces(trace_id);
CREATE INDEX idx_chat_traces_message ON chat_traces(message_id);
CREATE INDEX idx_chat_traces_swarm ON chat_traces(swarm_id, created_at DESC);

-- No RLS — only accessible by service role (backend writes, admin reads)
```

### VERIFY STAGE 2:
```bash
# Run all migrations against Supabase
# Option A: Via Supabase CLI
supabase db push

# Option B: Via Supabase dashboard SQL editor
# Copy each file and run in order (001 through 010)

# Verify: Check that all tables exist
# Run in SQL editor:
SELECT table_name FROM information_schema.tables
WHERE table_schema IN ('public', 'fie')
ORDER BY table_schema, table_name;

# Expected: 40+ tables (including chat_traces from migration 010)

# (Decision 8) Write and run initial DB tests:
# backend/tests/test_migrations.py — verify all tables exist via Supabase client
cd backend && pytest tests/test_migrations.py -v
```

---

## STAGE 3: BACKEND CORE

This stage creates the foundation files that every other service depends on. Build these files exactly as specified — they set patterns that all subsequent stages follow.

### 3.1 Configuration (`app/core/config.py`)

```python
"""Central configuration — all env vars defined here."""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ── Required ──
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str          # (Decision 1) For verifying Supabase JWTs server-side
    GROQ_API_KEY: str
    OPENAI_API_KEY: str

    # ── Optional with defaults ──
    GROQ_API_KEYS: str = ""  # Comma-separated for rotation
    GROQ_MAX_CONCURRENT_REQUESTS: int = 10
    ADMIN_API_KEY: Optional[str] = None
    NUTRITIONIST_JWT_SECRET: Optional[str] = None  # Separate from ADMIN_API_KEY for nutritionist portal JWTs

    # ── Frontend ──
    FRONTEND_URL: str = "https://izana-chat.netlify.app"

    # ── Redis (Decision 2 — REQUIRED for task queue) ──
    REDIS_URL: str = "redis://localhost:6379"  # Upstash Redis URL in production

    # ── Email ──
    SENDGRID_API_KEY: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@izana.ai"

    # ── Cloudflare Stream ──
    CLOUDFLARE_ACCOUNT_ID: Optional[str] = None
    CLOUDFLARE_STREAM_TOKEN: Optional[str] = None

    # ── Feature Flags (Decision 11) ──
    FEATURE_BLOODWORK_ENABLED: bool = True
    FEATURE_PARTNER_ENABLED: bool = True
    FEATURE_FIE_ENABLED: bool = False      # Was FIE_ENABLED — renamed for consistency
    FEATURE_PUSH_ENABLED: bool = True

    # ── FIE ──
    FIE_ANONYMIZATION_SALT: str = ""
    FIE_MIN_CYCLES_FOR_INSIGHTS: int = 50

    # ── Admin ──
    NEXT_PUBLIC_ADMIN_EMAIL: str = "admin@izana.com"

    # ── App ──
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Claude Code: Now build the remaining core files.** For each file, follow the patterns from the master specification. The key files and their responsibilities:

| File | Build from Master Spec Section |
|------|-------------------------------|
| `app/core/database.py` | Supabase singleton client |
| `app/core/auth.py` | **(Decision 1)** JWT verification from `Authorization: Bearer` header. Extract user_id from `sub` claim. Verify with `SUPABASE_JWT_SECRET`. Also: `get_admin_key()` for admin endpoints. See Section M3 for full implementation. |
| `app/core/exceptions.py` | 23+ custom exceptions (master spec Part 1 backend architecture). **Add:** `EmptyResponseError`, `RefusalError`, `AllKeysExhaustedError`, `AllOCRFailedError` for swarm failures (Decision 5) |
| `app/core/model_config.py` | 4-category LLM registry with fallback chains |
| `app/core/validators.py` | Input sanitization, PII detection, 35+ injection patterns |
| `app/core/biomarker_config.py` | Reference ranges for 19+ biomarkers |
| `app/core/logging_config.py` | Structured JSON logging |
| `app/core/metrics.py` | Prometheus business metrics |
| `app/core/timeouts.py` | Operation timeout configuration |
| `app/core/correlation.py` | Request correlation ID via ContextVar |
| `app/core/task_queue.py` | **(Decision 2)** arq Redis connection pool, task enqueue helper |
| `app/core/feature_flags.py` | **(Decision 11)** Helper to check feature flags: `require_feature("bloodwork")` raises 503 with "Coming soon" if disabled |

**Also build the auth routes (Decision 7):**

| File | Purpose |
|------|---------|
| `app/api/auth_routes.py` | `POST /auth/signup` — server-side signup transaction (creates Supabase auth user + profile + gamification + recovery phrase in one call). `GET /auth/lookup` — always returns `{pseudonym}@users.izana.ai` regardless of existence (Decision 6). |

### VERIFY STAGE 3:
```bash
cd backend
python -c "from app.core.config import settings; print(settings.SUPABASE_URL)"
python -c "from app.core.database import get_supabase_client; print('DB OK')"
python -c "from app.core.exceptions import *; print('Exceptions OK')"
python -c "from app.core.model_config import MODEL_REGISTRY; print(f'{len(MODEL_REGISTRY)} model categories')"
python -c "from app.core.task_queue import get_redis_pool; print('Redis OK')"

# (Decision 8) Run Stage 3 tests:
pytest tests/test_auth.py -v
# Tests must include:
#   - test_jwt_accepts_valid_token
#   - test_jwt_rejects_expired_token
#   - test_jwt_rejects_forged_token
#   - test_jwt_rejects_missing_header
#   - test_signup_creates_all_records (profile + gamification + recovery phrase)
#   - test_signup_rolls_back_on_profile_failure
#   - test_lookup_returns_same_response_for_existing_and_nonexistent_pseudonym
#   - test_feature_flag_blocks_disabled_feature
```

---

## STAGES 4-22: CONTINUATION

**IMPORTANT NOTE TO CLAUDE CODE:**

Stages 4 through 22 follow the same pattern. For each stage:

1. **Read the relevant section of IZANA_MASTER_SPECIFICATION.md** — it contains the exact specifications, API contracts, component designs, and edge cases.

2. **Build files in the exact directory structure** specified in Stage 1.

3. **Follow the patterns established in Stage 3** — every service uses the same error handling, logging, and database access patterns.

4. **Run the VERIFY step** before proceeding to the next stage.

Here is the build order with references to the master spec:

### Stage 4: Swarm Pipeline
**Master Spec Reference:** Part 1 Section "Swarm Agent Architecture" + Part 4 Section 9

- Build `swarm_base.py` first — abstract base with:
  - Health metrics (call count, error count, latency)
  - **(Decision 5) Universal retry wrapper:** `async def execute_with_retry(self, messages, **kwargs)` — try the LLM call → validate output schema → if validation fails, retry once with a stricter prompt → if still fails, return `self.get_fallback_value()`. Each subclass implements `get_fallback_value()` returning its typed fallback:
    - Swarm 0 (Polyglot): return original text untranslated
    - Swarm 1 (Gatekeeper): return `{"safe": True, "is_fertility_related": True}` (fail-open)
    - Swarm 4 (Curator): return `"I couldn't answer that right now. Could you try rephrasing?"`
    - Swarm 7 (Compliance): return input unchanged (pass-through, don't block)
    - Swarm 9 (Context): return `{"summary": "", "phase": "unknown"}`
    - Swarm 8 (Gap): skip (no-op)
    - Swarm 10 (Sentiment): skip (no-op)
  - **(Decision 10) Automatic tracing:** Every `execute_with_retry()` call logs a row to `chat_traces` with: trace_id, swarm_id, input (truncated 2000 chars), output (truncated 2000 chars), model, tokens_in, tokens_out, latency_ms, error, retry_count, fallback_used
- Build each swarm using human-readable file names **(Decision 17)**:
  - `translator.py` (Swarm 0), `gatekeeper.py` (Swarm 1), `bloodwork_extractor.py` (Swarm 2)
  - `clinical_brain.py` (Swarm 3), `response_curator.py` (Swarm 4)
  - `bloodwork_analyser.py` (Swarm 5), `bloodwork_curator.py` (Swarm 6)
  - `compliance_checker.py` (Swarm 7), `gap_detector.py` (Swarm 8)
  - `context_builder.py` (Swarm 9), `sentiment_analyser.py` (Swarm 10)
  - Each class sets `swarm_id = "swarm_0_polyglot"` etc. for trace compatibility
- Build `groq_client.py` with multi-key rotation
- Build `swarm_health.py` for monitoring

**Swarm base implementation pattern (Decision 5):**
```python
# app/services/swarm_base.py

class SwarmBase(ABC):
    """Abstract base for all 11 swarms. Provides retry, fallback, and tracing."""

    swarm_id: str           # e.g., "swarm_0_polyglot"
    model: str              # e.g., "llama-3.3-70b-versatile"
    fallback_model: str     # e.g., "llama-3.1-8b-instant"
    temperature: float
    max_tokens: int
    timeout_seconds: int

    @abstractmethod
    def get_fallback_value(self) -> Any:
        """Return the safe fallback value when all retries fail."""
        ...

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """Validate the LLM output meets the expected schema."""
        ...

    async def execute_with_retry(
        self, messages: list, trace_id: UUID, **kwargs
    ) -> Any:
        """Try primary model → validate → retry with stricter prompt → fallback."""
        start = time.monotonic()
        retry_count = 0
        last_error = None

        for attempt in range(2):  # Max 2 attempts
            try:
                model = self.model if attempt == 0 else self.fallback_model
                response = await groq_client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                output = self._parse_response(response)

                if not output or not self.validate_output(output):
                    raise EmptyResponseError(f"{self.swarm_id} returned invalid output")

                await self._log_trace(trace_id, messages, output, model,
                    response.usage, time.monotonic() - start, None, retry_count, False)
                return output

            except (EmptyResponseError, ValidationError, JSON.ParserError) as e:
                retry_count += 1
                last_error = str(e)
                if attempt == 0:
                    messages = self._make_stricter_prompt(messages)
                    continue

            except (TimeoutError, RateLimitError, ServiceUnavailableError) as e:
                last_error = str(e)
                break  # Don't retry infra errors — go straight to fallback

        # All attempts failed — use fallback
        fallback = self.get_fallback_value()
        await self._log_trace(trace_id, messages, fallback, "fallback",
            None, time.monotonic() - start, last_error, retry_count, True)
        logger.warning(f"{self.swarm_id} used fallback after {retry_count} retries: {last_error}")
        return fallback
```

- **VERIFY:** Each swarm can be instantiated and returns mock responses

```bash
# (Decision 8) Run Stage 4 tests:
pytest tests/test_swarms.py -v
# Tests must include:
#   - test_swarm_base_retry_on_empty_response
#   - test_swarm_base_fallback_after_two_failures
#   - test_swarm_base_traces_logged_on_success
#   - test_swarm_base_traces_logged_on_failure
#   - test_gatekeeper_classifies_fertility_topic
#   - test_gatekeeper_rejects_off_topic
#   - test_polyglot_passes_through_english
#   - test_compliance_adds_disclaimer
#   - test_all_swarms_have_fallback_values
```

### Stage 5: RAG Engine
**Master Spec Reference:** Part 1 "RAG Engine (ClinicalBrain)"
- Build embedding generation (OpenAI text-embedding-3-small, 384 dimensions)
- Build vector search via Supabase `match_documents` RPC
- Build multi-query retrieval (3 variations, deduplicate, cross-query boost)
- Build 4-level graceful degradation
- **Run knowledge base ingestion:** `python scripts/ingest_docs.py` against the 236 PDFs
- **IMPORTANT:** Assert `len(embedding) == 384` before every storage operation. Dimension mismatch causes silent search failures (cosine distance returns garbage).
- **VERIFY:** Query "What should I eat during IVF stims?" returns relevant documents

```bash
# (Decision 8) Run Stage 5 tests:
pytest tests/test_rag.py -v
# Tests must include:
#   - test_embedding_dimension_is_384
#   - test_embedding_dimension_mismatch_raises_error
#   - test_multi_query_deduplication
#   - test_cross_query_score_boosting
#   - test_graceful_degradation_level_4_no_results
#   - test_graceful_degradation_level_2_low_confidence
#   - test_search_returns_relevant_docs_for_fertility_query
```

### Stage 6: Chat API
**Master Spec Reference:** Part 1 "Chat Data Flow" + Part 4 Section 3

**CRITICAL CHANGES FROM ARCHITECTURAL REVIEW:**

**(Decision 2) Task Queue Architecture:**
The chat pipeline does NOT run inline in the SSE endpoint. Instead:
1. `POST /chat/stream` receives the user message, validates, enqueues a task to the Redis task queue
2. The arq worker picks up the task, runs the full swarm pipeline (Steps 1-10)
3. The worker writes progress events to a Redis stream keyed by `task_id`
4. The SSE endpoint reads from the Redis stream and forwards events to the client
5. This decouples the HTTP connection from the LLM processing

**(Decision 12) Inline Fallback When Redis Is Down:**
If `redis.ping()` fails when the chat endpoint is called, fall back to running the pipeline
INLINE (synchronous, same process). This is slower but keeps the app functional:
```python
try:
    redis = get_redis()
    await redis.ping()
    # Normal path: enqueue to task queue
    await arq_pool.enqueue_job("chat_pipeline_task", task_id, user_id, content)
    return stream_from_redis(task_id)
except (ConnectionError, TimeoutError):
    logger.warning("Redis unavailable — running chat pipeline inline (Decision 12)")
    # Fallback path: run pipeline synchronously in this request
    return stream_inline_pipeline(user_id, content)
```
Background jobs (evening summaries, nudges, etc.) simply skip their run when Redis is
down and retry on the next cron trigger. The app degrades gracefully, not catastrophically.

**(Decision 9) Pipeline Reorder — Compliance BEFORE Streaming:**
The corrected pipeline order:
```
sanitize → PII → greeting → translate → gate → context → RAG →
curate (FULL response) → compliance (check/modify FULL response) →
translate back → THEN stream approved text token-by-token → background tasks
```
The user NEVER sees unchecked medical content. The search animation ("Crafting your answer...") covers the ~0.5s compliance check latency.

- Build the task queue chat worker (`app/workers/chat_tasks.py`)
- Build the SSE endpoint that polls the Redis stream for task progress
- Build REST fallback (same task queue, but blocks and returns the complete response)
- Build the 12-step pipeline inside the worker, NOT the endpoint
- **VERIFY:** Send a chat message and get a sourced response

```bash
# (Decision 8) Run Stage 6 tests:
pytest tests/test_chat_pipeline.py -v
# Tests must include:
#   - test_chat_enqueues_task_to_redis
#   - test_sse_streams_events_from_redis
#   - test_compliance_runs_before_token_streaming
#   - test_user_never_sees_unchecked_response
#   - test_pii_detection_blocks_personal_info
#   - test_gatekeeper_rejects_off_topic
#   - test_rag_sources_appear_in_response
#   - test_medical_disclaimer_present_on_clinical_response
#   - test_client_disconnect_cleans_up_resources
#   - test_rate_limiting_enforced
```

### Stage 7: Bloodwork Pipeline
**Master Spec Reference:** Part 1 "Bloodwork Pipeline"
- Build file upload to Supabase Storage (accept PDF, JPG, PNG, HEIC — A6.2)
- Build PDF extraction (PyMuPDF) + OCR (Vision client with Groq → OpenAI fallback)
- Build Swarm 2 structured extraction (using `bloodwork_extractor.py` — Decision 17)
- Build confirmation + analysis pipeline
- Gate behind `FEATURE_BLOODWORK_ENABLED` flag (Decision 11) using router dependency (A6.2)
- **VERIFY:** Upload a test PDF, extract values, confirm, get analysis

```bash
# (Decision 8) Run Stage 7 tests:
pytest tests/test_bloodwork.py -v
# Tests must include:
#   - test_upload_accepts_pdf_jpg_png_heic
#   - test_upload_rejects_exe_doc_zip
#   - test_upload_rejects_over_5mb
#   - test_pdf_text_extraction_returns_biomarkers
#   - test_ocr_fallback_when_groq_vision_fails
#   - test_biomarker_parsing_edge_values (0, negative, missing units)
#   - test_reference_range_comparison (normal, high, low)
#   - test_feature_flag_disabled_returns_503
```

### Stage 8: All Remaining Backend APIs
**Master Spec Reference:** Part 4 Sections 5-8
- Build ALL API routers listed in the directory structure
- Each endpoint follows the pattern: validate → JWT auth (Decision 1) → service call → response
- Apply feature flags as router-level dependencies (A6.2), NOT per-route checks:
  ```python
  bloodwork_router = APIRouter(dependencies=[Depends(require_feature("bloodwork"))])
  partner_router = APIRouter(dependencies=[Depends(require_feature("partner"))])
  ```
- Add account lockout logic to login flow (A6.2): 5 failed attempts per pseudonym in 15 min → block
- Add `POST /recovery/regenerate` endpoint (Decision 14): requires current password, returns new phrase
- Add pagination to `/chapters/{id}/messages` (A6.2): `?page=1&per_page=100` with cursor-based pagination
- Refer to the complete endpoint map in the master spec
- **VERIFY:** Every endpoint returns correct status codes for valid/invalid requests

```bash
# (Decision 8) Run Stage 8 tests:
pytest tests/test_api_endpoints.py -v
# Tests must include:
#   - test_all_endpoints_require_jwt_auth
#   - test_feature_flag_disabled_returns_503_with_message
#   - test_account_lockout_after_5_failures
#   - test_account_lockout_resets_after_15_minutes
#   - test_recovery_regenerate_requires_correct_password
#   - test_recovery_regenerate_invalidates_old_phrase
#   - test_pagination_returns_correct_page_size
#   - test_meal_log_dedup_prevents_double_logging
```

### Stage 9: Background Jobs + Nudge Engine
**Master Spec Reference:** Part 1 "Background Jobs" + "Nudge Engine"

**(Decision 4) ALL background jobs use the Redis + arq task queue from Decision 2.**
Scheduled triggers use Render Cron Jobs, which hit authenticated HTTP endpoints (`X-Admin-API-Key` header) that enqueue tasks into the same arq queue.

**Architecture:**
```
Render Cron Job (e.g., "0 * * * *")
    │
    ▼
POST /api/v1/jobs/evening-summaries  (X-Admin-API-Key header)
    │
    ▼
app/api/jobs.py → enqueues task to Redis
    │
    ▼
app/workers/scheduled_tasks.py → arq worker picks up and runs
```

**Cron schedule (all times UTC, jobs convert to user timezone):**
| Cron Expression | Job | Notes |
|-----------------|-----|-------|
| `*/30 * * * *` | Phase transition checks | Every 30 min |
| `0 * * * *` | Evening summary generation | Hourly, filters by user timezone |
| `0 * * * *` | Plan overdue escalation | Hourly, checks queue depth |
| `*/5 * * * *` | Nudge delivery | Every 5 min, processes nudge_queue |
| `0 3 * * *` | FIE feature extraction | Daily 3am UTC |
| `0 3 * * *` | Landing page cache refresh | Daily 3am UTC |
| `0 4 * * 0` | FIE insight discovery | Weekly Sunday 4am UTC |
| `0 2 * * 0` | Data lifecycle archival | Weekly Sunday 2am UTC |
| `0 2 * * 0` | Chat traces retention (Decision 20) | Weekly Sunday 2am UTC — delete rows >90 days |
| `0 1 * * *` | Disengagement sensing | Daily 1am UTC |

- Build `app/api/jobs.py` — authenticated endpoints that enqueue each job type
- Build `app/workers/scheduled_tasks.py` — arq task functions for each job
- Build the nudge engine with `chat_card` delivery channel
- Build disengagement sensing service
- Build phase transition scheduling service
- **VERIFY:** Jobs can be triggered manually via HTTP and produce correct effects

```bash
# (Decision 8) Run Stage 9 tests:
pytest tests/test_jobs.py -v
# Tests must include:
#   - test_job_endpoints_require_admin_key
#   - test_evening_summary_filters_by_timezone
#   - test_nudge_respects_disengagement_silence
#   - test_phase_transition_check_triggers_at_80_percent
#   - test_plan_overdue_escalation_after_4_hours
```

### Stage 10: Frontend Shell
**Master Spec Reference:** Part 4 Section 1 (Design System) + Section 2 (UI/UX)
- Apply the COMPLETE design system from the master spec (all CSS custom properties)
- Build the root layout with theme support (light/dark/system)
- Build `BottomNav` (3 text-only tabs: Today | Journey | You)
- Build base UI components (button, input, card, etc.)
- Install Inter + DM Serif Display fonts
- **VERIFY:** App loads with correct colors, fonts, and bottom nav in both light and dark mode

### Stage 11: Landing Page
**Master Spec Reference:** Part 2 "Stage 0: Value Showcase" + Part 4 Section 3
- Build `LandingPage.tsx` with the exact layout from spec
- Build `PreviewChat.tsx` with rate-limited backend endpoint
- Build `SocialProofStrip.tsx`
- Language selector (11 languages)
- **VERIFY:** Landing page loads, preview chat works, responsive on 375px

### Stage 12: Identity + Onboarding
**Master Spec Reference:** Part 2 "Stage 1" + "Stage 2" + "Stage 3"
- Build `IdentityCreator.tsx` (pseudonym + avatar + sex + password)
- Build `RecoveryPhrase.tsx`
- Build `ConversationalOnboarding.tsx` with full state machine (30+ steps)
- Build partner invitation flow
- **VERIFY:** Complete onboarding flow end-to-end, user exists in Supabase

### Stage 13: Chat Interface + Chapters
**Master Spec Reference:** Part 1 Sections 2-4 + Part 4 Section 4
- Build `ChatInterface.tsx` (the main screen)
- Build `ChapterHeader.tsx` with phase, day counter, streak
- Build `WeeklyGroup.tsx` with accordion expand/collapse
- Build `DaySeparator.tsx`
- Build `ChatMessageList.tsx` with virtualized rendering
- Build `useStreamingChat.ts` hook
- Build `useChapter.ts` + `useWeeklyGroups.ts` hooks
- **VERIFY:** Chat works with SSE streaming, messages appear in weekly groups

### Stage 14: Card System
**Master Spec Reference:** Part 4 Section 4 + Part 5 Section 14
- Build `ChatCard.tsx` (polymorphic renderer)
- Build ALL 11 card types one at a time
- Apply micro-interactions from master spec Section 14
- **VERIFY:** Each card type renders correctly with proper animations

### Stage 15: Content CMS + Streaming
**Master Spec Reference:** Part 1 Section 6 + Part 3 (Content Library) + Part 4 Section 5
- Set up Cloudflare Stream account and API integration
- Build `cloudflare_stream.py` backend service
- Build `ContentManagerTab.tsx` admin component
- Build `MediaPlayer.tsx` with hls.js
- Upload all exercise videos and meditation audios
- **VERIFY:** Admin can upload, tag, and manage content; user can play inline

### Stage 16: Nutritionist Portal
**Master Spec Reference:** Part 1 "Nutritionist Portal" + Part 4 Section 6
- Build nutritionist login + auth guard
- Build queue view with priority sorting
- Build 3-panel review editor
- Build approve/modify/reject workflow
- **VERIFY:** Nutritionist can log in, see queue, review and approve a plan

### Stage 17: Admin Dashboard
**Master Spec Reference:** Part 1 "Admin Dashboard" + Part 4 Section 5
- Build all 8 tabs (Dashboard, Analytics, Feedback, Training, Health, Prompts, Content Manager, Plan Queue)
- **VERIFY:** Admin dashboard loads with data from all tabs

### Stage 18: Partner System
**Master Spec Reference:** Part 1 Section 11.5 (Partner Experience)
- Build partner onboarding (abbreviated)
- Build partner chapter sync
- Build `PartnerCard.tsx`
- Build couple goals + couple streaks
- **VERIFY:** Two test accounts can link, see each other's data, send encouragement

### Stage 19: Provider Portal
**Master Spec Reference:** Part 1 Section 7 + Part 4 Section 7
- Build `ShareModal.tsx`
- Build `report_generator.py` (PDF via reportlab)
- Build `/portal/{token}` web view
- Build PHI audit logging
- **VERIFY:** Generate share link, open portal, download PDF

### Stage 20: FIE Pipeline
**Master Spec Reference:** Part 5 Section 13
- Build all FIE service files in `app/services/fie/`
- Build FIE background jobs
- Build FIE admin dashboard section
- **VERIFY:** Feature extraction runs on test data, produces anonymized records

### Stage 21: Offline + PWA + Capacitor
**Master Spec Reference:** Part 1 Section 11.1 + Part 4 Section 2
- Build service worker (`sw.js`)
- Build IndexedDB offline store
- Build `OfflineQueue.tsx` + `OfflineBanner.tsx`
- Build PWA manifest
- Add Capacitor 8 (iOS + Android)
- **VERIFY:** App works offline (can check in, log meals), syncs on reconnect

### Stage 22: E2E Tests + Deployment

**(Decision 8) Note:** Unit and integration tests have been written alongside each stage (Stages 3-21). By this point, the test suite already covers auth, swarms, RAG, chat pipeline, plans, bloodwork, jobs, and all API endpoints. Stage 22 focuses on:

**E2E tests ONLY (Playwright):**
- Write E2E tests for the 5 critical user flows:
  1. Landing → signup → onboarding → grand reveal → chat
  2. Chat message → search animation → streaming response with sources
  3. Bloodwork upload → extraction confirmation → analysis display
  4. Nutritionist login → queue → review → approve → user receives plan
  5. Phase transition → new chapter → new plan generation
- Write E2E responsive tests (375px iPhone SE viewport)
- Write E2E light/dark mode visual regression tests

**Deployment:**
- Deploy frontend to Netlify (custom domain: chat.izana.ai)
- Deploy backend to Render (Singapore region):
  - **Web Service:** FastAPI (uvicorn, 4 workers)
  - **Worker Service:** arq worker (processes task queue) — **(Decision 2)**
  - **Cron Jobs:** Render Cron triggers for all scheduled tasks — **(Decision 4)**
  - **Redis:** Render Redis or Upstash Redis
- Configure all production env vars (including `SUPABASE_JWT_SECRET`, `REDIS_URL`, feature flags)
- Configure DNS for chat.izana.ai
- Set up monitoring (Prometheus metrics endpoint on Render)
- Run the full backend test suite against production database (read-only assertions)
- **VERIFY:** Full end-to-end flow works in production: landing → signup → onboarding → chat → plan delivery → daily rhythm

```bash
# Run all accumulated tests (Stages 3-21):
cd backend && pytest --tb=short -q    # All backend unit + integration tests
cd ../frontend && npx vitest --run    # All frontend unit tests

# Run E2E tests:
cd frontend && npx playwright test    # All Playwright E2E tests

# Post-deploy smoke tests:
curl -s https://api.izana.ai/health | jq .status    # Should return "healthy"
curl -s https://chat.izana.ai | head -1              # Should return HTML
```

---

## HOW TO USE THIS GUIDE WITH CLAUDE CODE

### Session Strategy

This build is too large for a single Claude Code session. Break it into sessions:

| Session | Stages | Estimated Time |
|---------|--------|----------------|
| Session 1 | Stages 1-3 (Setup + Database + Core) | 2-3 hours |
| Session 2 | Stages 4-5 (Swarm Pipeline + RAG) | 3-4 hours |
| Session 3 | Stage 6-7 (Chat API + Bloodwork) | 2-3 hours |
| Session 4 | Stages 8-9 (All APIs + Jobs) | 3-4 hours |
| Session 5 | Stages 10-12 (Frontend Shell + Landing + Onboarding) | 3-4 hours |
| Session 6 | Stages 13-14 (Chat Interface + Cards) | 4-5 hours |
| Session 7 | Stage 15 (Content CMS + Streaming) | 2-3 hours |
| Session 8 | Stages 16-17 (Nutritionist + Admin) | 3-4 hours |
| Session 9 | Stages 18-19 (Partner + Provider Portal) | 2-3 hours |
| Session 10 | Stages 20-21 (FIE + Offline + Capacitor) | 3-4 hours |
| Session 11 | Stage 22 (Testing + Deployment) | 2-3 hours |

### What to Tell Claude Code at the Start of Each Session

```
I'm building Izana Chat from scratch. The complete build guide is:
IZANA_COMPLETE_BUILD_GUIDE_FINAL.md (this is the ONE document).

IMPORTANT: Read Sections A5 AND A6 FIRST.
They contain 20 critical decisions (11 architectural + 9 engineering)
that override conflicting specs elsewhere in the document. Covers:
JWT auth, task queue, Redis fallback, compliance ordering, test-per-stage,
feature flags, gamification points, i18n type safety, account lockout,
phase skipping, recovery phrase regeneration, and more.

I'm on [Stage X]. My previous session completed through [Stage X-1]
and all VERIFY steps + tests passed.

Please build Stage [X] now, following the build guide exactly.
Create all files, write the tests specified in the VERIFY step,
then run both the VERIFY commands and the test suite.
```

### Critical Reminders for Every Session

```
╔══════════════════════════════════════════════════════════════════════╗
║ 1. Read Sections A5 AND A6 (Architectural + Eng Decisions) FIRST. ║
║    They contain 20 decisions that override conflicting specs.      ║
║ 2. Follow the directory structure from Stage 1 EXACTLY.            ║
║ 3. Run VERIFY + TESTS after each stage before proceeding.          ║
║    (Decision 8: tests are written alongside each stage)            ║
║ 4. Every component must support light AND dark mode.               ║
║ 5. Every API endpoint uses JWT auth (Decision 1), NOT X-User-ID.  ║
║ 6. Every frontend component must work at 375px width.              ║
║ 7. User must NEVER see a plan not approved by nutritionist.        ║
║ 8. FIE writes ONLY to fie.* tables — never production data.       ║
║ 9. Apply microcopy from master spec Section 14 everywhere.         ║
║ 10. Commit to git after each successful VERIFY.                    ║
║ 11. All heavy work (chat pipeline, plan generation, bloodwork)     ║
║     goes through the Redis + arq task queue (Decision 2).          ║
║ 12. Compliance check (Swarm 7) runs BEFORE token streaming         ║
║     (Decision 9). User never sees unchecked medical content.       ║
║ 13. Check feature flags before processing optional features        ║
║     (Decision 11: FEATURE_BLOODWORK_ENABLED, etc.).                ║
║ 14. ALL React components are client components — NO server         ║
║     components (Decision 3).                                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## QUICK REFERENCE: KEY DECISIONS

### Original Tech Decisions
| Decision | Choice | Reason |
|----------|--------|--------|
| State management | Zustand | Simpler than Context chains, devtools, persist middleware |
| API client | Axios + SWR | Retry logic + client-side caching with revalidation |
| Styling | Tailwind + CSS custom properties | Utility classes + theme tokens for light/dark |
| Forms | Controlled components (not form libraries) | Chat-native inputs, not traditional forms |
| Animation | Framer Motion | Declarative, performant, `prefers-reduced-motion` support |
| Icons | Lucide React | Consistent, lightweight, tree-shakeable |
| Charts | Recharts | Already proven in existing codebase |
| Markdown | react-markdown + remark-gfm | Chat message rendering |
| Offline | idb (IndexedDB wrapper) | Type-safe, promise-based, lightweight |
| Mobile | Capacitor 8 | Native iOS/Android from same codebase |
| Video | hls.js + Cloudflare Stream | Adaptive bitrate, global CDN, simple pricing |
| Testing | Vitest (unit) + Playwright (E2E) | Fast, modern, Next.js integrated |

### Architectural Review Decisions (Section A5)
| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Authentication | Server-side JWT verification | X-User-ID header was forgeable — any user could impersonate any other user |
| 2 | Concurrency | Redis + arq task queue | Single-process FastAPI bottlenecks at ~50 concurrent chat users |
| 3 | Rendering | All client components (no RSC) | Server Components conflict with Capacitor static export |
| 4 | Background jobs | Task queue + Render Cron | No job runner was specified; consolidate on one pattern |
| 5 | LLM failures | Universal retry wrapper in swarm_base.py | 10 unrescued error paths (empty response, bad JSON, refusal) |
| 6 | Login security | /auth/lookup always returns same response | Only ~13,000 pseudonym combinations — trivially enumerable |
| 7 | Signup atomicity | Server-side transaction endpoint | Network drop after auth.signUp but before profile insert = broken state |
| 8 | Testing | Tests written per stage, not deferred | 30+ hours of code before any test is too risky for medical data |
| 9 | Compliance order | Check before streaming | User would see unchecked medical content then see it change |
| 10 | Observability | chat_traces table | No way to debug "Izana gave wrong advice" reports |
| 11 | Feature flags | Env-var boolean flags | Full rollback is the only option if one feature breaks |

### Engineering Review Decisions (Section A6)
| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 12 | Redis resilience | Upstash Redis + inline fallback | Redis SPOF would take down entire app; fallback keeps chat working |
| 13 | Phase transitions | Allow non-sequential with skip confirmation | Users skip phases in real life (e.g., stims → retrieval, no trigger) |
| 14 | Account recovery | Recovery phrase regeneration while logged in | Lost phrase = permanent account loss with no mitigation |
| 15 | Gamification | Complete point schedule + badge criteria defined | Undefined scoring prevents consistent frontend/backend implementation |
| 16 | Chat length | 2000-char limit (was 500) | Fertility questions with med names/dosages/bloodwork values exceed 500 |
| 17 | File naming | Human-readable swarm files (translator.py not swarm_0_polyglot.py) | Numeric indices meaningless to new developers |
| 18 | i18n safety | Type-safe translation keys (en.ts as base type) | Adding English strings silently breaks 10 languages (blank text) |
| 19 | Test mocking | Deterministic mock Groq client with fixture responses | Tests must be fast, deterministic, no API calls, cover retry/fallback |
| 20 | Data retention | 90-day chat_traces retention with weekly cleanup | ~2.4M rows/month, ~10GB/month unbounded growth |

---

*This is the complete build guide. It contains everything needed to build Izana from an empty directory: product spec, design system, architecture, 20 architectural decisions, and execution-level requirements.*

---

# SECTION G: FERTILITY INTELLIGENCE ENGINE (FIE)

## 13. FERTILITY INTELLIGENCE ENGINE (FIE)

### 13.1 Purpose & Strategic Value

The Fertility Intelligence Engine is Izana's long-term competitive moat. It is a **completely independent system** that reads from the production database but writes only to its own isolated tables. It never modifies user-facing data. Its purpose is threefold:

1. **Generate training data** for a proprietary fertility outcome prediction model
2. **Discover correlations** between lifestyle interventions (nutrition, exercise, meditation adherence) and treatment outcomes that no academic study has access to (because no study has daily behavioral + biomarker + outcome data at this granularity)
3. **Continuously improve plan personalization** by feeding insights back to the nutrition swarms as enriched context

```
╔══════════════════════════════════════════════════════════════════╗
║ CRITICAL: The FIE is READ-ONLY on production data.             ║
║ It NEVER modifies chat_logs, profiles, personalized_plans,     ║
║ or any user-facing table. It writes ONLY to fie_* tables.      ║
║ It runs in a separate process / background job context.        ║
║ It can be disabled entirely without affecting any user feature.║
╚══════════════════════════════════════════════════════════════════╝
```

### 13.2 Architecture: Independent Data Pipeline

```
Production Database (READ-ONLY)
    │
    ├── profiles (demographics, bloodwork, wellness)
    ├── treatment_journeys (phases, transitions, dates)
    ├── chapters (phase durations, outcomes)
    ├── cycles (multi-cycle data, outcomes)
    ├── symptom_logs + emotion_logs (daily check-ins)
    ├── meal_logs + activity_logs (plan adherence)
    ├── content_progress (exercise/meditation completion)
    ├── personalized_plans (plan content, versions)
    ├── plan_modifications (nutritionist corrections)
    ├── bloodwork_snapshots (biomarker trends)
    ├── dpo_logs + dpo_feedback_details (response quality)
    ├── population_insights (aggregate trends)
    │
    ▼
┌─────────────────────────────────────────────┐
│         FERTILITY INTELLIGENCE ENGINE        │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  STAGE 1: Feature Extraction         │   │
│  │  (Daily ETL job — 3am UTC)           │   │
│  │                                      │   │
│  │  Reads production tables             │   │
│  │  Extracts & anonymizes features      │   │
│  │  Writes to fie_feature_store         │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  STAGE 2: Training Data Generation   │   │
│  │  (Weekly job — Sunday 4am UTC)       │   │
│  │                                      │   │
│  │  Creates feature vectors from        │   │
│  │  completed cycles with known outcomes│   │
│  │  Writes to fie_training_data         │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  STAGE 3: Insight Discovery          │   │
│  │  (Weekly job — Sunday 5am UTC)       │   │
│  │                                      │
│  │  Correlation analysis between        │   │
│  │  adherence patterns and outcomes     │   │
│  │  Writes to fie_insights              │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  STAGE 4: Model Training (Future)    │   │
│  │  (Monthly or on-demand)              │   │
│  │                                      │   │
│  │  Train/retrain prediction models     │   │
│  │  Export for external training if      │   │
│  │  needed (JSONL, anonymized)          │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  STAGE 5: Feedback Loop              │   │
│  │  (Continuous, read by swarms)        │   │
│  │                                      │   │
│  │  fie_insights readable by Swarm 4    │   │
│  │  and Nutrition Swarms for enriched   │   │
│  │  plan generation context             │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 13.3 Feature Taxonomy

The FIE extracts and tracks these feature categories. All features are **anonymized** — no pseudonym, no user_id in training data, only a hashed anonymous_cycle_id.

#### Category A: Demographic & Baseline (static per cycle)
| Feature | Source | Type |
|---------|--------|------|
| age_range | profiles | categorical |
| bmi | profiles (calculated) | continuous |
| treatment_type | cycles | categorical |
| health_conditions | profiles.wellness | categorical[] |
| smoking_status | profiles.wellness | categorical |
| alcohol_consumption | profiles.wellness | categorical |
| sleep_duration | profiles.wellness | categorical |
| sleep_quality | profiles.wellness | categorical |
| stress_level | profiles.wellness | categorical |
| hydration | profiles.wellness | categorical |
| fitness_level | profiles.wellness | categorical |
| cycle_number | cycles | integer |
| previous_cycle_outcome | cycles (previous) | categorical |

#### Category B: Biomarkers (per cycle, from bloodwork)
| Feature | Source | Type |
|---------|--------|------|
| amh | profiles.core_fertility_json | continuous |
| fsh | profiles.core_fertility_json | continuous |
| lh | profiles.core_fertility_json | continuous |
| estradiol | profiles.core_fertility_json | continuous |
| progesterone | profiles.core_fertility_json | continuous |
| tsh | profiles.core_fertility_json | continuous |
| vitamin_d | profiles.core_fertility_json | continuous |
| testosterone_total | profiles.core_fertility_json | continuous |
| prolactin | profiles.core_fertility_json | continuous |
| all_extended_panels | profiles.extended_bloodwork_json | continuous[] |
| biomarker_delta (vs previous cycle) | bloodwork_snapshots | continuous |

#### Category C: Behavioral (daily, aggregated per phase and per cycle)
| Feature | Source | Aggregation |
|---------|--------|-------------|
| meal_adherence_pct | meal_logs vs personalized_plans | % per phase |
| meal_quality_score | meal_logs.followed_plan + satisfaction | avg per phase |
| exercise_completion_pct | activity_logs + content_progress | % per phase |
| exercise_minutes_avg | activity_logs.duration | avg per day per phase |
| meditation_completion_pct | content_progress (meditation type) | % per phase |
| checkin_consistency | symptom_logs + emotion_logs | % days checked in per phase |
| mood_avg | emotion_logs.mood | avg per phase (encoded 1-5) |
| mood_trend | emotion_logs.mood | slope (improving/declining) per phase |
| anxiety_avg | emotion_logs.anxiety | avg per phase |
| hope_avg | emotion_logs.hope | avg per phase |
| energy_avg | emotion_logs.energy | avg per phase |
| overwhelm_avg | emotion_logs.overwhelm | avg per phase |
| symptom_severity_index | symptom_logs | composite score per phase |
| plan_overall_adherence | composite of meal + exercise + meditation | weighted avg per cycle |
| days_active_pct | any log entry per day | % of phase days with activity |
| disengagement_events | gaps > 2 days with no interaction | count per cycle |
| content_engagement_score | content_progress (videos + audios) | completion rate |

#### Category D: Treatment Process (from journey/chapters)
| Feature | Source | Type |
|---------|--------|------|
| phase_duration_actual | chapters | integer (days per phase) |
| phase_duration_vs_expected | chapters vs phase_durations | ratio |
| stim_days (if IVF) | chapters | integer |
| total_cycle_duration | cycles | integer (days) |
| nutritionist_plan_modifications | plan_modifications | count + severity |
| plan_modification_categories | plan_modifications.category | categorical[] |

#### Category E: Outcome (target variable)
| Feature | Source | Type |
|---------|--------|------|
| outcome | cycles.outcome | categorical: POSITIVE, NEGATIVE, CHEMICAL, MISCARRIAGE, ECTOPIC, CANCELLED |
| outcome_binary | derived | 1 = POSITIVE, 0 = all others |
| time_to_outcome | cycle started_at → outcome recorded | integer (days) |

### 13.4 Database Tables (FIE-specific)

```sql
-- All FIE tables are in a separate schema for isolation
CREATE SCHEMA IF NOT EXISTS fie;

-- Feature store: anonymized, per-cycle feature vectors
CREATE TABLE fie.feature_store (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT NOT NULL, -- SHA-256 hash of user_id + cycle_id + salt
  treatment_type TEXT NOT NULL,
  cycle_number INTEGER,
  features_demographic JSONB,   -- Category A
  features_biomarker JSONB,     -- Category B
  features_behavioral JSONB,    -- Category C (aggregated per phase)
  features_treatment JSONB,     -- Category D
  outcome TEXT,                 -- Category E (NULL if cycle not complete)
  outcome_binary INTEGER,       -- 1/0/NULL
  cycle_completed BOOLEAN DEFAULT false,
  extracted_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(anonymous_cycle_id)
);

-- Training data: completed cycles with known outcomes, ready for ML
CREATE TABLE fie.training_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT NOT NULL,
  feature_vector JSONB NOT NULL, -- Flattened, normalized feature vector
  target_outcome INTEGER NOT NULL, -- 1 = positive, 0 = negative
  treatment_type TEXT NOT NULL,
  quality_score DECIMAL, -- Data completeness (0-1, higher = more features available)
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Insights: discovered correlations
CREATE TABLE fie.insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_type TEXT NOT NULL CHECK (insight_type IN (
    'adherence_outcome_correlation',
    'biomarker_behavior_correlation',
    'phase_duration_outcome',
    'lifestyle_factor_impact',
    'plan_modification_pattern',
    'symptom_outcome_predictor',
    'content_engagement_impact'
  )),
  treatment_type TEXT,
  phase TEXT,
  description TEXT NOT NULL,
  statistical_significance DECIMAL, -- p-value
  effect_size DECIMAL,
  sample_size INTEGER,
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  actionable BOOLEAN DEFAULT false, -- Can this be used to improve plans?
  insight_data JSONB, -- Raw correlation data
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Model registry: track trained models
CREATE TABLE fie.model_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  treatment_type TEXT,
  algorithm TEXT, -- xgboost, random_forest, neural_net, etc.
  features_used TEXT[], -- Which features the model uses
  training_samples INTEGER,
  metrics JSONB, -- { auc, accuracy, precision, recall, f1 }
  model_artifact_path TEXT, -- Path to serialized model
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Export log: audit trail for training data exports
CREATE TABLE fie.export_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exported_by TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  treatment_type_filter TEXT,
  quality_threshold DECIMAL,
  format TEXT DEFAULT 'jsonl',
  export_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- No RLS on fie.* tables — only accessible by admin/service role
```

### 13.5 Backend Implementation

**New service: `app/services/fie/`** (separate directory for isolation)

```
app/services/fie/
  __init__.py
  feature_extractor.py      # Stage 1: Read production → extract features
  training_generator.py     # Stage 2: Create training vectors
  insight_engine.py         # Stage 3: Correlation discovery
  model_trainer.py          # Stage 4: Train/evaluate models
  feedback_provider.py      # Stage 5: Serve insights to swarms
  anonymizer.py             # Hash user_id + cycle_id for privacy
  feature_config.py         # Feature definitions, normalization rules
```

**Key implementation details for Claude Code:**

```python
# app/services/fie/anonymizer.py
import hashlib
from app.core.config import settings

FIE_SALT = settings.FIE_ANONYMIZATION_SALT  # New env var, random 64-char string

def anonymize_cycle(user_id: str, cycle_id: str) -> str:
    """One-way hash. Cannot be reversed to identify user."""
    raw = f"{user_id}:{cycle_id}:{FIE_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

```python
# app/services/fie/feature_extractor.py
class FeatureExtractor:
    """
    Stage 1: Extract and anonymize features from production data.
    
    RULES:
    - READ-ONLY on production tables
    - Writes ONLY to fie.feature_store
    - All user identifiers are hashed before storage
    - Runs as a background job, never in request context
    - Can be disabled via FIE_ENABLED=false env var
    """
    
    async def extract_cycle_features(self, user_id: str, cycle_id: str) -> dict:
        """Extract all features for a single cycle."""
        anon_id = anonymize_cycle(user_id, cycle_id)
        
        # Category A: Demographics
        profile = await self._get_profile(user_id)
        demographics = {
            "age_range": profile.get("age_range"),
            "bmi": self._calculate_bmi(profile),
            "health_conditions": profile.get("health_conditions", []),
            "smoking": profile.get("smoking_status"),
            "alcohol": profile.get("alcohol_consumption"),
            "sleep_duration": profile.get("sleep_duration"),
            "sleep_quality": profile.get("sleep_quality"),
            "stress": profile.get("stress_level"),
            "hydration": profile.get("hydration"),
            "fitness": profile.get("fitness_level"),
        }
        
        # Category B: Biomarkers
        bloodwork = await self._get_bloodwork(user_id)
        biomarkers = self._extract_biomarkers(bloodwork, profile.get("gender"))
        
        # Category C: Behavioral (aggregated per phase)
        behavioral = await self._extract_behavioral(user_id, cycle_id)
        
        # Category D: Treatment process
        treatment = await self._extract_treatment_features(user_id, cycle_id)
        
        # Category E: Outcome
        cycle = await self._get_cycle(cycle_id)
        outcome = cycle.get("outcome") if cycle.get("completed_at") else None
        
        return {
            "anonymous_cycle_id": anon_id,
            "treatment_type": cycle.get("treatment_type"),
            "cycle_number": cycle.get("cycle_number"),
            "features_demographic": demographics,
            "features_biomarker": biomarkers,
            "features_behavioral": behavioral,
            "features_treatment": treatment,
            "outcome": outcome,
            "outcome_binary": 1 if outcome == "POSITIVE" else (0 if outcome else None),
            "cycle_completed": outcome is not None,
        }
    
    async def _extract_behavioral(self, user_id: str, cycle_id: str) -> dict:
        """Aggregate behavioral data per phase within a cycle."""
        chapters = await self._get_chapters_for_cycle(cycle_id)
        phase_data = {}
        
        for chapter in chapters:
            phase = chapter["phase"]
            phase_days = (chapter["ended_at"] or datetime.now()) - chapter["started_at"]
            
            # Meal adherence
            meal_logs = await self._count_meal_logs(user_id, chapter["started_at"], chapter.get("ended_at"))
            plan_meals = self._expected_meals(phase_days.days)
            
            # Exercise + meditation
            exercise_completions = await self._count_content_completions(
                user_id, chapter["started_at"], chapter.get("ended_at"), "exercise_video")
            meditation_completions = await self._count_content_completions(
                user_id, chapter["started_at"], chapter.get("ended_at"), "meditation_audio")
            
            # Mood and emotions
            emotions = await self._get_emotion_data(user_id, chapter["started_at"], chapter.get("ended_at"))
            
            # Check-in consistency
            checkin_days = await self._count_checkin_days(user_id, chapter["started_at"], chapter.get("ended_at"))
            
            phase_data[phase] = {
                "meal_adherence_pct": meal_logs / max(plan_meals, 1),
                "exercise_completion_pct": exercise_completions / max(phase_days.days, 1),
                "meditation_completion_pct": meditation_completions / max(phase_days.days, 1),
                "checkin_consistency": checkin_days / max(phase_days.days, 1),
                "mood_avg": self._avg(emotions, "mood"),
                "mood_trend": self._trend(emotions, "mood"),
                "anxiety_avg": self._avg(emotions, "anxiety"),
                "hope_avg": self._avg(emotions, "hope"),
                "energy_avg": self._avg(emotions, "energy"),
                "overwhelm_avg": self._avg(emotions, "overwhelm"),
                "days_active_pct": checkin_days / max(phase_days.days, 1),
            }
        
        # Also compute cycle-level aggregates
        phase_data["_cycle_aggregate"] = self._aggregate_across_phases(phase_data)
        return phase_data
```

### 13.6 Insight Discovery (Stage 3)

The insight engine runs weekly and discovers correlations like:

- "Users with >80% meal adherence during STIMS have 23% higher positive outcome rate" (sample: 500 cycles, p<0.01)
- "Meditation completion during TWW correlates with lower anxiety scores (r=0.42) and 15% fewer disengagement events"
- "BMI between 20-25 combined with daily exercise shows strongest positive outcome correlation for IVF"
- "Users whose nutritionist modified the plan for allergen safety have no difference in outcome vs unmodified plans (reassuring)"
- "Phase duration exceeding max_days in STIMS correlates with 12% lower positive outcome (may indicate poor response)"

```python
# app/services/fie/insight_engine.py
class InsightEngine:
    """Discover correlations between behavior, biomarkers, and outcomes."""
    
    async def run_weekly_analysis(self):
        """Run all insight analyses. Writes to fie.insights."""
        completed_cycles = await self._get_completed_cycles(min_quality=0.5)
        
        if len(completed_cycles) < 50:
            logger.info("Insufficient data for insights (<50 completed cycles)")
            return
        
        insights = []
        
        # Adherence → Outcome correlations
        insights.extend(await self._analyze_adherence_outcome(completed_cycles))
        
        # Biomarker → Behavior correlations
        insights.extend(await self._analyze_biomarker_behavior(completed_cycles))
        
        # Phase duration → Outcome
        insights.extend(await self._analyze_phase_duration_outcome(completed_cycles))
        
        # Lifestyle factors → Outcome
        insights.extend(await self._analyze_lifestyle_impact(completed_cycles))
        
        # Nutritionist modification patterns → Outcome
        insights.extend(await self._analyze_modification_impact(completed_cycles))
        
        # Content engagement → Mood/Outcome
        insights.extend(await self._analyze_content_impact(completed_cycles))
        
        # Store insights
        for insight in insights:
            if insight["statistical_significance"] < 0.05:  # Only store significant findings
                await self._store_insight(insight)
```

### 13.7 Feedback Loop to Swarms (Stage 5)

Insights with `actionable=true` and `confidence='high'` are readable by the nutrition swarms:

```python
# app/services/fie/feedback_provider.py
class FIEFeedbackProvider:
    """Provides actionable insights to swarms for enriched plan generation."""
    
    async def get_plan_context(self, treatment_type: str, phase: str, user_features: dict) -> str:
        """Returns a text summary of relevant insights for plan generation."""
        insights = await self._get_actionable_insights(treatment_type, phase)
        
        if not insights:
            return ""
        
        context_lines = ["Based on Izana's data from completed cycles:"]
        for insight in insights[:5]:  # Max 5 insights to avoid token bloat
            context_lines.append(f"- {insight['description']}")
        
        return "\n".join(context_lines)
```

This context is appended to the Nutrition Swarm 2's system prompt, enriching plan generation with real outcome data. Example:

> "Based on Izana's data from 500+ completed IVF cycles:
> - Users with >80% meal adherence during STIMS showed 23% better outcomes
> - Mediterranean-style diets during TWW correlated with lower anxiety scores
> - 20+ minutes of gentle yoga during STIMS correlated with improved mood trends
> 
> Use these insights to prioritize recommendations in the plan."

### 13.8 Admin Panel: FIE Dashboard

**New admin tab or sub-tab under Analytics:**

| Section | Shows |
|---------|-------|
| Data Overview | Total feature records, completed cycles, data quality distribution |
| Insight Feed | Latest discovered insights with significance scores, filterable by type |
| Training Data | Count, quality distribution, export buttons (JSONL, CSV) with filters |
| Model Registry | Trained models, metrics (AUC, accuracy), active model indicator |
| Correlation Explorer | Interactive charts: adherence vs outcome, biomarker distributions by outcome |
| Export History | Audit log of all training data exports |

### 13.9 Privacy & Ethics

```
╔══════════════════════════════════════════════════════════════════╗
║ FIE PRIVACY RULES:                                             ║
║                                                                 ║
║ 1. ALL data in fie.* tables is anonymized via one-way hash.    ║
║    It is IMPOSSIBLE to identify a specific user from FIE data. ║
║                                                                 ║
║ 2. When a user deletes their account (GDPR), the FIE data      ║
║    REMAINS because it cannot be linked back to them. This is   ║
║    disclosed in the privacy policy: "Anonymized, aggregated    ║
║    data may be retained for research purposes."                ║
║                                                                 ║
║ 3. Minimum sample sizes: insights require ≥50 cycles.         ║
║    No insight is generated from <50 data points.               ║
║                                                                 ║
║ 4. Training data exports require admin auth + are audit logged.║
║                                                                 ║
║ 5. FIE_ENABLED=false completely disables all FIE jobs.         ║
╚══════════════════════════════════════════════════════════════════╝
```

### 13.10 Environment Variables (New)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `FIE_ENABLED` | No | false | Master switch for FIE pipeline |
| `FIE_ANONYMIZATION_SALT` | Yes (if FIE enabled) | — | Random 64-char string for hashing |
| `FIE_MIN_CYCLES_FOR_INSIGHTS` | No | 50 | Minimum completed cycles before generating insights |
| `FIE_EXPORT_ENABLED` | No | false | Allow training data exports |

---

## 14. MICROCOPY & LUXURY MICRO-INTERACTIONS

### 14.1 Microcopy Philosophy

Every piece of text in Izana should feel like it was written by a thoughtful human, not generated by a template engine. Microcopy is the invisible hand that makes the app feel premium, empathetic, and trustworthy. It includes: button labels, loading states, empty states, error messages, transition text, toast notifications, placeholder text, confirmation messages, and celebration copy.

**Three rules:**
1. **Warm, not clinical.** "Your plan is on its way" not "Plan status: pending"
2. **Active, not passive.** "We're crafting your plan" not "Your plan is being created"
3. **Brief, not verbose.** Every word earns its place. No filler.

### 14.2 Loading States — Never a Spinner, Always a Story

Replace all generic spinners with contextual, phase-aware loading messages. Use the gentle pulse animation (opacity 0.5→1.0, `--duration-slow`), never a rotating spinner.

| Context | Loading Microcopy | Animation |
|---------|-------------------|-----------|
| Chat response streaming | Phase indicators: "Understanding your question..." → "Searching clinical literature..." → "Found 4 relevant sources..." → "Crafting your answer..." | Each phase gets a subtle ✓ checkmark as it completes. Sources appear one-by-one with a slide-in. |
| Plan loading | "Preparing your daily plan..." | Cards fade in one at a time: breakfast → lunch → dinner → exercise → meditation (staggered 150ms each) |
| Bloodwork analysis | "Reading your results..." → "Comparing with reference ranges..." → "Preparing your analysis..." | Progress bar with warm gradient (bronze → sage), not a cold blue bar |
| Content video loading | "Loading your session..." | Thumbnail visible immediately (cached), play button pulses gently until stream is ready |
| Chapter transition | "Closing this chapter..." → "Opening your next chapter..." | Subtle page-turn animation: current chapter slides left with slight scale-down (0.95), new chapter slides in from right |
| App startup (returning user) | "Welcome back, {pseudonym}..." | Brief (max 1 second). Chapter header + latest message visible within 2 seconds. |
| Search | "Searching your journey..." | Results fade in as found, not all at once |
| Provider report generation | "Preparing your doctor's report..." → "Compiling treatment timeline..." → "Formatting bloodwork..." | Step-by-step progress with warm checkmarks |

### 14.3 Empty States — Never Blank, Always Inviting

| Context | Empty State Copy | Visual |
|---------|-----------------|--------|
| No plan yet (waiting for nutritionist) | "Your personalized plan is being crafted by our nutrition team. While you wait — ask me anything or try a meditation." | Warm illustration placeholder + CTA buttons |
| No bloodwork uploaded | "Upload your bloodwork and I'll give you personalized insights about every biomarker. It takes under 2 minutes." | Subtle test-tube illustration with warm gradient |
| No check-ins yet today | "Good morning! Ready for your daily check-in?" | Animated mood emojis gently floating |
| No partner connected | "Going through this together? Connect your partner and they'll get their own Izana with daily support tips." | Two overlapping circles illustration (connection metaphor) |
| Search — no results | "I couldn't find that in your journey. Try different words, or ask me directly." | Subtle magnifying glass with question mark |
| Past chapter — no messages (pre-migration) | "This chapter was before I started organizing your journey. Your medical data from this period is preserved in your records." | Soft divider with date range |
| Content library — no content for this phase | "New content for this phase is coming soon. In the meantime, try our universal meditation." | Coming soon badge with gentle shimmer |

### 14.4 Toast Notifications — Brief, Warm, Purposeful

All toasts use `sonner` (existing dependency). Position: bottom-center on mobile. Duration: 3 seconds. Dismiss on swipe.

| Trigger | Toast Copy | Style |
|---------|-----------|-------|
| Meal marked done | "Breakfast logged ✓ +10 points" | Success (sage green) |
| Exercise completed | "Yoga complete! 20 min of gentle strength. ✓" | Success |
| Meditation completed | "10 minutes of calm. Beautiful. ✓" | Success |
| Check-in submitted | "Check-in done — thank you for sharing ✓" | Success |
| Streak milestone (7 days) | "7-day streak! 🔥 You're building a powerful habit." | Celebration (bronze + confetti particles) |
| Badge earned | "New badge: Wellness Warrior 🏅" | Celebration (with badge icon animation) |
| Plan approved | "Your personalized plan has arrived! 🎉" | Celebration |
| Partner connected | "Your partner is here! 🎉 You're in this together." | Celebration |
| Copy to clipboard | "Copied ✓" | Neutral (subtle) |
| Offline action queued | "Saved — will sync when you're connected" | Info (calm blue) |
| Sync complete | "All caught up ✓" | Success (brief, 2 seconds) |
| Error — generic | "Something went wrong. Trying again..." | Error (soft red, NOT alarming) |
| Error — network | "Connection lost. Your actions are saved locally." | Warning (warm amber) |
| Error — video load | "Video unavailable right now. Try again in a moment." | Warning |

### 14.5 Button & CTA Microcopy

| Generic (NEVER use) | Izana (ALWAYS use) |
|---------------------|-------------------|
| Submit | Done ✓ |
| Cancel | Not now |
| Delete | Remove |
| OK | Got it |
| Continue | Let's go |
| Sign up | Start my journey |
| Log in | Welcome back |
| Send | Share ❤️ (for partner messages) |
| Upload | Upload my results |
| Skip | Skip for now |
| Next | Continue → |
| Close | ✕ (icon only, no text) |
| Error: Try again | Let's try that again |
| Save | Saved ✓ (auto-save feedback, no button needed) |

### 14.6 Transition & Celebration Animations

#### Chapter Transition Animation
```
Current chapter → slides left with:
  - Scale: 1.0 → 0.96 (subtle shrink)
  - Opacity: 1.0 → 0.0
  - Duration: --duration-slow (400ms)
  - Easing: --ease-out

New chapter → slides in from right with:
  - Initial position: translateX(40px), opacity: 0
  - Final: translateX(0), opacity: 1
  - Duration: --duration-slow
  - Easing: --ease-out
  - Delay: 200ms (after old chapter finishes)

Chapter header → crossfade:
  - Phase name, day counter update with a soft fade (150ms)
```

#### Card Entrance Animation
```
Each chat card enters with:
  - Initial: translateY(12px), opacity: 0
  - Final: translateY(0), opacity: 1
  - Duration: --duration-normal (250ms)
  - Easing: --ease-out

For daily plan card (multiple items):
  - Each item staggers by 100ms
  - Breakfast fades in, then lunch (100ms later), then dinner, etc.
  - Creates a "waterfall" effect that feels intentional and premium
```

#### Check-in Submission
```
On mood tap:
  - Selected emoji scales: 1.0 → 1.3 → 1.0 (bounce)
  - Easing: --ease-spring
  - Duration: 300ms
  - Unselected emojis: opacity 1.0 → 0.4

On submit:
  - Card smoothly collapses (height animation, --duration-slow)
  - Izana's response slides up to fill the space
  - No jarring layout shift
```

#### Celebration (Confetti)
```
Triggers:
  - Plan approved
  - Onboarding complete
  - Streak milestones (7, 14, 30, 60, 100)
  - Badge earned
  - Positive outcome

Config (canvas-confetti):
  particleCount: 80 (not overwhelming)
  spread: 70
  colors: [var(--celebration-primary), var(--celebration-secondary), '#E8DFF0']
  origin: { y: 0.6 } (from center, not top)
  duration: --duration-celebration (600ms)
  gravity: 1.2 (gentle fall)
  
For positive outcome ONLY:
  particleCount: 150 (bigger celebration)
  duration: 1200ms
  Add: gentle vibration if device supports it (navigator.vibrate(200))
```

#### Streak Fire Animation
```
The 🔥 in the chapter header:
  - Idle: gentle size pulse (scale 1.0 → 1.05 → 1.0, 2s cycle, infinite)
  - On new streak day: brief flare (scale 1.0 → 1.4 → 1.0, --ease-spring, 400ms)
  - Color: --streak-color (bronze) with subtle glow
```

#### Weekly Group Accordion
```
Expand:
  - Height: 0 → auto (use max-height trick for CSS transition)
  - Duration: --duration-slow (400ms)
  - Easing: --ease-out
  - Summary line: opacity 1.0 → 0, replaced by full content
  - Scroll: auto-scroll so the expanded week's top is visible

Collapse:
  - Reverse of expand
  - Content fades before height shrinks (prevents jarring clip)
  - Summary line fades in at end
```

#### Media Player Enter/Exit
```
Open (from content card tap):
  - Overlay slides up from bottom: translateY(100%) → translateY(0)
  - Duration: --duration-slow
  - Easing: --ease-out
  - Background overlay: opacity 0 → 0.5 (var(--canvas-overlay))
  - Player controls fade in 200ms after overlay settles

Close:
  - Reverse slide down
  - Smooth, never jarring
  - Progress saved automatically before close
```

### 14.7 Grief Mode Visual Treatment

When `chapter.grief_mode = true`, the entire visual tone shifts:

```css
[data-grief-mode="true"] {
  /* Soften everything */
  --brand-primary: #6B6278;          /* Muted, not vibrant */
  --brand-secondary: #9B93A8;
  --celebration-primary: transparent; /* No confetti possible */
  
  /* Disable all non-essential animations */
  * { animation-duration: 0ms !important; }
  
  /* Exception: gentle opacity fades still work */
  .fade-transition { animation-duration: 250ms !important; }
  
  /* Hide gamification elements */
  .streak-indicator { display: none; }
  .points-display { display: none; }
  .badge-celebration { display: none; }
}
```

### 14.8 Placeholder Text (Input Fields)

| Field | Placeholder |
|-------|-------------|
| Chat input (normal) | "Ask Izana anything..." |
| Chat input (post-checkin) | "How can I help today?" |
| Chat input (grief mode) | "I'm here whenever you're ready..." |
| Search | "Search your journey..." |
| Partner encouragement | "Send a kind word..." |
| Free text (meal logging) | "What did you have?" |
| Free text (food dislikes) | "Foods you'd rather avoid..." |
| Password | "At least 8 characters" |
| Recovery code input | "XXXX-XXXX-XXXX-XXXX" |

### 14.9 Error Messages — Never Technical, Always Human

| Error Type | Generic (NEVER) | Izana (ALWAYS) |
|-----------|-----------------|----------------|
| Network error | "ERR_NETWORK" | "I lost my connection for a moment. Trying again..." |
| Server error | "500 Internal Server Error" | "Something unexpected happened on my end. I'm working on it." |
| Rate limited | "429 Too Many Requests" | "I need a moment to catch up. Try again in a few seconds." |
| File too large | "File exceeds 5MB limit" | "That file is a bit large for me. Could you try one under 5MB?" |
| Invalid file type | "Unsupported file format" | "I can read PDFs and images (JPEG, PNG). Could you try one of those?" |
| Session expired | "401 Unauthorized" | "Your session has ended. Let's get you back in." + redirect to login |
| Feature unavailable (offline) | "Feature not available" | "This needs an internet connection. I'll have it ready when you're back online." |
| Video playback error | "Media error" | "Having trouble loading this video. [Try again] or [Skip for today]" |
| Plan not ready | "Plan pending" | "Your plan is still being reviewed. I'll let you know the moment it's ready!" |

### 14.10 Micro-interaction Summary for Claude Code

```
╔═══════════════════════════════════════════════════════════════╗
║ IMPLEMENTATION CHECKLIST FOR MICRO-INTERACTIONS:             ║
║                                                              ║
║ □ Replace ALL spinners with contextual loading messages      ║
║ □ Add card stagger animation (100ms per item)                ║
║ □ Add check-in emoji bounce on select                        ║
║ □ Add weekly group smooth accordion                          ║
║ □ Add chapter transition slide animation                     ║
║ □ Add streak fire pulse animation                            ║
║ □ Add media player slide-up overlay                          ║
║ □ Add confetti for celebrations (canvas-confetti)            ║
║ □ Add grief mode CSS overrides                               ║
║ □ Replace ALL error messages with human-friendly copy        ║
║ □ Replace ALL button labels per Section 14.5                 ║
║ □ Add empty state illustrations + copy per Section 14.3      ║
║ □ Add toast notifications per Section 14.4                   ║
║ □ Add placeholder text per Section 14.8                      ║
║ □ Test ALL animations with prefers-reduced-motion: reduce    ║
║ □ Test grief mode visual treatment                           ║
║ □ Verify toast positioning on mobile (bottom-center)         ║
║ □ Verify card entrance doesn't cause layout shift            ║
╚═══════════════════════════════════════════════════════════════╝
```

---

---

---

# SECTION H: UI COMPONENT UPDATES (Revised from Original)

This section documents changes from the original specification that MUST be applied:

## H1. Changes from Original Spec

| Original | Updated | Reason |
|----------|---------|--------|
| "Chapters" user-facing term | REMOVED. User sees phase name only: "Your stims · day 8" | "Chapters" feels unempathetic |
| 4-tab bottom nav (Chat, Chapters, Blood, More) | 3-tab text-only nav: Today, Journey, You | Less generic, warmer |
| Check-in card (mood + symptoms + submit = 4+ taps) | Mood emojis as part of Izana's message (1 tap). Symptoms optional via "+log symptoms" link | Reduced friction |
| All cards visible simultaneously | Smart collapsing: only latest interaction visible. Completed sections collapse to one-line summaries | Reduces clutter |
| Separate landing page | Chat IS the landing page. Izana's first message is the value prop | More cohesive |
| Full-screen signup page | Bottom-sheet modal over dimmed chat. Avatar + name combined on one row | Saves space |
| 14 individual onboarding messages | 3 grouped rounds: Treatment & You, Lifestyle, Food & Exercise | More engaging |
| Mood check during signup | NO mood at signup. First mood check = next morning | Feels more natural |
| After onboarding → recovery → dashboard | After onboarding → grand reveal IN CHAT with shadow text placeholder | Immediate value |

## H2. Bottom Nav Implementation

```tsx
// 3-tab navigation — text only, no icons
const tabs = [
  { label: "Today", path: "/chat" },
  { label: "Journey", path: "/journey" },
  { label: "You", path: "/profile" },
];
// Active tab gets pill: bg-[--brand-primary-bg] text-[--brand-primary] font-medium rounded-2xl px-4 py-1
// Inactive tab: text-[--text-tertiary] text-[9px]
```

## H3. Chapter Header Implementation

```tsx
// The header says "Your {phase} · day {n}" — never "Chapter"
// Examples:
// "Your stims · day 8"        (IVF stims)
// "Your baseline · day 3"     (IVF baseline)
// "Your two week wait · day 5" (TWW)
// "Getting started"           (onboarding, no day count)
// "Your early pregnancy"      (positive outcome)

// Header also shows streak: 🔥 {n}
// 3-dot menu (⋮) opens: Share with doctor, Settings, Theme toggle
```

## H4. Smart Collapsing Rules

```
RULE: Only the LATEST interaction section is expanded.
Everything before it collapses to a ONE-LINE summary.

Examples:
- Morning done, afternoon conversation:
  "morning · 🙂 good · 2/4 done  ▸" (collapsed)
  [afternoon conversation expanded]

- Yesterday:
  "yesterday · 🙂 · 3/4 done  ▸" (collapsed)
  [today expanded]

- Past week:
  "Days 1-7  ▸" (collapsed)
  [current period expanded]

Tapping the ▸ arrow expands any collapsed section.
```

## H5. Content Library (63 Assets)

Exercise Videos (29, ~500 min total):
- EX-001 to EX-029
- Key: EX-006/007 (Stims Yoga — no twists/inversions), EX-014 (TWW Yoga), EX-011 (Post-Retrieval Walk)
- Partner: EX-026 (Couples Yoga), EX-027 (Partner Fitness)
- Hosted on Cloudflare Stream, played via hls.js

Meditation/Audio (34, ~340 min total):
- MD-001 to MD-034
- Critical: MD-018 (Negative Result — "no silver linings, just holding space")
- MD-019 (Pregnancy Loss — needs mental health professional review)
- Universal breathwork: MD-030 (4-7-8), MD-031 (Box Breathing, 3 min)

Priority 1 MVP assets (18): MD-003, MD-004, MD-030, MD-031, EX-001, EX-005, EX-006, EX-007, EX-008, EX-014, EX-015, EX-025, MD-005, MD-006, MD-013, MD-014, MD-015, MD-018

---

# SECTION I: INFRASTRUCTURE STATUS (What You Have vs What Gets Built)

| Resource | Status | Action |
|----------|--------|--------|
| Supabase project | ❌ Create new | You create before Phase 1 (Section S2) |
| Groq API keys | ✅ You have these | Paste into env vars |
| Domain (chat.izana.ai) | ✅ Ready | DNS configured |
| OpenAI API key | ✅ You have this | For embeddings during PDF ingestion |
| Knowledge base (236 PDFs) | ✅ Files on your computer | Ingested by Claude Code in Phase 2 (~$3-5 OpenAI cost) |
| Exercise videos (29) | ✅ Produced locally | Uploaded to Cloudflare Stream in Phase 4 |
| Meditation audios (34) | ✅ Produced locally | Uploaded to Cloudflare Stream in Phase 4 |
| Cloudflare Stream | ❌ Create before Phase 4 | Video/audio hosting |
| Netlify | ❌ Create before Phase 6 | Frontend hosting |
| Render | ❌ Create before Phase 6 | Backend hosting |

---

# SECTION J: THE PLAN SYSTEM (Complete Specification)

## J1. What Is a Plan?

A plan is the core deliverable of Izana. It's a personalised daily guide containing:

1. **Nutrition plan** — 3 meals (breakfast, lunch, dinner) + 1-2 optional snacks, each with:
   - Meal name (e.g., "Mediterranean salmon bowl")
   - Ingredients list with quantities
   - Brief preparation notes
   - Nutritional reasoning (e.g., "omega-3 for follicle membrane health")
   - Phase-specific notes (e.g., "avoid raw fish during TWW")
   - Respects user's allergies, dietary restrictions, cuisine preferences, and dislikes

2. **Exercise plan** — 1 session per day, matched to a specific content asset:
   - Exercise type (yoga, walking, stretching, etc.)
   - Duration (matching user's exercise_time preference)
   - Content ID (links to a specific video from the content library)
   - Intensity level (gentle/light/moderate — never high-impact during stims or TWW)
   - Contraindication check (no inversions during stims, no twisting during TWW, etc.)

3. **Meditation/mental health plan** — 1 session per day:
   - Type (guided meditation, breathing exercise, visualisation)
   - Content ID (links to a specific audio from the content library)
   - Duration (5-15 minutes)
   - Phase-appropriate focus (e.g., "egg quality visualisation" during stims, "implantation calm" during TWW)

## J2. Plan JSON Structure

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "status": "APPROVED",  // GENERATING → PENDING_NUTRITIONIST → IN_REVIEW → APPROVED/MODIFIED/REJECTED
  "version": 1,
  "treatment_type": "IVF",
  "phase": "STIMS",
  "nutrition_plan": {
    "daily_calories_target": 2200,
    "macros": { "protein_pct": 30, "carbs_pct": 40, "fat_pct": 30 },
    "hydration_litres": 2.5,
    "phase_nutrition_notes": "Focus on protein and anti-inflammatory foods during stims.",
    "meals": [
      {
        "meal_type": "breakfast",
        "name": "Avocado toast with poached eggs",
        "description": "Whole grain sourdough, ripe avocado, two poached eggs, microgreens, seeds",
        "ingredients": [
          { "name": "Sourdough bread", "quantity": "2 slices" },
          { "name": "Avocado", "quantity": "1/2" },
          { "name": "Eggs", "quantity": "2" },
          { "name": "Mixed microgreens", "quantity": "1 handful" },
          { "name": "Pumpkin seeds", "quantity": "1 tbsp" }
        ],
        "nutritional_reasoning": "Folate from greens, choline from eggs, healthy fats from avocado — all support follicle development.",
        "calories_approx": 480,
        "emoji": "🌅",
        "prep_time_minutes": 10
      },
      {
        "meal_type": "lunch",
        "name": "Salmon quinoa bowl",
        "description": "Grilled salmon, quinoa, roasted vegetables, tahini dressing",
        "ingredients": [ /* ... */ ],
        "nutritional_reasoning": "Omega-3 from salmon reduces inflammation. Quinoa provides complete protein.",
        "calories_approx": 650,
        "emoji": "☀️",
        "prep_time_minutes": 25
      },
      {
        "meal_type": "dinner",
        "name": "Bone broth sweet potato bowl",
        "description": "Homemade bone broth, roasted sweet potato, steamed greens, turmeric",
        "ingredients": [ /* ... */ ],
        "nutritional_reasoning": "Collagen from broth, beta-carotene from sweet potato, turmeric for anti-inflammation. Gentle on digestion for evening.",
        "calories_approx": 520,
        "emoji": "🌙",
        "prep_time_minutes": 20
      }
    ],
    "snacks": [
      {
        "name": "Greek yogurt with walnuts and honey",
        "nutritional_reasoning": "Probiotics, omega-3, natural sugars for sustained energy.",
        "calories_approx": 250
      }
    ]
  },
  "exercise_plan": {
    "session": {
      "type": "yoga",
      "name": "Gentle stims yoga — day 8",
      "content_id": "uuid-of-EX-007",
      "duration_minutes": 20,
      "intensity": "gentle",
      "description": "Modified yoga flow avoiding inversions and deep twists. Focus on hip openers and gentle stretching.",
      "contraindication_check": {
        "passed": true,
        "avoided": ["inversions", "deep_twists", "core_compression"],
        "reason": "Standard stims precautions"
      }
    },
    "alternatives": [
      { "type": "walking", "name": "20-minute easy walk", "content_id": null, "duration_minutes": 20 }
    ]
  },
  "mental_health_plan": {
    "session": {
      "type": "guided_meditation",
      "name": "Follicle growth visualisation",
      "content_id": "uuid-of-MD-005",
      "duration_minutes": 10,
      "description": "A guided meditation focusing on visualising healthy follicle growth and preparing your body for retrieval."
    },
    "alternatives": [
      { "type": "breathing", "name": "Box breathing (3 min)", "content_id": "uuid-of-MD-031", "duration_minutes": 3 }
    ]
  },
  "generation_context": {
    "user_age_range": "31-35",
    "allergies": ["dairy"],
    "dietary_restrictions": ["dairy-free"],
    "cuisine_preferences": ["Mediterranean", "Asian"],
    "food_dislikes": "cilantro",
    "exercise_time_minutes": 20,
    "exercise_preferences": ["yoga", "walking"],
    "health_conditions": ["none"],
    "bmi": 22.5,
    "fitness_level": "moderate",
    "fie_insights_used": [
      "Users with >80% meal adherence during STIMS showed 23% better outcomes",
      "Mediterranean-style diets during stims correlated with lower anxiety scores"
    ]
  },
  "created_at": "2026-03-21T10:00:00Z",
  "approved_at": "2026-03-21T14:15:00Z",
  "approved_by": "nutritionist-uuid"
}
```

## J3. Plan Generation Pipeline

```
Phase change detected (or new user onboarding complete)
    │
    ▼
Step 1: Gather user context
    - Profile: allergies, dietary_restrictions, cuisine_preferences, food_dislikes,
      exercise_time, exercise_preferences, fitness_level, health_conditions, age_range
    - Current phase + treatment type + day count
    - Bloodwork (if available): key biomarkers
    - Previous plan (if exists): what worked, nutritionist modifications
    - FIE insights (if available): actionable correlations for this phase
    │
    ▼
Step 2: Nutrition Swarm 0 — Input Validation
    - Validate all inputs are present
    - Flag missing critical data (e.g., no allergies data)
    - Normalize cuisine preferences to supported list
    │
    ▼
Step 3: Nutrition Swarm 1 — Profile Analysis
    - Calculate calorie target based on age, BMI, activity level, treatment phase
    - Determine macro ratios for phase
    - Identify phase-specific nutritional priorities
      (e.g., STIMS = high protein + omega-3; TWW = anti-inflammatory + folate)
    - Identify phase-specific restrictions
      (e.g., STIMS = no high-mercury fish; TWW = no raw fish, limit caffeine)
    │
    ▼
Step 4: Nutrition Swarm 2 — Plan Generation
    - Generate 3 meals + 1-2 snacks using LLM
    - Match exercise content from wellness_content table:
      WHERE plan_eligible = true
      AND treatment_phases @> ARRAY[current_phase]
      AND treatment_types @> ARRAY[current_treatment]
      AND intensity <= user_fitness_level
      AND NOT (contraindications && user_health_conditions)
    - Match meditation content similarly
    - Apply FIE insights as priority recommendations
    │
    ▼
Step 5: Compliance Check
    - Verify no allergens in any ingredient
    - Verify dietary restrictions respected
    - Verify exercise intensity appropriate for phase
    - Verify content contraindications checked
    │
    ▼
Step 6: Save to personalized_plans with status = 'PENDING_NUTRITIONIST'
    │
    ▼
Step 7: Create entry in approval_queue
    - priority = 'normal' (or 'urgent_phase_change' if triggered by transition)
    - deadline = now + 4 hours (target turnaround)
    │
    ▼
Step 8: Notify nutritionists
    - Push notification to all active nutritionists
    - Email notification
    - Queue item appears in nutritionist portal
```

## J4. Nutritionist Review Workflow

```
Nutritionist opens portal → sees queue sorted by priority then deadline
    │
    ▼
Clicks "Assign to me" → status changes to IN_REVIEW
    │
    ▼
3-panel review screen:
    LEFT: User context (treatment, allergies, preferences, bloodwork summary)
    CENTER: Plan editor (nutrition, exercise, meditation — all editable)
    RIGHT: AI reasoning (why each meal was chosen, FIE insights used)
    │
    ├── Option A: "Approve" → plan delivered to user immediately
    │
    ├── Option B: "Modify & Approve"
    │     → Modified fields highlighted in orange
    │     → For each modification, nutritionist fills:
    │       - Reason (required, ≥10 chars)
    │       - Category: Allergen Safety / Dietary Restriction Violation /
    │         Treatment Phase Mismatch / Calorie Adjustment /
    │         Nutrient Optimization / Preference Alignment / Cultural Sensitivity
    │       - Severity: Minor / Moderate / Major / Critical
    │       - "Could cause harm?" checkbox (red warning)
    │     → Modifications saved to plan_modifications table (DPO training data)
    │     → Modified plan delivered to user
    │
    └── Option C: "Reject"
          → Reason required (≥20 chars)
          → Option to request AI regeneration with specific instructions
          → New plan generated with modifications as context
          → Re-enters queue
```

## J5. Plan Delivery to User

When plan is approved:

1. `personalized_plans.status` → 'APPROVED' (or 'MODIFIED')
2. `personalized_plans.approved_at` → now()
3. Push notification sent to user: "Your personalised plan has arrived! 🎉"
4. In chat: celebration message + plan card (with confetti if first plan)
5. Plan card appears in the "Today" view with tabbed layout

## J6. Daily Plan Rotation

Plans don't change daily by default. The same plan structure applies for the entire phase (stims meals stay stims-appropriate). However:

- **Meal variety:** The AI generates 5-7 meal options per meal type. The plan card shows a different combination each day, cycling through options to avoid repetition.
- **Phase change:** Triggers a completely new plan generation → nutritionist review cycle
- **Manual request:** User can say "I'm bored of the meals" → Izana generates fresh options within the existing plan framework (still requires nutritionist approval)

## J7. Plan Status Card (During Review)

While the plan is being reviewed, the user sees this in chat:

```
✦  Your personalised plan is being prepared.

┌─────────────────────────────┐
│ Plan status                 │
│                             │
│ Created      10:00 AM    ✓  │
│ In review    2:15 PM     ✓  │  ← Updates in real-time via polling
│ Ready        —           ⏳  │
│                             │
│ Usually takes a few hours.  │
└─────────────────────────────┘
```

The status card polls `/api/v1/plan-status` every 30 seconds. When status changes to APPROVED, the card transforms into the celebration + plan delivery.

---

# SECTION K: PRE-CACHED LANDING PAGE RESPONSES

## K1. Concept

The 3 suggested questions on the landing page ("What to eat during IVF?", "Is my AMH normal?", "Help with TWW anxiety") have **pre-computed responses cached in the frontend**. When a user taps one, they see the full Perplexity-style search animation, but the response is already ready — it appears within 2-3 seconds instead of 8-10.

This creates the illusion of incredible speed and makes the first impression feel magical.

## K2. How It Works

```
Build time (or daily cron):
    │
    ▼
Backend endpoint: GET /api/v1/preview/cached-responses
    - Runs the full swarm pipeline (0→1→3→4→7) for each of the 3 questions
    - Returns response + sources + follow-ups for each
    - Stores in Redis/memory with 24-hour TTL
    │
    ▼
Frontend build / first load:
    - Fetches cached responses from API
    - Stores in component state (or SWR cache with long TTL)
    │
    ▼
User taps suggested question:
    - IMMEDIATELY starts the search animation:
      Phase 1 (0.5s): "Understanding your question..." ✓
      Phase 2 (1.0s): "Searching clinical literature..." ✓
      Phase 3 (0.5s): "Found 4 relevant sources..." ✓ (sources appear one by one)
      Phase 4 (0.5s): "Crafting your answer..."
    - Total animation: ~2.5 seconds
    - Response text starts streaming (from cache, simulated token-by-token)
    │
    ▼
User types their own question (not cached):
    - Real swarm pipeline runs
    - Same animation, but phases are real (not simulated)
    - Takes 5-10 seconds (normal)
```

## K3. The Search Animation (Perplexity-Style)

This animation runs for EVERY chat response, not just cached ones. For cached responses, the phases are timed. For real responses, the phases are driven by SSE events from the backend.

```tsx
// Search animation stages
const STAGES = [
  { id: 'understanding', label: 'Understanding your question...', icon: '🔍' },
  { id: 'searching', label: 'Searching clinical literature...', icon: '📚' },
  { id: 'found', label: null, icon: '✓' },  // Dynamic: "Found N relevant sources..."
  { id: 'crafting', label: 'Crafting your answer...', icon: '✨' },
];
```

**Visual design of the animation:**

```
┌─────────────────────────────────┐
│                                 │
│  ✦ (Izana avatar, gently pulsing)
│                                 │
│  🔍 Understanding your question │  ← Fade in, then ✓ and fade to muted
│  📚 Searching clinical lit...   │  ← Fade in (0.3s after previous ✓)
│  ✓ Found 4 relevant sources     │  ← Sources slide in one by one:
│     • ESHRE IVF Guidelines      │     each with a subtle slide-left
│     • Fertility & Sterility     │     entrance (staggered 200ms)
│     • Reproductive BioMedicine  │
│     • Human Reproduction        │
│  ✨ Crafting your answer...      │  ← Pulsing opacity while generating
│                                 │
│  [Response text streams in      │  ← Token-by-token, like typing
│   word by word here...]         │
│                                 │
└─────────────────────────────────┘
```

**Animation details:**
- Each stage fades in with `opacity: 0→1, y: 4→0` over 200ms
- When complete, the icon changes to ✓ and text becomes muted (`--text-tertiary`)
- Sources appear one at a time with a slide-from-left animation (200ms stagger)
- The "crafting" stage has a gentle pulse animation on the ✨ icon
- Once the response starts, the entire animation section collapses smoothly (400ms) and the response takes its place
- After collapse, a small "Sources" badge remains (tappable to expand citations)

## K4. Cached Questions (Updated Per Language)

For each of the 11 supported languages, cache responses for these 3 questions:

| # | English | Notes |
|---|---------|-------|
| 1 | "What should I eat during IVF?" | Broad nutrition question — shows plan capability |
| 2 | "Is my AMH level normal?" | Bloodwork question — shows clinical knowledge |
| 3 | "How do I manage TWW anxiety?" | Emotional question — shows empathy |

**Cache refresh:** Daily at 3am UTC via background job. If cache is stale/missing, fall back to real-time pipeline (user sees normal timing).

## K5. Backend Implementation

```python
# app/api/preview.py

@router.get("/preview/cached-responses")
async def get_cached_responses(language: str = "en"):
    """Return pre-computed responses for landing page questions."""
    cache_key = f"preview_responses:{language}"
    cached = await cache_service.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Generate fresh if not cached
    questions = PREVIEW_QUESTIONS.get(language, PREVIEW_QUESTIONS["en"])
    responses = []
    for q in questions:
        response = await run_preview_pipeline(q, language)
        responses.append({
            "question": q,
            "response": response["content"],
            "sources": response["sources"],
            "follow_ups": response["follow_ups"],
        })
    
    await cache_service.set(cache_key, json.dumps(responses), ttl=86400)
    return responses

@router.post("/preview/ask")
@rate_limit(1, per=600)  # 1 request per 10 minutes per IP
async def preview_ask(request: PreviewRequest):
    """Real-time preview for custom questions (rate limited)."""
    # Run swarms 0→1→3→4→7 (no context, no user ID)
    response = await run_preview_pipeline(request.question, request.language)
    return response
```

---

# SECTION L: UBER LUXE UI DESIGN SPECIFICATIONS

## L1. Design Philosophy: Beyond "Nice" Into "Covetable"

Izana should feel like opening a Diptyque candle box, not downloading a health app. Every pixel should feel considered. Every interaction should feel intentional. The app should make users think "whoever made this cares deeply about the details."

**Reference aesthetic:** Aesop website × Headspace app × Linear app
- Aesop: warm typography, restraint, editorial quality, cream/amber palette
- Headspace: gentle motion, playful but calm, breathing animations
- Linear: precision, smooth transitions, zero jank, keyboard-first quality

## L2. Signature Design Details

### The Izana Breathing Dot
The ✦ Izana avatar in the chat gently "breathes" — a subtle scale animation that runs constantly when Izana is idle, giving the app a sense of life.

```css
.izana-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--brand-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: izana-breathe 4s ease-in-out infinite;
}

@keyframes izana-breathe {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.04); opacity: 1; }
}
```

### Warm Gradient Shimmer
Loading skeletons don't use the standard grey pulse. They use a warm gradient shimmer that sweeps left-to-right:

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--canvas-sunken) 0%,
    var(--canvas-elevated) 40%,
    var(--canvas-sunken) 80%
  );
  background-size: 200% 100%;
  animation: warm-shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}

@keyframes warm-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Message Bubble Morphology
Izana's messages have a signature asymmetric border radius — rounded on three corners, pointed on the bottom-left (like a speech tail):

```css
.izana-bubble {
  background: var(--canvas-sunken);
  border: 0.5px solid var(--border-default);
  border-radius: 16px 16px 16px 4px;  /* Bottom-left is pointed */
  padding: 12px 14px;
}

.user-bubble {
  background: var(--brand-primary);
  color: white;
  border-radius: 16px 16px 4px 16px;  /* Bottom-right is pointed */
  padding: 12px 14px;
}
```

### Haptic-Quality Button Press
Every tappable element has a micro-scale animation that feels like a physical button press:

```tsx
<motion.button
  whileTap={{ scale: 0.97 }}
  transition={{ duration: 0.1 }}
  className="..."
>
  {label}
</motion.button>
```

For important actions (Done ✓, Start my journey), add a subtle glow on press:

```css
.cta-primary:active {
  box-shadow: 0 0 0 4px rgba(74, 61, 143, 0.15);
  transition: box-shadow 0.1s;
}
```

### Elevated Cards with Micro-Shadow
Cards don't just have borders — they have a barely-visible shadow that creates depth without heaviness:

```css
.card-elevated {
  background: var(--canvas-elevated);
  border: 0.5px solid var(--border-default);
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(42, 36, 51, 0.04), 0 1px 2px rgba(42, 36, 51, 0.02);
}
```

### Text Reveal Animation
When Izana types a long message, text appears word-by-word (not character-by-character). This is the streaming response rendered with a soft fade per word:

```tsx
// During SSE streaming, each new word gets a brief opacity animation
const StreamingText = ({ text }: { text: string }) => {
  const words = text.split(' ');
  return (
    <p className="text-sm leading-relaxed">
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          {word}{' '}
        </motion.span>
      ))}
    </p>
  );
};
```

### The Progress Line
The plan progress is shown as an ultra-thin line (2px) at the bottom of the plan card. It fills with `--brand-primary` as items are completed. The fill animates smoothly:

```css
.progress-line {
  height: 2px;
  background: var(--canvas-sunken);
  border-radius: 1px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--brand-primary);
  border-radius: 1px;
  transition: width 0.6s var(--ease-out);
}
```

### Source Citations as Floating Pills
After a response, sources appear as small floating pills that slide in one by one. Tapping a source expands it inline:

```css
.source-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  color: var(--text-tertiary);
  background: var(--canvas-sunken);
  padding: 3px 8px;
  border-radius: 8px;
  border: 0.5px solid var(--border-default);
}
```

### Empty State Illustrations
Each empty state has a minimal single-line SVG illustration (not emoji, not stock art). These are custom:
- No plan: a soft curved line resembling a plate with steam
- No bloodwork: a single test tube outline with a gradient inside
- No partner: two overlapping circles (Venn-diagram style)
- Search no results: a magnifying glass with a gentle question mark

These are rendered as inline SVGs with `currentColor` so they adapt to light/dark mode automatically.

## L3. Luxury Transitions Between Screens

### Tab Switch
When switching between Today/Journey/You tabs, the content doesn't just swap — it crossfades:

```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={activeTab}
    initial={{ opacity: 0, x: direction * 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: direction * -20 }}
    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
  >
    {tabContent}
  </motion.div>
</AnimatePresence>
```

The direction (`x: 20` or `x: -20`) follows the tab position — swiping right to Journey feels like the content slides in from the right.

### Modal Transitions
All modals (signup, recovery, media player) use a bottom-sheet pattern with a spring-damped slide:

```tsx
// Backdrop: warm overlay, not cold black
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  exit={{ opacity: 0 }}
  style={{ background: 'rgba(42, 36, 51, 0.4)' }}  // Warm, not rgba(0,0,0,0.5)
/>
// Sheet
<motion.div
  initial={{ y: '100%' }}
  animate={{ y: 0 }}
  exit={{ y: '100%' }}
  transition={{ type: 'spring', damping: 30, stiffness: 300 }}
/>
```

### Scroll-Linked Header
The phase header ("Your stims · day 8") shrinks slightly as the user scrolls down, creating a compact mode:

```css
/* Normal: padding 10px 14px, font-size 15px */
/* Compact (scrolled): padding 6px 14px, font-size 13px */
/* Transition: 200ms ease-out */
```

---

# SECTION M: COMPLETE BACKEND ARCHITECTURE

## M1. System Overview

```
                    FRONTEND (Next.js)
                         │
                    HTTPS/SSE
                         │
                    ┌────▼────┐
                    │ FastAPI  │
                    │  Server  │
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
     │ Supabase │   │  Groq   │   │ OpenAI  │
     │  (DB +   │   │  (LLM)  │   │ (Embed) │
     │   Auth)  │   │         │   │         │
     └─────────┘   └─────────┘   └─────────┘
                         │
                    ┌────▼────┐
                    │  Redis  │   (Optional: caching + rate limiting)
                    └─────────┘
```

## M2. FastAPI Application Structure

```python
# app/main.py — the entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Izana API", version="2.0")

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Rate limiting middleware (custom)
app.middleware("http")(rate_limit_middleware)

# Correlation ID middleware
app.middleware("http")(correlation_id_middleware)

# Include all routers
app.include_router(chat_router,        prefix="/api/v1", tags=["Chat"])
app.include_router(preview_router,     prefix="/api/v1", tags=["Preview"])
app.include_router(chapters_router,    prefix="/api/v1", tags=["Chapters"])
app.include_router(bloodwork_router,   prefix="/api/v1", tags=["Bloodwork"])
app.include_router(companion_router,   prefix="/api/v1", tags=["Companion"])
app.include_router(nutrition_router,   prefix="/api/v1", tags=["Nutrition"])
app.include_router(coach_router,       prefix="/api/v1", tags=["Coach"])
app.include_router(content_router,     prefix="/api/v1", tags=["Content"])
app.include_router(content_admin_router, prefix="/api/v1", tags=["ContentAdmin"])
app.include_router(plan_status_router, prefix="/api/v1", tags=["PlanStatus"])
app.include_router(push_router,        prefix="/api/v1", tags=["Push"])
app.include_router(privacy_router,     prefix="/api/v1", tags=["Privacy"])
app.include_router(reports_router,     prefix="/api/v1", tags=["Reports"])
app.include_router(translate_router,   prefix="/api/v1", tags=["Translate"])
app.include_router(admin_router,       prefix="/api/v1/admin", tags=["Admin"])
app.include_router(nutritionist_router, prefix="/api/v1/nutritionist", tags=["Nutritionist"])
app.include_router(resilience_router,  prefix="/api/v1", tags=["Health"])
app.include_router(jobs_router,        prefix="/api/v1", tags=["Jobs"])
```

## M3. Authentication Pattern (Decision 1: Server-Side JWT Verification)

**CRITICAL: The X-User-ID header pattern is ELIMINATED.** Every authenticated API request must include a Supabase access token. The backend verifies it server-side.

Every API endpoint (except preview, health, and provider portal public) requires authentication:

```python
# app/core/auth.py

import jwt
from fastapi import Request, HTTPException, Depends
from app.core.config import settings

async def get_user_id(request: Request) -> str:
    """Extract and verify user ID from Supabase JWT.

    (Decision 1) The frontend sends: Authorization: Bearer <supabase_access_token>
    We verify the JWT signature using SUPABASE_JWT_SECRET, check expiry,
    and extract the user_id from the 'sub' claim.

    This REPLACES the old X-User-ID header pattern which allowed
    any HTTP client to impersonate any user.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def get_admin_key(request: Request) -> str:
    """Verify admin API key for admin/nutritionist endpoints."""
    key = request.headers.get("X-Admin-API-Key")
    if not key or key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return key

# Usage in routes:
@router.post("/chat")
async def chat(request: ChatRequest, user_id: str = Depends(get_user_id)):
    ...

@router.get("/admin/dashboard")
async def dashboard(_: str = Depends(get_admin_key)):
    ...
```

**Frontend auth header setup:**
```typescript
// src/lib/api-client.ts
// Every API call includes the Supabase access token:

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function apiCall(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error('Not authenticated');

  return fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    },
  });
}
```

**SUPABASE_JWT_SECRET:** Found in Supabase Dashboard → Settings → API → JWT Secret. Add this to your `.env` file.

## M4. The Chat Pipeline (12 Steps, Detailed)

This is the most complex flow in the system. Every chat message goes through these 12 steps.

**CRITICAL (Decision 2):** The pipeline does NOT run inline in the HTTP handler. It runs in an arq background worker. The SSE endpoint polls Redis for progress events.

**CRITICAL (Decision 9):** Compliance (Step 9) runs on the COMPLETE response BEFORE any tokens are streamed. The user never sees unchecked medical content.

```
ARCHITECTURE (Decision 2):
┌──────────────┐     ┌─────────┐     ┌──────────────────┐
│ POST /chat/  │     │  Redis  │     │  arq Worker      │
│ stream       │────▶│  Queue  │────▶│  (chat_tasks.py) │
│ (enqueue)    │     │         │     │                  │
└──────┬───────┘     │         │     │  Runs steps 1-10 │
       │             │  Stream │◀────│  Writes events   │
       │             │  Events │     │  to Redis stream  │
       ▼             │         │     └──────────────────┘
┌──────────────┐     │         │
│ SSE endpoint │◀────│         │
│ (reads Redis │     └─────────┘
│  stream)     │
└──────────────┘
```

```python
# app/workers/chat_tasks.py — runs in arq worker process

async def chat_pipeline_task(ctx, task_id: str, user_id: str, content: str):
    """The full chat pipeline. Runs in background, writes events to Redis stream."""
    redis = ctx["redis"]
    trace_id = uuid4()

    async def emit(event_type: str, data: dict):
        """Write an SSE event to the Redis stream for this task."""
        await redis.xadd(f"chat:{task_id}", {"event": event_type, "data": json.dumps(data)})

    try:
        # ── STEP 1: Input Sanitization ──
        content = sanitize_input(content)  # Strip HTML, limit length
        await emit("stage", {"stage": "understanding"})

        # ── STEP 2: PII Detection ──
        pii_result = check_for_pii(content)
        if pii_result.has_pii:
            await emit("warning", {"message": "Please don't share personal identifying information."})
            await emit("done", {})
            return

        # ── STEP 3: Greeting Detection ──
        if is_greeting(content):
            greeting_response = generate_greeting(user_id)
            await emit("response", {"content": greeting_response})
            await emit("done", {})
            return

        # ── STEP 4: Translation (Swarm 0) ──
        user_language = await get_user_language(user_id)
        if user_language != "en":
            translated = await swarm_0.execute_with_retry(
                translate_messages(content, user_language, "en"), trace_id)
            content_en = translated
        else:
            content_en = content

        # ── STEP 5: Gatekeeper (Swarm 1) ──
        await emit("stage", {"stage": "checking"})
        gate_result = await swarm_1.execute_with_retry(
            classify_messages(content_en), trace_id)

        if not gate_result.get("safe", True):
            await emit("response", {"content": "I'm designed to help with fertility and wellness questions. Could you rephrase that?"})
            await emit("done", {})
            return

        if not gate_result.get("is_fertility_related", True):
            await emit("response", {"content": "That's a great question, but it's outside my expertise. I'm best at fertility, nutrition, and wellness topics."})
            await emit("done", {})
            return

        # ── STEP 6: Context (Swarm 9) ──
        context = await swarm_9.execute_with_retry(
            context_messages(user_id), trace_id)

        # ── STEP 7: RAG Search (Swarm 3) ──
        await emit("stage", {"stage": "searching"})
        queries = await generate_search_queries(content_en, context)
        rag_results = await swarm_3.search(queries)

        # Emit sources one by one
        for source in rag_results.top_matches:
            await emit("source", {
                "title": source.metadata.get("title", "Clinical Source"),
                "relevance": source.score
            })
        await emit("stage", {"stage": "found", "count": len(rag_results.top_matches)})

        # ── STEP 8: Response Generation (Swarm 4) — FULL response ──
        await emit("stage", {"stage": "crafting"})
        response = await swarm_4.execute_with_retry(
            curate_messages(content_en, context, rag_results, user_id), trace_id)

        # ── STEP 9: Compliance Check (Swarm 7) — BEFORE streaming (Decision 9) ──
        checked_response = await swarm_7.execute_with_retry(
            compliance_messages(response.content), trace_id)
        final_content = checked_response  # May have appended disclaimer

        # ── STEP 10: Translate Back (Swarm 0) ──
        if user_language != "en":
            final_content = await swarm_0.execute_with_retry(
                translate_messages(final_content, "en", user_language), trace_id)

        # ── NOW stream the approved, checked, translated text token-by-token ──
        words = final_content.split(" ")
        for word in words:
            await emit("token", {"text": word + " "})
            await asyncio.sleep(0.02)  # 50 words/sec feels natural

        # ── STEP 11: Follow-Up Questions ──
        follow_ups = response.follow_up_questions[:3] if hasattr(response, 'follow_up_questions') else []
        await emit("followups", {"questions": follow_ups})

        # ── STEP 12: Background Tasks (fire-and-forget within worker) ──
        await save_chat_log(user_id, content, final_content, trace_id)
        await update_context(user_id, content, final_content)
        # These are lightweight DB writes, safe to run in worker
        try:
            await swarm_8.execute_with_retry(gap_messages(content_en, rag_results), trace_id)
        except Exception:
            pass  # Gap detection is non-critical
        try:
            await swarm_10.execute_with_retry(sentiment_messages(content_en, final_content), trace_id)
        except Exception:
            pass  # Sentiment is non-critical

        await emit("done", {})

    except Exception as e:
        logger.error(f"Chat pipeline error: {e}", exc_info=True)
        await emit("error", {"message": "Something went wrong. Please try again."})
```

```python
# app/api/chat.py — SSE endpoint (reads from Redis stream)

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user_id: str = Depends(get_user_id)):
    """Enqueue chat task, then stream results via SSE from Redis."""
    task_id = str(uuid4())

    # Enqueue the pipeline task
    await arq_pool.enqueue_job("chat_pipeline_task", task_id, user_id, request.content)

    async def event_generator():
        redis = get_redis()
        last_id = "0"
        timeout_at = time.monotonic() + 120  # 2-minute max

        while time.monotonic() < timeout_at:
            # Read new events from the Redis stream
            events = await redis.xread({f"chat:{task_id}": last_id}, count=10, block=500)

            for stream_name, messages in events:
                for msg_id, fields in messages:
                    last_id = msg_id
                    event_type = fields[b"event"].decode()
                    data = fields[b"data"].decode()
                    yield f"event: {event_type}\ndata: {data}\n\n"

                    if event_type in ("done", "error"):
                        # Cleanup: delete the Redis stream
                        await redis.delete(f"chat:{task_id}")
                        return

        # Timeout
        yield f"event: error\ndata: {{\"message\": \"Request timed out\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# Note: The REST fallback endpoint (/chat without /stream) uses the same task queue
# but blocks and returns the complete response as JSON instead of streaming.
```

> **Render SSE Note:** Render's proxy supports SSE natively. The `X-Accel-Buffering: no` header is included for compatibility but Render doesn't use Nginx. Test SSE streaming on Render during Stage 22 deployment.
```

## M5. SSE Event Format

```
event: stage
data: {"stage": "understanding"}

event: stage
data: {"stage": "searching"}

event: source
data: {"title": "ESHRE IVF Guidelines 2024", "relevance": 0.87}

event: source
data: {"title": "Fertility & Sterility Journal", "relevance": 0.82}

event: stage
data: {"stage": "found", "count": 4}

event: stage
data: {"stage": "crafting"}

event: token
data: {"text": "During"}

event: token
data: {"text": " IVF"}

event: token
data: {"text": " stims,"}

... (continues token by token)

event: followups
data: {"questions": ["What about protein intake?", "Are supplements helpful?", "How much water should I drink?"]}

event: done
data: {}
```

## M6. Swarm Configuration Details

Each swarm has specific model, temperature, and token settings:

```python
SWARM_CONFIG = {
    "swarm_0_polyglot": {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.1,  # Low — translation needs accuracy
        "max_tokens": 2000,
        "timeout_seconds": 15,
        "fallback_model": "llama-3.1-8b-instant",
    },
    "swarm_1_gatekeeper": {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.0,  # Zero — classification must be deterministic
        "max_tokens": 200,
        "timeout_seconds": 10,
        "fallback_model": "llama-3.1-8b-instant",
    },
    "swarm_3_clinical_brain": {
        "embedding_model": "text-embedding-3-small",  # OpenAI
        "embedding_dimensions": 384,
        "match_threshold": 0.5,
        "match_count": 10,
        "multi_query_count": 3,  # Generate 3 search variations
        "reranking": True,  # Cross-query deduplication + score boosting
    },
    "swarm_4_curator": {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.4,  # Moderate — needs creativity but accuracy
        "max_tokens": 1500,
        "timeout_seconds": 30,
        "fallback_model": "llama-3.1-70b-versatile",
        "system_prompt_template": "SWARM_4_PROMPT",  # Loaded from admin_prompts table
    },
    "swarm_5_analyser": {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.2,
        "max_tokens": 2000,
        "timeout_seconds": 20,
    },
    "swarm_6_bloodwork_curator": {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "max_tokens": 2000,
        "timeout_seconds": 20,
    },
    "swarm_7_compliance": {
        "model": "llama-3.1-8b-instant",  # Small, fast — just checks
        "temperature": 0.0,
        "max_tokens": 500,
        "timeout_seconds": 10,
    },
    "swarm_8_gap": {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.0,
        "max_tokens": 200,
        "timeout_seconds": 10,
    },
    "swarm_9_context": {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.1,
        "max_tokens": 300,
        "timeout_seconds": 10,
        "context_priority": {
            "P0": ["phase+day+treatment (~20 tokens)", "plan summary (~50 tokens)", "key bloodwork (~40 tokens)"],
            "P1": ["last 3 check-ins (~40 tokens)", "last 3 messages (~150 tokens)"],
            "total_budget": "~300 tokens, leaves 500 for generation"
        }
    },
    "swarm_10_sentiment": {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.0,
        "max_tokens": 100,
        "timeout_seconds": 8,
    },
}
```

## M7. Groq Client with Multi-Key Rotation

```python
# app/services/groq_client.py

class GroqClientManager:
    """Manages multiple Groq API keys with rotation and circuit breaking."""
    
    def __init__(self):
        keys = settings.GROQ_API_KEYS.split(",") if settings.GROQ_API_KEYS else [settings.GROQ_API_KEY]
        self.keys = [k.strip() for k in keys if k.strip()]
        self.current_index = 0
        self.circuit_breakers = {key: CircuitBreaker(failure_threshold=3, reset_timeout=60) for key in self.keys}
        self.semaphore = asyncio.Semaphore(settings.GROQ_MAX_CONCURRENT_REQUESTS)
    
    def _get_client(self) -> Groq:
        """Get next available client using round-robin."""
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            if not self.circuit_breakers[key].is_open:
                return Groq(api_key=key)
        raise AllKeysExhaustedError("All Groq API keys are circuit-broken")
    
    async def chat_completion(self, messages, model, temperature=0.3, max_tokens=1000, **kwargs):
        """Make a completion request with retry and fallback."""
        async with self.semaphore:
            last_error = None
            for attempt in range(3):
                try:
                    client = self._get_client()
                    response = await asyncio.to_thread(
                        client.chat.completions.create,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    return response
                except (RateLimitError, APIError) as e:
                    last_error = e
                    self.circuit_breakers[client.api_key].record_failure()
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            raise last_error
```

## M8. RAG Engine (ClinicalBrain — Swarm 3)

```python
# app/services/swarm_3_clinical.py

class ClinicalBrain:
    """RAG engine: search 236 clinical documents via pgvector."""
    
    async def search(self, queries: list[str]) -> RAGResult:
        """Multi-query search with deduplication and relevance boosting."""
        
        all_results = []
        seen_ids = set()
        
        for query in queries:
            # Generate embedding
            embedding = await self._embed(query)
            
            # Search via Supabase pgvector
            matches = await supabase.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": 10,
                }
            ).execute()
            
            for match in matches.data:
                if match["id"] not in seen_ids:
                    seen_ids.add(match["id"])
                    all_results.append(match)
                else:
                    # Cross-query boost: if same doc found by multiple queries, boost score
                    for r in all_results:
                        if r["id"] == match["id"]:
                            r["similarity"] = min(1.0, r["similarity"] + 0.1)
        
        # Sort by similarity, take top 5
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = all_results[:5]
        
        # Graceful degradation
        if not top_results:
            return RAGResult(matches=[], degradation_level=4, message="No relevant clinical sources found.")
        elif top_results[0]["similarity"] < 0.6:
            return RAGResult(matches=top_results, degradation_level=2, message="Limited sources found.")
        
        return RAGResult(matches=top_results, degradation_level=0)
    
    async def _embed(self, text: str) -> list[float]:
        """Generate embedding via OpenAI."""
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=384,
        )
        return response.data[0].embedding
```

## M9. Rate Limiting

```python
# Per-endpoint rate limits
RATE_LIMITS = {
    "/api/v1/chat":           (10, 60),    # 10 requests per 60 seconds per user
    "/api/v1/chat/stream":    (10, 60),
    "/api/v1/preview/ask":    (1, 600),    # 1 per 10 minutes per IP (landing page)
    "/api/v1/analyze-file":   (5, 300),    # 5 per 5 minutes (bloodwork upload)
    "/api/v1/recovery/attempt": (3, 3600), # 3 per hour (brute force protection)
    "/api/v1/auth/lookup":    (10, 60),    # (Decision 6) 10 per minute per IP
}

# Account lockout (A6.2 — stored in Redis, NOT in rate limits table)
ACCOUNT_LOCKOUT = {
    "max_attempts": 5,        # Failed password attempts per pseudonym
    "lockout_minutes": 15,    # Lockout duration
    "redis_key_pattern": "lockout:{pseudonym}",  # Redis key with TTL
}
# On failed signInWithPassword: increment Redis counter.
# If counter >= 5: return "Too many login attempts. Please try again in 15 minutes."
# Redis key auto-expires after 15 minutes (TTL).
```

## M10. Error Handling Pattern

Every service follows the same error handling pattern:

```python
# Every endpoint uses this try/except structure
@router.post("/endpoint")
async def endpoint(request: Request, user_id: str = Depends(get_user_id)):
    try:
        # Business logic
        result = await service.do_something(user_id, request)
        return result
    except ValidationError as e:
        raise HTTPException(422, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(429, detail="Too many requests", headers={"Retry-After": "30"})
    except ExternalServiceError as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(500, detail="Internal server error")
```

## M11. Complete API Endpoint Map

### Chat & Conversation
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /chat | User | Send message (REST fallback) |
| POST | /chat/stream | User | SSE streaming chat |
| GET | /personalized-questions | User | 7 sets of 3 questions per gender/language |
| POST | /chat/feedback | User | Quick score (1/0) |
| POST | /chat/feedback/detailed | User | Rich feedback with issues |
| DELETE | /chat/history | User | GDPR data deletion |
| GET | /chat/search | User | Search conversations |

### Preview (No Auth)
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /preview/cached-responses | None | Pre-cached landing page responses |
| POST | /preview/ask | None (IP rate limited) | Real-time preview question |

### Chapters & Journey
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /chapters | User | List all chapters for current cycle |
| GET | /chapters/active | User | Get active chapter |
| GET | /chapters/{id}/messages | User | Get messages for a chapter |
| POST | /journey | User | Create treatment journey |
| GET | /journey | User | Get active journey |
| POST | /journey/transition | User | Record phase transition |

### Bloodwork
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /analyze-file | User | Upload PDF/image |
| POST | /confirm-results | User | Confirm extracted values |
| POST | /analyze-bloodwork | User | Trigger analysis |

### Companion
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /companion/context | User | Journey context |
| POST | /companion/checkin | User | Daily mood check-in |
| GET | /companion/checkin/history | User | Past check-ins |
| GET | /companion/symptoms/{phase} | User | Phase symptoms |
| GET | /companion/content/{phase} | User | Phase tips |
| POST | /outcome/record | User | Record cycle outcome |

### Nutrition & Plans
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /nutrition/wellness-profile | User | Get wellness profile |
| POST | /nutrition/wellness-profile | User | Update wellness profile |
| POST | /nutrition/meals | User | Log meal completion |
| POST | /nutrition/activities | User | Log activity completion |
| GET | /nutrition/dashboard | User | Dashboard data |
| GET | /plan-status | User | Check plan review status |
| GET | /nutrition/plan/current | User | Get current approved plan |

### Partner
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /partner/invite | User | Generate invite code |
| POST | /partner/join | User | Join with code |
| GET | /partner/dashboard | User | Partner view data |
| GET | /partner/status | User | Link status |
| PUT | /partner/visibility | User | Update visibility |
| DELETE | /partner/link | User | Revoke link |

### Content
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /content/library | User | Browse content |
| GET | /content/{id}/stream-url | User | Get signed Cloudflare URL |
| POST | /content/{id}/progress | User | Update watch/listen progress |
| POST | /content/{id}/rating | User | Rate content |

### Provider Portal
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /reports/share | User | Generate share token |
| GET | /reports/portal/{token} | None | View shared report |
| GET | /reports/download/{token} | None | Download PDF |

### Push Notifications
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /push/vapid-key | User | Public key |
| POST | /push/subscribe | User | Subscribe |
| DELETE | /push/subscribe | User | Unsubscribe |

### Privacy
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| DELETE | /delete-account | User | GDPR deletion |
| POST | /recovery/generate | User | Generate recovery phrase |
| POST | /recovery/attempt | None | Recovery login |

### Nutritionist Portal
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /nutritionist/queue | Admin | View approval queue |
| GET | /nutritionist/queue/stats | Admin | Queue statistics |
| POST | /nutritionist/queue/{id}/assign | Admin | Assign plan to self |
| GET | /nutritionist/plan/{id} | Admin | Get plan for review |
| POST | /nutritionist/plan/{id}/approve | Admin | Approve plan |
| POST | /nutritionist/plan/{id}/modify | Admin | Modify and approve |
| POST | /nutritionist/plan/{id}/reject | Admin | Reject plan |
| GET | /nutritionist/assignments | Admin | My assigned plans |
| GET | /nutritionist/analytics | Admin | Modification patterns |

### Admin
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | /admin/dashboard | Admin | KPI overview |
| GET | /admin/analytics/* | Admin | Gaps, citations, sentiment |
| GET | /admin/health | Admin | Swarm health status |
| GET | /admin/models | Admin | LLM model status |
| GET/PUT | /admin/prompts/{swarm} | Admin | Edit swarm prompts |
| GET | /admin/dpo/* | Admin | DPO training data |
| GET | /admin/content/* | Admin | Content management |
| GET | /admin/fie/* | Admin | FIE dashboard |

---

# SECTION N: CHATBOT RULES & PERSONA

## N1. Izana's Persona

Izana is a **warm, knowledgeable fertility companion**. Not a doctor, not a nurse, not a therapist — a trusted friend who happens to know a lot about fertility science.

**Voice characteristics:**
- First person singular ("I" not "we")
- Warm but not saccharine
- Knowledgeable but not clinical
- Empathetic but not pitying
- Direct but not blunt
- Uses the user's pseudonym occasionally (not every message)
- Never says "I understand how you feel" (she doesn't — she's AI)
- Instead says "That sounds really tough" or "Many women in your phase feel that way"

## N2. Response Rules

```
╔═══════════════════════════════════════════════════════════════╗
║ 1. ALWAYS cite sources. Every clinical claim needs a source. ║
║ 2. ALWAYS add medical disclaimer on clinical responses.      ║
║ 3. NEVER diagnose or prescribe.                              ║
║    Say: "Your doctor would be the best person to advise on..." ║
║ 4. NEVER give specific dosage recommendations.               ║
║ 5. ALWAYS acknowledge emotions before giving information.    ║
║    "That sounds worrying. Here's what the research says..."  ║
║ 6. NEVER mention other users' data or outcomes.              ║
║    "Many women find that..." is OK. "Users report..." is not.║
║ 7. ALWAYS use phase-appropriate language.                    ║
║    During TWW: hopeful, not anxious. During stims: strong.   ║
║ 8. NEVER say "don't worry" or "it'll be fine."               ║
║    Instead: "It's completely normal to feel that way."        ║
║ 9. MAX response length: 200 words for simple questions,      ║
║    400 words for complex ones. Never wall-of-text.           ║
║ 10. ALWAYS offer follow-up questions (up to 3).              ║
╚═══════════════════════════════════════════════════════════════╝
```

## N3. Greeting Rules

Time-based greetings (based on user's timezone):

| Time | Greeting |
|------|----------|
| 5am-11am | "Good morning ✨" |
| 11am-5pm | "Good afternoon ✨" |
| 5pm-9pm | "Good evening ✨" |
| 9pm-5am | "Hope you're resting well ✨" |

First message of the day includes phase context:
"Good morning ✨ Day 8 of stims — you're getting close."

## N4. Swarm 4 System Prompt Template

This is the core prompt that generates responses. It's stored in `admin_prompts` and editable by admins:

```
You are Izana, a fertility wellness companion. You help women going through fertility treatments with evidence-based information, emotional support, and practical guidance.

CONTEXT ABOUT THIS USER:
{context_summary}  ← From Swarm 9

RELEVANT CLINICAL SOURCES:
{rag_sources}  ← From Swarm 3

RULES:
1. Be warm and empathetic. Acknowledge emotions first, then provide information.
2. Cite sources using [Source Name] format.
3. Keep responses concise: 100-200 words for simple questions, 200-400 for complex.
4. End with a medical disclaimer if the response contains clinical information.
5. Generate 2-3 follow-up questions the user might want to ask.
6. Never diagnose. Never prescribe. Never give dosage advice.
7. Use the user's treatment phase to contextualise your response.
8. If the knowledge base doesn't have relevant information, say so honestly.
9. Never make up studies or statistics.
10. Use "your doctor" not "a doctor" — personalise the referral.

USER'S QUESTION:
{question}

Respond in a warm, knowledgeable tone. Structure: empathy → information → disclaimer → follow-ups.
```

## N5. Compliance Checker Rules (Swarm 7)

Swarm 7 checks every response for:

| Check | Rule | Auto-fix |
|-------|------|----------|
| Medical disclaimer | Present on clinical responses | Append: "⚕️ Always consult your doctor..." |
| Diagnosis language | No "you have" / "you might have" | Rephrase to "your doctor can evaluate..." |
| Dosage mentions | No specific mg/ml amounts | Remove specific numbers, say "your doctor will advise on dosage" |
| Tone check | Not too clinical, not too casual | Flag for review if detected |
| Citation present | At least 1 source on clinical responses | Flag as knowledge gap if no source |
| Length check | Under 400 words | Truncate and add "Would you like me to go into more detail?" |
| PII in response | No user PII repeated back | Strip any PII detected |

---

---

# SECTION O: USER LOGIN FLOW (Returning Users)

## O1. Login Modal

When user taps "Log in" on the landing page, a bottom-sheet modal slides up (same pattern as signup):

```
┌─────────────────────────────────┐
│  ░░░░ (dimmed chat behind) ░░░░ │
├──── ▬▬▬ drag handle ▬▬▬ ────────┤
│                                 │
│        Welcome back ✨           │
│                                 │
│  Pseudonym                      │
│  ┌───────────────────────────┐  │
│  │ BraveOcean42              │  │
│  └───────────────────────────┘  │
│                                 │
│  Password                       │
│  ┌───────────────────────────┐  │
│  │ ••••••••         [show]   │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌─────────────────────────┐    │
│  │      Welcome back       │    │  ← Primary button
│  └─────────────────────────┘    │
│                                 │
│  Forgot password?               │  ← Opens recovery modal
│                                 │
└─────────────────────────────────┘
```

**Login flow (Decision 6 — anti-enumeration):**
```
1. User enters pseudonym + password
2. Frontend calls: GET /api/v1/auth/lookup?pseudonym=BraveOcean42
3. Backend ALWAYS returns 200: { email: "BraveOcean42@users.izana.ai" }
   (Decision 6: returns the SAME response regardless of whether the pseudonym
    exists. This prevents enumeration of the ~13,000 possible pseudonyms.)
   Rate limit: 10 requests per minute per IP.
4. Frontend calls: supabase.auth.signInWithPassword({ email, password })
5. On success: store session, fetch profile, redirect to /chat
6. On failure: "Pseudonym or password is incorrect. Try again or use your recovery phrase."
   (User cannot distinguish "wrong pseudonym" from "wrong password" — intentional.)
```

**Recovery flow:**
```
1. User taps "Forgot password?"
2. Recovery modal appears:
   ┌───────────────────────────┐
   │  Account recovery         │
   │                           │
   │  Pseudonym                │
   │  [________________]       │
   │                           │
   │  Recovery phrase          │
   │  [XXXX-XXXX-XXXX-XXXX]   │
   │                           │
   │  New password             │
   │  [________________]       │
   │                           │
   │  [Reset my password]      │
   └───────────────────────────┘
3. Backend: POST /api/v1/recovery/attempt
   - Look up user by pseudonym
   - Hash submitted phrase with stored salt
   - Compare with stored hash
   - If match: allow password reset via supabase.auth.updateUser()
   - Rate limited: 3 attempts per hour per IP
```

---

# SECTION P: NUTRITIONIST PORTAL (Complete Specification)

## P1. Who Are Nutritionists?

Nutritionists are professional staff employed by Izana. They are NOT regular users. They have their own login, their own portal, and their own database table (`admin_users`). There can be multiple nutritionists, and one or more admins who manage the team.

**Roles:**
- `NUTRITIONIST` — can review and approve/modify/reject plans in their queue
- `ADMIN` — everything a nutritionist can do, PLUS manage other nutritionist accounts

## P2. Nutritionist Login

The nutritionist portal lives at `/nutritionist/login`. It is completely separate from the user-facing app — different layout, no bottom nav, no chat.

```
┌─────────────────────────────────────────────┐
│                                             │
│                  [izana logo]               │
│              Nutritionist Portal            │
│                                             │
│  Email                                      │
│  ┌───────────────────────────────────────┐  │
│  │ sarah@izana.ai                        │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Password                                   │
│  ┌───────────────────────────────────────┐  │
│  │ ••••••••                     [show]   │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │            Sign in                    │  │
│  └───────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

**Auth flow:**
```
1. Nutritionist enters email + password
2. Frontend calls: POST /api/v1/nutritionist/auth/login
3. Backend:
   - Look up email in admin_users table
   - Verify password hash (bcrypt)
   - Check is_active = true
   - Return JWT token + user details (name, role)
4. Frontend stores JWT in sessionStorage["izana_nutritionist_token"]
5. All subsequent API calls include: Authorization: Bearer {token}
6. Session expires after 8 hours (shift-length)
```

**NutritionistAuthGuard (frontend component):**
```tsx
// Wraps all /nutritionist/* pages except /nutritionist/login
// Checks sessionStorage for valid token
// Redirects to /nutritionist/login if missing or expired
// Passes nutritionist data (name, role) via context
```

## P3. Nutritionist Portal Layout

**Desktop only** (nutritionists use laptops, not phones). Minimum width: 1024px.

```
┌──────────────────────────────────────────────────────┐
│  izana · Nutritionist Portal    Sarah K.  [Sign out] │  ← Top bar
├────────────┬─────────────────────────────────────────┤
│            │                                         │
│  SIDEBAR   │          MAIN CONTENT                   │
│            │                                         │
│  ┌──────┐  │   (changes based on active page)        │
│  │Queue │  │                                         │
│  │  12  │  │                                         │
│  └──────┘  │                                         │
│            │                                         │
│  My Plans  │                                         │
│     3      │                                         │
│            │                                         │
│  Analytics │                                         │
│            │                                         │
│  ──────    │                                         │
│  Admin     │  ← Only visible if role = ADMIN         │
│            │                                         │
│            │                                         │
│            │                                         │
│  ──────    │                                         │
│  [urgent]  │  ← Red badge if urgent plans waiting    │
│  2 urgent  │                                         │
│            │                                         │
├────────────┴─────────────────────────────────────────┤
```

Sidebar width: 220px. Always visible on desktop.

## P4. Queue Page (`/nutritionist/queue`)

This is the nutritionist's primary work screen.

### Stats Cards (top row)
```
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  Pending   │ │ In Review  │ │   Urgent   │ │  Overdue   │
│    12      │ │     3      │ │     2      │ │     1      │
│  ○ yellow  │ │  ○ blue    │ │  ○ orange  │ │  ○ red     │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

### Filters Row
```
[Status: All ▾]  [Priority: All ▾]  [Search user...]
```

### Queue Table
```
┌─────────────────────┬───────────┬──────────┬──────────────┬─────────┐
│ User                │ Status    │ Priority │ Deadline     │ Action  │
├─────────────────────┼───────────┼──────────┼──────────────┼─────────┤
│ BraveOcean42        │ ● Pending │ 🔴 Urgent│ 2h remaining │[Assign] │
│ IVF · Stims Day 8   │           │ Phase    │ (orange)     │         │
│ Dairy-free           │           │ change   │              │         │
├─────────────────────┼───────────┼──────────┼──────────────┼─────────┤
│ HopefulRiver17      │ ● Pending │ Normal   │ 3h remaining │[Assign] │
│ IUI · Preparing      │           │          │ (green)      │         │
│ Vegetarian, nut-free │           │          │              │         │
├─────────────────────┼───────────┼──────────┼──────────────┼─────────┤
│ LuminousCoral88     │ ○ In      │ Normal   │ 1h remaining │[Review] │
│ Natural · TWW        │ Review    │          │ (yellow)     │         │
│ No restrictions      │ (by you)  │          │              │         │
├─────────────────────┼───────────┼──────────┼──────────────┼─────────┤
│ GentleBloom23       │ ● Pending │ 🟢 Posit │ 4h remaining │[Assign] │
│ IVF · Positive!      │           │ outcome  │ (green)      │         │
│ Gluten-free          │           │          │              │         │
└─────────────────────┴───────────┴──────────┴──────────────┴─────────┘
```

**Table details:**
- User column shows: pseudonym, treatment type + phase, key allergies/restrictions (as coloured badges)
- Priority column: `normal` (grey), `urgent_phase_change` (orange with "Phase change" label), `positive_outcome` (green with "Positive!" label)
- Deadline: colour-coded. Green (>3h), Yellow (1-3h), Orange (<1h), Red (overdue)
- Action: "Assign to me" for unassigned plans, "Review" for plans assigned to current nutritionist
- Pagination: 10 per page

**Clicking "Assign to me":**
1. `approval_queue.status` → 'ASSIGNED'
2. `approval_queue.assigned_to` → current nutritionist ID
3. Button changes to "Review"
4. Toast: "Plan assigned to you"

## P5. Plan Review Page (`/nutritionist/review/[planId]`)

This is a 3-panel layout. This is where the nutritionist actually reads and edits the plan.

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back to queue                    BraveOcean42 · IVF Stims Day 8 │
├───────────────┬─────────────────────────────────┬────────────────────┤
│               │                                 │                    │
│ USER CONTEXT  │      PLAN EDITOR                │   AI CONTEXT       │
│ (272px)       │      (flex-1)                   │   (320px)          │
│               │                                 │                    │
│ Treatment     │  ┌─[Nutrition]─[Exercise]─┐     │ Priority           │
│ IVF · Stims   │  │        [Meditation]    │     │ 🔴 URGENT          │
│ Day 8 of ~10  │  │                        │     │ Phase change       │
│               │  │ BREAKFAST              │     │                    │
│ Allergies     │  │ ┌────────────────────┐ │     │ Deadline           │
│ 🔴 Dairy      │  │ │Avocado toast +     │ │     │ 2h 15m remaining   │
│               │  │ │poached eggs        │ │     │                    │
│ Restrictions  │  │ │                    │ │     │ ──────             │
│ Dairy-free    │  │ │Sourdough, avocado, │ │     │                    │
│               │  │ │2 eggs, microgreens,│ │     │ AI Reasoning       │
│ Preferences   │  │ │pumpkin seeds       │ │     │ "Chose high-       │
│ Mediterranean │  │ │                    │ │     │  folate breakfast   │
│ Asian         │  │ │Reasoning: folate   │ │     │  because user is   │
│               │  │ │from greens, choline│ │     │  in stims phase.   │
│ Exercise pref │  │ │from eggs...        │ │     │  Mediterranean     │
│ Yoga, walking │  │ └────────────────────┘ │     │  preference        │
│               │  │                        │     │  applied."         │
│ Dislikes      │  │ LUNCH                  │     │                    │
│ Cilantro      │  │ ┌────────────────────┐ │     │ FIE Insights       │
│               │  │ │Salmon quinoa bowl  │ │     │ "Mediterranean     │
│ Fitness       │  │ │[editable...]       │ │     │  diets during      │
│ Moderate      │  │ └────────────────────┘ │     │  stims: 23% better │
│               │  │                        │     │  outcomes"          │
│ BMI: 22.5     │  │ DINNER                 │     │                    │
│               │  │ ┌────────────────────┐ │     │ Review History      │
│ Bloodwork     │  │ │Bone broth + sweet  │ │     │ (first plan —      │
│ AMH: 2.1      │  │ │potato              │ │     │  no history)       │
│ FSH: 7.2      │  │ │[editable...]       │ │     │                    │
│ E2: 1200      │  │ └────────────────────┘ │     │                    │
│ (day 8)       │  │                        │     │                    │
│               │  │ EXERCISE               │     │                    │
│ Age: 31-35    │  │ ┌────────────────────┐ │     │                    │
│               │  │ │Gentle stims yoga   │ │     │                    │
│ Health: None  │  │ │EX-007, 20 min      │ │     │                    │
│               │  │ │No inversions ✓     │ │     │                    │
│ Smoking: No   │  │ └────────────────────┘ │     │                    │
│ Alcohol: No   │  │                        │     │                    │
│               │  │ MEDITATION             │     │                    │
│               │  │ ┌────────────────────┐ │     │                    │
│               │  │ │Follicle growth vis │ │     │                    │
│               │  │ │MD-005, 10 min      │ │     │                    │
│               │  │ └────────────────────┘ │     │                    │
│               │  │                        │     │                    │
├───────────────┴──┴────────────────────────┴─────┴────────────────────┤
│  Modifications: 0  │  [Approve]  [Modify & Approve]  [Reject]       │
└──────────────────────────────────────────────────────────────────────┘
```

### Editing a Field
When the nutritionist changes any text in the plan editor:
1. The field gets an orange left border (highlighting the modification)
2. The modification counter in the bottom bar increments
3. When they click "Modify & Approve", a modification capture modal appears for EACH changed field

### Modification Capture Modal
```
┌────────────────────────────────────────────────────┐
│  Modification 1 of 2                               │
│                                                    │
│  Field: Breakfast → name                           │
│                                                    │
│  AI Original:                                      │
│  "Avocado toast with poached eggs"                 │
│                                                    │
│  Your Change:                                      │
│  "Avocado toast with scrambled eggs and spinach"   │
│                                                    │
│  Reason (required):                                │
│  ┌──────────────────────────────────────────────┐  │
│  │ Added spinach for extra iron. Scrambled is   │  │
│  │ easier to prepare during stims fatigue.      │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Category:                                         │
│  [Allergen Safety] [Dietary Restriction]           │
│  [Phase Mismatch] [Calorie Adjustment]             │
│  [Nutrient Optimization ✓] [Preference Align]      │
│  [Cultural Sensitivity]                            │
│                                                    │
│  Severity:                                         │
│  [Minor ✓] [Moderate] [Major] [Critical]           │
│                                                    │
│  ☐ Could cause harm if AI version was delivered    │
│    (red warning checkbox)                          │
│                                                    │
│  [← Previous]  [Next modification →]               │
│                                                    │
│  [Save all modifications & approve plan]           │
└────────────────────────────────────────────────────┘
```

**Each modification is saved to `plan_modifications` table:**
```sql
INSERT INTO plan_modifications (
  plan_id, section, field_path,
  ai_original, human_modified,
  reason, category, severity,
  could_cause_harm, training_eligible,
  reviewer_id
) VALUES (...);
```

This data is used for DPO (Direct Preference Optimisation) training — it teaches the AI what humans prefer over what it generated.

### Reject Modal
```
┌────────────────────────────────────────────┐
│  Reject Plan                               │
│                                            │
│  Reason (required, min 20 chars):          │
│  ┌──────────────────────────────────────┐  │
│  │ Plan includes dairy ingredients      │  │
│  │ despite user being dairy-free.       │  │
│  │ Multiple meals affected. Needs       │  │
│  │ complete regeneration.               │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ☐ Request AI regeneration with these      │
│    specific instructions:                  │
│  ┌──────────────────────────────────────┐  │
│  │ Strictly dairy-free. Replace all     │  │
│  │ cheese with nutritional yeast.       │  │
│  │ Replace yogurt with coconut yogurt.  │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  [Cancel]              [Reject plan]       │
└────────────────────────────────────────────┘
```

On reject:
1. `personalized_plans.status` → 'REJECTED'
2. If regeneration requested: new plan generated with rejection context
3. New plan enters queue automatically
4. User is NOT notified of rejection (they just continue waiting)

## P6. Nutritionist Analytics (`/nutritionist/analytics`)

```
┌─────────────────────────────────────────────────────────┐
│  Modification Patterns          [7d] [14d] [30d] [90d] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Top Category     │  │ Severity Dist   │              │
│  │                  │  │                 │              │
│  │ Allergen    32%  │  │ Minor     45%   │              │
│  │ Nutrient    28%  │  │ Moderate  30%   │              │
│  │ Preference  22%  │  │ Major     20%   │              │
│  │ Phase       12%  │  │ Critical   5%   │              │
│  │ Other        6%  │  │                 │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  ⚠️ Critical Issues (last 30 days)                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 3 plans included allergens the user flagged.     │    │
│  │ 2 plans had exercise intensity too high for TWW. │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  Recent Modifications                                   │
│  ┌────────┬──────────┬──────────┬──────────┬────────┐   │
│  │ User   │ Category │ Severity │ Harm?    │ Date   │   │
│  ├────────┼──────────┼──────────┼──────────┼────────┤   │
│  │ Brave..│ Allergen │ Major    │ Yes ⚠️   │ Today  │   │
│  │ Hope.. │ Nutrient │ Minor    │ No       │ Today  │   │
│  │ Luna.. │ Prefer.  │ Minor    │ No       │ Yester │   │
│  └────────┴──────────┴──────────┴──────────┴────────┘   │
│                                                         │
│  [Export DPO training data]                             │
└─────────────────────────────────────────────────────────┘
```

## P7. Nutritionist Admin (`/nutritionist/admin`) — ADMIN role only

```
┌─────────────────────────────────────────────────────────┐
│  Team Management                      [+ Add member]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────┬──────────────┬─────────┬────────┬────────┐  │
│  │ Name   │ Email        │ Role    │ Active │ Action │  │
│  ├────────┼──────────────┼─────────┼────────┼────────┤  │
│  │ Sarah K│ sarah@iz..   │ Admin   │ ✓ Yes  │ [Edit] │  │
│  │ Priya M│ priya@iz..   │ Nutri.  │ ✓ Yes  │ [Edit] │  │
│  │ James L│ james@iz..   │ Nutri.  │ ✗ No   │ [Edit] │  │
│  └────────┴──────────────┴─────────┴────────┴────────┘  │
│                                                         │
│  Add Member Modal:                                      │
│  ┌───────────────────────────────────────┐              │
│  │ Name: [______________]                │              │
│  │ Email: [______________]               │              │
│  │ Role: [Nutritionist ▾]               │              │
│  │ Temporary password: [auto-generated]  │              │
│  │                                       │              │
│  │ [Cancel]            [Add member]      │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

# SECTION Q: ADMIN DASHBOARD (Complete 8-Tab Specification)

## Q1. Admin Login

The admin dashboard lives at `/admin`. It uses a simple API key auth (not Supabase user auth).

```
┌─────────────────────────────────────────────┐
│                                             │
│              [izana logo]                   │
│           Admin Dashboard                   │
│                                             │
│  Email                                      │
│  ┌───────────────────────────────────────┐  │
│  │ admin@izana.com                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  API Key                                    │
│  ┌───────────────────────────────────────┐  │
│  │ ••••••••••••••••••••                  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │            Enter Dashboard            │  │
│  └───────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

**Auth flow:**
```
1. Admin enters email + API key
2. Frontend checks: email === process.env.NEXT_PUBLIC_ADMIN_EMAIL
3. Stores API key in sessionStorage["izana_admin_key"]
4. All admin API calls include: X-Admin-API-Key: {key}
5. Backend verifies: key === settings.ADMIN_API_KEY
```

## Q2. Admin Layout

**Desktop only.** Tabs across the top:

```
┌──────────────────────────────────────────────────────────────────┐
│  izana · Admin                                        [Sign out] │
├──────────────────────────────────────────────────────────────────┤
│  [Dashboard] [Analytics] [Feedback] [Training] [Health]          │
│  [Prompts] [Content] [Plans Queue]                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    TAB CONTENT                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Q3. Tab 1: Dashboard

**KPI Cards (top row):**
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total Users  │ │ Active Today │ │ AI Accuracy  │ │ Plans Queue  │
│    1,247     │ │     342      │ │    87.3%     │ │    12 / 2 ⚠️ │
│ +23 this wk  │ │ +8% vs last  │ │ (thumbs up)  │ │ pending/urgt │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**Charts:**
- User growth (line chart, last 30 days)
- Check-in completion rate (line chart, last 30 days)
- Plan adherence by treatment type (bar chart)
- Bloodwork gaps (bar chart: missing biomarkers by gender)
- Knowledge gaps (donut chart: categories of questions with no good answer)

**Knowledge Gaps Table:**
```
┌──────────────────────────────────────┬────────┬──────────┐
│ Question / Topic                     │ Count  │ Action   │
├──────────────────────────────────────┼────────┼──────────┤
│ "Can I take ibuprofen during stims?" │ 14     │ [Review] │
│ "Acupuncture timing for transfer"    │ 9      │ [Review] │
│ "Melatonin dosage for egg quality"   │ 7      │ [Review] │
└──────────────────────────────────────┴────────┴──────────┘
```
"Review" → Mark as: Reviewed | Addressed (added to knowledge base) | Dismissed

## Q4. Tab 2: Analytics

**Sub-tabs:** Gaps | Gap Details | Citations | Devices | Categories | Sentiment | Actions

### Gaps Sub-tab
- Date range picker (7d / 30d presets)
- Gap types: chat (question with no good RAG match), bloodwork (missing biomarker), retrieval_empty (zero results from vector search), low_confidence (RAG match below 0.6)
- Table with: query, type, timestamp, status, action

### Citations Sub-tab
- Top cited documents (which of the 236 PDFs are used most)
- Average citation count per response
- Citation relevance score distribution

### Sentiment Sub-tab
- Mood distribution over time (stacked area chart)
- Sentiment by treatment phase (heatmap)
- Disengagement events per week

## Q5. Tab 3: Feedback

- DPO feedback distribution: pie chart (helpful / not helpful / partial)
- Recent feedback entries with user query, AI response, and user's rating
- Detailed feedback with issues (wrong info, too long, too clinical, etc.)
- Text feedback log (free-text feedback from users)

## Q6. Tab 4: Training (DPO)

**Overview cards:**
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total        │ │ Helpful      │ │ Valid for    │ │ Avg Quality  │
│ Feedback     │ │              │ │ Training     │ │ Score        │
│    2,847     │ │   2,104      │ │    1,532     │ │    4.2/5     │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**Sub-tabs:**
- **Feedback:** Detailed entries with query → response → user issues → preferred response
- **Training Pairs:** Side-by-side "chosen" vs "rejected" responses (from nutritionist modifications + user feedback)
- **Exports:** Export JSONL with filters (date range, quality threshold, validation status). Download button + audit log.

## Q7. Tab 5: Health

**System Status Banner:**
```
┌──────────────────────────────────────────────────┐
│  🟢 System Healthy                               │
│  11/11 swarms operational · 1,247 queries/24h    │
│  Avg latency: 2.3s · Error rate: 0.2%           │
└──────────────────────────────────────────────────┘
```

**Swarm Grid (11 cards):**
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Swarm 0         │ │ Swarm 1         │ │ Swarm 3         │
│ Polyglot        │ │ Gatekeeper      │ │ ClinicalBrain   │
│                 │ │                 │ │                 │
│ 🟢 Healthy      │ │ 🟢 Healthy      │ │ 🟡 Degraded     │
│ 87 q/hr         │ │ 92 q/hr         │ │ 84 q/hr         │
│ Avg: 1.2s       │ │ Avg: 0.8s       │ │ Avg: 3.1s ⚠️    │
│ P95: 2.4s       │ │ P95: 1.5s       │ │ P95: 6.2s       │
│ Errors: 0%      │ │ Errors: 0.1%    │ │ Errors: 1.2%    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
... (repeat for all 11 swarms)
```

**Model Status:**
```
┌─────────────────────────────────────────────────┐
│  Groq Models                                    │
│  ● llama-3.3-70b-versatile    Available  ✓     │
│  ● llama-3.1-70b-versatile    Available  ✓     │ (fallback)
│  ● llama-3.1-8b-instant       Available  ✓     │
│                                                 │
│  OpenAI Models                                  │
│  ● text-embedding-3-small     Available  ✓     │
│                                                 │
│  Active Alerts                                  │
│  ⚠️ ClinicalBrain P95 latency above threshold  │
│     since 14:30 UTC (2 hours ago)               │
└─────────────────────────────────────────────────┘
```

## Q8. Tab 6: Prompts

Editable system prompts for each swarm:

```
┌─────────────────────────────────────────────────────────┐
│  Swarm: [Swarm 4 — ChatResponseCurator ▾]              │
│                                                         │
│  Version: 3 (last edited: Mar 20, 2026 by admin)       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ You are Izana, a fertility wellness companion.  │    │
│  │ You help women going through fertility          │    │
│  │ treatments with evidence-based information...   │    │
│  │                                                 │    │
│  │ CONTEXT ABOUT THIS USER:                        │    │
│  │ {context_summary}                               │    │
│  │                                                 │    │
│  │ RELEVANT CLINICAL SOURCES:                      │    │
│  │ {rag_sources}                                   │    │
│  │                                                 │    │
│  │ RULES:                                          │    │
│  │ 1. Be warm and empathetic...                    │    │
│  │ 2. Cite sources using [Source Name] format...   │    │
│  │ ... (full prompt, editable)                     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  [Discard changes]                     [Save v4]        │
│                                                         │
│  Version History:                                       │
│  v3 — Mar 20, 2026 — Added FIE insight injection       │
│  v2 — Mar 15, 2026 — Reduced max response length       │
│  v1 — Mar 10, 2026 — Initial prompt                    │
│                                                         │
│  [Seed default prompts]  ← Resets all swarms to default │
└─────────────────────────────────────────────────────────┘
```

## Q9. Tab 7: Content Manager

Upload and manage exercise videos + meditation audios:

```
┌─────────────────────────────────────────────────────────┐
│  Content Library                        [+ Upload new]  │
├─────────────────────────────────────────────────────────┤
│  [All] [Exercise ✓] [Meditation] [Active] [Inactive]    │
│                                                         │
│  ┌────────┬──────────────────┬──────┬────────┬───────┐  │
│  │ ID     │ Title            │ Type │ Phases │ Active│  │
│  ├────────┼──────────────────┼──────┼────────┼───────┤  │
│  │ EX-001 │ Foundation Yoga  │ Video│ ALL    │ ✓     │  │
│  │ EX-006 │ Early Stims Yoga │ Video│ STIMS  │ ✓     │  │
│  │ MD-003 │ Morning Calm     │ Audio│ ALL    │ ✓     │  │
│  │ MD-018 │ Negative Result  │ Audio│ OUTCOME│ ✓     │  │
│  └────────┴──────────────────┴──────┴────────┴───────┘  │
│                                                         │
│  Click any row to edit tags, phases, treatment types,   │
│  contraindications, translations, and plan eligibility. │
│                                                         │
│  Upload Modal:                                          │
│  ┌───────────────────────────────────────┐              │
│  │ [Drop file or click to upload]        │              │
│  │                                       │              │
│  │ Title: [_______________]              │              │
│  │ Type: [Exercise video ▾]              │              │
│  │ Duration: [auto-detected]             │              │
│  │ Intensity: [Gentle ▾]                 │              │
│  │ Phases: [☑ STIMS] [☑ BASELINE] ...    │              │
│  │ Treatment types: [☑ IVF] [☑ IUI] ... │              │
│  │ Contraindications: [☑ No inversions]  │              │
│  │ Plan eligible: [☑ Yes]                │              │
│  │                                       │              │
│  │ [Cancel]         [Upload to Stream]   │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Uploading → Cloudflare Stream → get stream_id → save   │
└─────────────────────────────────────────────────────────┘
```

## Q10. Tab 8: Plans Queue (Admin View)

Same as the nutritionist queue, but admin sees ALL plans (not just their own) with additional metrics:

```
┌─────────────────────────────────────────────────────────┐
│  Plans Queue (Admin Overview)                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Avg Turn-    │ │ Plans Today  │ │ Escalations  │    │
│  │ around       │ │              │ │              │    │
│  │   2.4 hrs    │ │    18 / 16 ✓ │ │     1 ⚠️     │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                         │
│  Full queue table (same as nutritionist queue but       │
│  with "Assigned to" column visible)                     │
│                                                         │
│  ┌──────┬────────┬──────────┬──────────┬──────────┐     │
│  │ User │ Status │ Priority │ Assigned │ Deadline │     │
│  │ ...  │ ...    │ ...      │ Sarah K  │ 2h       │     │
│  │ ...  │ ...    │ ...      │ —        │ 3h       │     │
│  │ ...  │ ...    │ ...      │ Priya M  │ Overdue! │     │
│  └──────┴────────┴──────────┴──────────┴──────────┘     │
│                                                         │
│  Turnaround heatmap (by hour of day × day of week)      │
│  Nutritionist workload distribution (bar chart)         │
└─────────────────────────────────────────────────────────┘
```

---

# SECTION R: DATA MODELS FOR ADMIN/NUTRITIONIST

## R1. admin_users Table

```sql
CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'NUTRITIONIST' CHECK (role IN ('NUTRITIONIST', 'ADMIN')),
  password_hash TEXT NOT NULL,  -- bcrypt hash
  is_active BOOLEAN DEFAULT true,
  last_login_at TIMESTAMPTZ,
  plans_reviewed_count INTEGER DEFAULT 0,
  avg_review_minutes DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed initial admin:
INSERT INTO admin_users (email, name, role, password_hash)
VALUES ('admin@izana.com', 'Admin', 'ADMIN', '$2b$12$...');  -- bcrypt hash of initial password
```

## R2. API Endpoints for Auth

```python
# Nutritionist auth
POST /api/v1/nutritionist/auth/login
  Body: { email, password }
  Returns: { token, user: { id, name, email, role } }
  Token: JWT with 8-hour expiry, signed with ADMIN_API_KEY

POST /api/v1/nutritionist/auth/change-password
  Headers: Authorization: Bearer {token}
  Body: { current_password, new_password }

# Admin dashboard auth (simpler — API key based)
# No login endpoint needed — frontend just stores the API key
# Every admin request includes: X-Admin-API-Key: {key}
```

## R3. Notification Flow for Plans

```
New plan created
    │
    ├── Push notification to ALL active nutritionists
    │   Title: "New plan for review"
    │   Body: "BraveOcean42 · IVF Stims · Dairy-free"
    │
    ├── Email to ALL active nutritionists (if configured)
    │   Subject: "New plan — BraveOcean42 (IVF Stims)"
    │   Body: Brief context + link to portal
    │
    └── If priority = 'urgent_phase_change':
        ├── Push with [URGENT] prefix
        └── Email with 🔴 URGENT in subject

Plan overdue (> 4 hours):
    │
    └── Email to ALL nutritionists + admin
        Subject: "⚠️ OVERDUE: Plan for BraveOcean42"
        Body: "This plan has been waiting 4+ hours. Any nutritionist can review."
```

---

# SECTION S: COMPLETE FROM-SCRATCH SETUP & BUILD PHASES

## S1. Starting Point

You are building everything from scratch. Here's what you have:

| Resource | Status | What it is |
|----------|--------|------------|
| 236 clinical PDFs | ✅ On your computer | Fertility research papers, clinical guidelines, treatment protocols |
| Groq API keys | ✅ You have these | Multiple keys for LLM inference (llama models) |
| OpenAI API key | ✅ You have this | For generating text embeddings (text-embedding-3-small) |
| Domain (chat.izana.ai) | ✅ DNS configured | Will point to Netlify when deployed |
| Exercise videos (29 files) | ✅ Produced locally | MP4/MOV files, need uploading to Cloudflare Stream |
| Meditation audios (34 files) | ✅ Produced locally | MP3/M4A files, need uploading to Cloudflare Stream |
| Supabase project | ❌ Need to create | Database, auth, vector search |
| Cloudflare Stream | ❌ Need to create | Video/audio hosting + streaming |
| Netlify account | ❌ Need to create | Frontend hosting |
| Render account | ❌ Need to create | Backend hosting |

Everything else (code, database tables, AI pipeline, frontend, admin portal) is built by Claude Code following this guide.

## S2. What YOU Do Before Opening Claude Code

These are manual steps you do in your browser and terminal. Takes ~20 minutes.

### Step 1: Create Supabase Project (5 minutes)

```
1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Settings:
   - Organization: your org
   - Project name: izana-v2
   - Database password: click "Generate a password" → SAVE THIS
   - Region: Southeast Asia (Singapore)
   - Security: ☑ Enable Data API, ☑ Enable automatic RLS
   - Postgres Type: Postgres (DEFAULT)
4. Click "Create new project"
5. Wait ~2 minutes for provisioning

6. Once ready, go to Settings → API and copy these 3 values:
   ┌────────────────────────────────────────────────────┐
   │ Project URL:      https://xxxxx.supabase.co        │
   │ anon public key:  eyJhbGciOi...                    │
   │ service_role key: eyJhbGciOi... (click "Reveal")   │
   └────────────────────────────────────────────────────┘
   Save all 3 somewhere safe.

7. Also go to Settings → Database and copy:
   ┌────────────────────────────────────────────────────┐
   │ Connection string (URI tab):                       │
   │ postgresql://postgres.xxxxx:PASSWORD@aws-0-...     │
   └────────────────────────────────────────────────────┘
   Replace [YOUR-PASSWORD] with your actual database password.
   Save this too — you may need it for direct DB access.
```

### Step 2: Enable pgvector (1 minute)

```
1. In your new project, click "SQL Editor" in the left sidebar
2. Paste and run:

   CREATE EXTENSION IF NOT EXISTS vector;

3. Should see "Success. No rows returned."
```

### Step 3: Generate Admin API Key (1 minute)

Open Terminal (Cmd+Space → type "Terminal" → Enter) and run:

```bash
openssl rand -hex 32
```

This outputs a 64-character string like `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1`. Copy and save it — this is your `ADMIN_API_KEY`.

### Step 4: Prepare Your Environment Variables (5 minutes)

Create a file on your desktop called `izana_env.txt` and fill in this template:

```bash
# ═══════════════════════════════════════════════════
# IZANA ENVIRONMENT VARIABLES
# Fill in every value after the = sign
# ═══════════════════════════════════════════════════

# ── Supabase (from Step 1) ──
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard   # (Decision 1) Settings → API → JWT Secret
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...your-anon-key

# ── Groq (you have these) ──
GROQ_API_KEY=gsk_...your-primary-key
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
GROQ_MAX_CONCURRENT_REQUESTS=10

# ── OpenAI (you have this) ──
OPENAI_API_KEY=sk-...your-openai-key

# ── Admin (from Step 3) ──
ADMIN_API_KEY=your-64-char-string-from-step-3
NUTRITIONIST_JWT_SECRET=your-separate-64-char-string   # Different from ADMIN_API_KEY

# ── Redis (Decision 2 — REQUIRED for task queue) ──
REDIS_URL=redis://localhost:6379   # Use Upstash Redis URL in production

# ── App Config (use these exact values for dev) ──
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_ADMIN_EMAIL=admin@izana.com
ENVIRONMENT=development
DEBUG=true

# ── Feature Flags (Decision 11) ──
FEATURE_BLOODWORK_ENABLED=true
FEATURE_PARTNER_ENABLED=true
FEATURE_FIE_ENABLED=false
FEATURE_PUSH_ENABLED=true

# ── Leave these empty for now (set up later) ──
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_STREAM_TOKEN=
SENDGRID_API_KEY=
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
FIE_ANONYMIZATION_SALT=
```

### Step 5: Organise Your PDFs (2 minutes)

Put all 236 clinical PDF files in a single folder on your computer. Note the path, e.g.:
```
/Users/yourname/Documents/izana-knowledge-base/
```

You'll tell Claude Code this path during Phase 2.

### Step 6: You're ready. Open Claude Code.

---

## S3. BUILD PHASES (What To Tell Claude Code)

The build is divided into **6 phases**. Each phase is 1-3 Claude Code sessions. You start each session by giving Claude Code the build guide + telling it which phase you're on.

```
╔═══════════════════════════════════════════════════════════════╗
║                    THE 6 BUILD PHASES                        ║
║                                                              ║
║  PHASE 1: Foundation         (Sessions 1-2, ~5 hours)        ║
║    Repo setup, database, backend core, .env files            ║
║                                                              ║
║  PHASE 2: AI Brain           (Sessions 3-4, ~6 hours)        ║
║    11 swarms, RAG engine, PDF ingestion, chat API            ║
║                                                              ║
║  PHASE 3: User-Facing App    (Sessions 5-7, ~8 hours)        ║
║    Landing page, signup, onboarding, chat UI, cards          ║
║                                                              ║
║  PHASE 4: Plans & Content    (Sessions 8-9, ~5 hours)        ║
║    Plan generation, nutritionist portal, content CMS         ║
║                                                              ║
║  PHASE 5: Supporting Systems (Sessions 10-11, ~5 hours)      ║
║    Admin dashboard, partner, provider portal, FIE            ║
║                                                              ║
║  PHASE 6: Polish & Deploy    (Sessions 12-13, ~4 hours)      ║
║    Offline, Capacitor, testing, deployment                   ║
║                                                              ║
║  TOTAL: ~13 sessions, ~33 hours of Claude Code work          ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## S4. PHASE 1: FOUNDATION

**What gets built:** Repository, database (40+ tables), backend core (config, auth, database client, models, exceptions)

**Sessions needed:** 1-2

### Session 1 Start Message (copy-paste this to Claude Code):

```
I'm building Izana Chat completely from scratch. 

Here is the complete build guide — it contains EVERYTHING about 
the product, UI, backend, and how to build it:
[attach IZANA_COMPLETE_BUILD_GUIDE_FINAL.md]

IMPORTANT: Read Section A5 "Architectural Decisions" FIRST.
It contains 11 critical decisions from the pre-build review.

Here are my environment variables:
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...           # (Decision 1) From Supabase Dashboard → Settings → API → JWT Secret
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
GROQ_API_KEY=...
GROQ_API_KEYS=...
OPENAI_API_KEY=...
ADMIN_API_KEY=...
NUTRITIONIST_JWT_SECRET=...       # Separate from ADMIN_API_KEY
REDIS_URL=redis://localhost:6379  # (Decision 2) Or Upstash Redis URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_ADMIN_EMAIL=admin@izana.com
ENVIRONMENT=development
DEBUG=true
GROQ_MAX_CONCURRENT_REQUESTS=10
FEATURE_BLOODWORK_ENABLED=true    # (Decision 11)
FEATURE_PARTNER_ENABLED=true
FEATURE_FIE_ENABLED=false
FEATURE_PUSH_ENABLED=true

I already have a new Supabase project with pgvector enabled.
I have Redis running locally (or an Upstash Redis instance).
There are NO existing tables — everything needs to be created.

The documents table for the RAG knowledge base also needs to
be created — I have 236 PDF files that will be ingested in
Phase 2.

Please start PHASE 1: FOUNDATION
- Build Guide Section F: Stage 1 (Repository Setup — include Redis + arq + PyJWT deps)
- Build Guide Section F: Stage 2 (Database Schema — all 10 migration files including chat_traces)
- Build Guide Section F: Stage 3 (Backend Core — JWT auth, task queue, feature flags)

Create the .env files using my variables above.
Run each migration against my Supabase project.
After each stage, run the VERIFY step AND the specified tests.
```

### What Claude Code builds in Phase 1:

```
Stage 1: Repository Setup
├── Creates monorepo: frontend/ (Next.js 15) + backend/ (FastAPI)
├── Installs all dependencies (including arq, PyJWT, bcrypt — Decisions 1, 2)
├── Creates complete directory structure (from Section F, including workers/)
├── Creates .env files with your actual keys (including SUPABASE_JWT_SECRET, REDIS_URL)
├── Sets up test infrastructure: conftest.py, mock clients (Decision 8)
└── VERIFY: Both servers start, Redis connects, pytest discovers tests

Stage 2: Database Schema
├── Creates 10 SQL migration files (9 original + 010_chat_traces):
│   001_core_tables.sql          → profiles table + RLS
│   002_cycles_chapters.sql      → cycles, chapters, phase_durations
│   003_chat_logs.sql            → chat_logs, summaries, archives
│   004_companion.sql            → symptoms, emotions, partner_links
│   005_nutrition_plans.sql      → plans, approval_queue, meal_logs
│   006_content_gamification.sql → wellness_content, badges, streaks
│   007_feedback_training.sql    → dpo_logs, training_data
│   008_system_tables.sql        → documents table (EMPTY — ingested in Phase 2),
│   │                              admin_prompts, knowledge_gaps, push_subs
│   009_fie_schema.sql           → fie.* schema
│   010_chat_traces.sql          → chat_traces table (Decision 10 — observability)
├── Runs each migration against your Supabase
├── Seeds phase_durations, badges, default prompts
└── VERIFY: "SELECT table_name FROM information_schema.tables" shows 40+ tables
    + pytest tests/test_migrations.py passes (Decision 8)

Stage 3: Backend Core
├── app/core/config.py           → Settings class with ALL env vars (JWT secret, Redis, feature flags)
├── app/core/database.py         → Supabase client singleton
├── app/core/auth.py             → JWT verification (Decision 1) + Admin key extraction
├── app/core/exceptions.py       → 23+ custom exceptions + EmptyResponseError, RefusalError (Decision 5)
├── app/core/model_config.py     → LLM model registry + fallback chains
├── app/core/validators.py       → Input sanitization, PII detection
├── app/core/biomarker_config.py → Reference ranges for 19+ biomarkers
├── app/core/logging_config.py   → Structured JSON logging
├── app/core/metrics.py          → Prometheus metrics
├── app/core/task_queue.py       → arq Redis connection pool + enqueue helper (Decision 2)
├── app/core/feature_flags.py    → require_feature() helper (Decision 11)
├── app/api/auth_routes.py       → POST /auth/signup (Decision 7), GET /auth/lookup (Decision 6)
├── app/main.py                  → FastAPI app with all middleware + auth_routes router
└── VERIFY: Backend starts, health endpoint returns 200, Redis connects
    + pytest tests/test_auth.py passes (Decision 8)
```

### Phase 1 Completion Check:
```
✅ frontend/ starts on localhost:3000 (shows Next.js default page)
✅ backend/ starts on localhost:8000 (shows FastAPI docs at /docs)
✅ 40+ tables exist in Supabase (including chat_traces — Decision 10)
✅ .env files have all keys (including SUPABASE_JWT_SECRET, REDIS_URL)
✅ Backend can connect to Supabase (test via health endpoint)
✅ Backend can connect to Redis (Decision 2)
✅ JWT auth accepts valid Supabase tokens (Decision 1)
✅ JWT auth rejects expired/forged tokens (Decision 1)
✅ POST /auth/signup creates user + profile + gamification in one call (Decision 7)
✅ GET /auth/lookup returns same response for existing and nonexistent pseudonyms (Decision 6)
✅ Feature flag helper blocks disabled features with "Coming soon" (Decision 11)
✅ All Stage 3 tests pass: pytest tests/test_auth.py -v
```

---

## S5. PHASE 2: AI BRAIN

**What gets built:** All 11 AI swarms, RAG engine with PDF ingestion, chat API with SSE streaming, bloodwork pipeline

**Sessions needed:** 2

### Session Start Message:

```
Continuing Izana build. Phase 1 is complete — repo, database 
(40+ tables), and backend core are all working.

The build guide is already loaded from last session.

Please start PHASE 2: AI BRAIN
- Build all 11 swarms (Section A3 for overview, Section M6 for config)
- Build RAG engine (Section M8) with document ingestion script
- Build chat API with SSE streaming (Section M4-M5)
- Build bloodwork pipeline
- Build the preview chat endpoint with caching (Section K)

My 236 clinical PDFs are located at: /Users/[myname]/Documents/izana-knowledge-base/

IMPORTANT for PDF ingestion:
- Chunk each PDF into ~500 token chunks with 50 token overlap
- Generate embeddings using OpenAI text-embedding-3-small (384 dimensions)
- Store in the documents table (already created in Phase 1)
- Include metadata: { filename, page_number, chunk_index, title }
- This will take time — process in batches of 50 chunks
- Expected result: ~29,000-30,000 chunks in the documents table

After building the swarms and ingesting the PDFs, verify the 
full chat pipeline works end-to-end:
1. Send a test message: "What should I eat during IVF stims?"
2. Should get a sourced response from the clinical docs
3. Test SSE streaming works

Build the 3 pre-cached landing page responses (Section K) after 
the pipeline is verified.
```

### What Claude Code builds in Phase 2:

```
Stage 4: Swarm Pipeline
├── app/services/groq_client.py          → Multi-key rotation + circuit breaker
├── app/services/swarm_base.py           → Abstract base class
├── app/services/swarm_0_polyglot.py     → Translation
├── app/services/swarm_1_gatekeeper.py   → Safety + topic classification
├── app/services/swarm_2_extractor.py    → Bloodwork OCR
├── app/services/swarm_3_clinical.py     → RAG engine (ClinicalBrain)
├── app/services/swarm_4_curator.py      → Response generation
├── app/services/swarm_5_analyser.py     → Biomarker interpretation
├── app/services/swarm_6_bloodwork_curator.py → Patient-friendly formatting
├── app/services/swarm_7_compliance.py   → Medical disclaimers
├── app/services/swarm_8_gap.py          → Knowledge gap detection
├── app/services/swarm_9_context.py      → Conversation context
├── app/services/swarm_10_sentiment.py   → Sentiment analysis
└── VERIFY: Each swarm can be instantiated, returns responses

Stage 5: RAG Engine + PDF Ingestion
├── app/services/swarm_3_clinical.py     → Vector search with multi-query
├── scripts/ingest_docs.py               → PDF chunking + embedding script
│   Process:
│   1. Read each PDF (pypdf)
│   2. Split into ~500 token chunks with 50 token overlap
│   3. Generate embeddings via OpenAI (text-embedding-3-small, 384 dims)
│   4. Batch upsert into documents table (50 chunks per batch)
│   5. Log progress: "Processing file 47/236: eshre_guidelines.pdf"
│   
│   Expected output:
│   - ~29,000-30,000 chunks in documents table
│   - Each chunk has: content, embedding (384-dim vector), metadata (filename, page, etc.)
│   - Takes ~30-60 minutes depending on PDF sizes
│   - Costs ~$3-5 in OpenAI embedding credits
│
├── match_documents function            → Already created in Phase 1 migrations
└── VERIFY: Query "IVF stims nutrition" returns relevant document chunks

Stage 6: Chat API
├── app/api/chat.py                     → SSE streaming + REST fallback
├── app/api/preview.py                  → Landing page preview (rate limited)
│   Pipeline: sanitize → PII check → greeting → translate → gate → 
│             context → RAG → generate → compliance → translate back
├── Pre-cached landing responses        → 3 questions × 11 languages
└── VERIFY: Send message, get sourced response with streaming

Stage 7: Bloodwork Pipeline
├── app/api/bloodwork.py                → Upload endpoint
├── app/services/vision_client.py       → OCR (Groq Vision → OpenAI fallback)
├── app/services/pdf_handler.py         → PDF text extraction
├── Upload → Extract → Confirm → Analyse flow
└── VERIFY: Upload test PDF, extract biomarkers, get analysis
```

### Phase 2 Completion Check:
```
✅ All 11 swarms instantiate and return responses
✅ ~29,000+ document chunks in the documents table
✅ Chat pipeline works end-to-end (question → sourced answer)
✅ SSE streaming works (tokens arrive progressively)
✅ Preview endpoint works (rate limited, cached responses)
✅ Bloodwork upload → extraction → analysis works
```

---

## S6. PHASE 3: USER-FACING APP

**What gets built:** Complete frontend — landing page, signup, onboarding, chat interface with chapters and cards, luxury design system

**Sessions needed:** 2-3

### Session Start Message:

```
Continuing Izana build. Phase 2 is complete — all 11 swarms 
work, RAG has ~29,000 document chunks, chat pipeline streams 
responses with sources.

Please start PHASE 3: USER-FACING APP
- Build the complete design system (Section B)
- Build landing page with chat (Section C1)
- Build signup bottom-sheet modal (Section C2)
- Build recovery phrase screen (Section C3)
- Build 3-round conversational onboarding (Section C4)
- Build grand reveal (Section C5)
- Build the main chat interface with:
  - Phase header ("Your stims · day 8")
  - Smart collapsing (Section H4)
  - Daily morning flow with 1-tap mood (Section C8)
  - Plan card with tabs (Section C7)
  - Evening summary (Section C8)
  - Phase transition prompts (Section C9)
  - Perplexity-style search animation (Section K3)
- Build Journey tab (Section C10)
- Build You tab (Section C11)
- Build 3-tab bottom nav: Today | Journey | You (Section B5)
- Apply ALL luxury UI details (Section L)
- Apply ALL microcopy (Section D)
- Apply ALL animations (Section B4)

This is the most important phase — the UI must feel uber luxe.
Follow Section L precisely: breathing dot, warm shimmer, 
asymmetric bubbles, haptic button press, word-by-word text 
reveal, source citation pills.

Every screen in Section C has an ASCII wireframe — follow 
those layouts exactly.
```

### What Claude Code builds in Phase 3:

```
Stage 10: Frontend Shell + Design System
├── src/styles/globals.css              → All CSS custom properties (Section B2)
├── src/app/layout.tsx                  → Root layout, fonts, theme provider
├── src/lib/theme.ts                    → Theme switching logic
├── src/stores/theme-store.ts           → Zustand theme store
├── src/components/ui/*                 → All base UI primitives
├── src/components/navigation/BottomNav.tsx → 3-tab text navigation
├── Fonts: Inter + DM Serif Display + JetBrains Mono
├── Tailwind config with custom design tokens
└── VERIFY: App loads with correct colors, fonts in light + dark mode

Stage 11: Landing Page
├── src/app/page.tsx                    → Chat-as-landing-page (Section C1)
├── src/components/landing/PreviewChat.tsx → With cached responses
├── Perplexity-style search animation   → 4-stage animation (Section K3)
├── Pre-loaded suggested questions      → Cache-first, instant feel
├── CTA + chat input both in first 100vh
└── VERIFY: Landing loads, tap question → animation → cached response in ~2.5s

Stage 12: Identity + Onboarding
├── src/components/identity/SignupModal.tsx  → Bottom-sheet (Section C2)
│   Avatar + name on one row, sex + password side by side
├── src/components/identity/LoginModal.tsx   → Returning users (Section O1)
├── src/components/identity/RecoveryPhrase.tsx → One-time display (Section C3)
├── src/components/onboarding/OnboardingRounds.tsx → 3 grouped rounds (Section C4)
│   Round 1: Treatment & You (treatment, phase, day, age)
│   Round 2: Lifestyle (health, activity, smoking, alcohol, sleep, stress)
│   Round 3: Food & Exercise (allergies, diet, cuisine, exercise pref, time)
├── Grand reveal message (Section C5)
└── VERIFY: Complete signup → 3 rounds → grand reveal → land in active chat

Stage 13: Chat Interface
├── src/app/chat/page.tsx               → Main chat page
├── src/components/chat/ChatInterface.tsx → Core chat component
├── src/components/chat/ChapterHeader.tsx → "Your stims · day 8" + streak
├── src/components/chat/SmartCollapse.tsx → Auto-collapsing past sections
├── src/components/chat/DaySeparator.tsx  → "today · day 8"
├── src/components/chat/MoodSelector.tsx  → 4 emoji, part of Izana's message
├── src/components/chat/SearchAnimation.tsx → Perplexity-style 4-stage
├── src/components/chat/StreamingText.tsx  → Word-by-word reveal
├── src/components/chat/SourcePills.tsx    → Floating citation pills
├── src/components/chat/SuggestedQuestions.tsx → Follow-up chips
├── src/hooks/useStreamingChat.ts         → SSE + REST fallback
├── src/hooks/useChapter.ts               → Active chapter state
├── src/stores/chat-store.ts              → Zustand chat state
└── VERIFY: Chat works with streaming, sources appear, mood selection works

Stage 14: Card System
├── src/components/chat/cards/ChatCard.tsx → Polymorphic card renderer
├── src/components/chat/cards/PlanCard.tsx → Tabbed: Nutrition|Exercise|Meditation
│   - Items with "Done" button, staggered entrance
│   - Next action prominent, rest dimmed
│   - Progress line at bottom
├── src/components/chat/cards/EveningSummaryCard.tsx → Day recap + points
├── src/components/chat/cards/TransitionCard.tsx → Phase change prompt
├── src/components/chat/cards/CelebrationCard.tsx → Confetti trigger
├── src/components/chat/cards/PlanStatusCard.tsx → Polling during review
├── src/components/chat/cards/BloodworkCard.tsx → Analysis results
├── src/components/chat/cards/ContentCard.tsx → Play video/audio
├── All cards use Framer Motion entrance animation
└── VERIFY: Each card type renders correctly in light + dark mode

Stage 15 (partial): Journey + You Tabs
├── src/app/journey/page.tsx            → Timeline + quick actions
├── src/components/navigation/JourneyTimeline.tsx → Vertical timeline
├── src/app/profile/page.tsx            → You tab
├── src/components/chat/MediaPlayer.tsx  → hls.js video/audio player
└── VERIFY: Journey tab shows timeline, You tab shows profile
```

### Phase 3 Completion Check:
```
✅ Landing page shows chat with Izana's intro in first 100vh
✅ Tapping suggested question → animation → response in ~2.5 seconds
✅ Signup modal slides up, creates account, shows recovery phrase
✅ 3-round onboarding works end-to-end (~3 minutes)
✅ Grand reveal appears with confetti and action buttons
✅ Chat interface streams responses with sources
✅ Morning mood check = 1 tap on emoji
✅ Plan card shows with tabs, "Done" buttons, progress line
✅ Smart collapsing works (completed sections → one-line summary)
✅ Journey tab shows timeline, You tab shows profile
✅ Everything works in light + dark mode
✅ Everything works at 375px width
✅ Animations respect prefers-reduced-motion
```

---

## S7. PHASE 4: PLANS & CONTENT

**What gets built:** Plan generation pipeline, nutritionist portal with full review workflow, Cloudflare Stream integration, content CMS

**Sessions needed:** 2

**⚠️ BEFORE THIS PHASE:** Create a Cloudflare Stream account:
```
1. Go to https://dash.cloudflare.com
2. Sign up or log in
3. Click "Stream" in left sidebar
4. Note your Account ID (visible in the URL or sidebar)
5. Go to "Manage" → "API Tokens" → Create Token
   - Permissions: Stream:Edit
   - Copy the token
6. Add to your env vars:
   CLOUDFLARE_ACCOUNT_ID=your-account-id
   CLOUDFLARE_STREAM_TOKEN=your-token
```

### Session Start Message:

```
Continuing Izana build. Phase 3 is complete — full user-facing 
app works (landing, signup, onboarding, chat with streaming, 
cards, journey tab, you tab).

My Cloudflare Stream credentials:
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_STREAM_TOKEN=...

Please start PHASE 4: PLANS & CONTENT
- Build plan generation pipeline (Section J3 — all 8 steps)
- Build nutritionist portal (Section P — complete):
  - Login page with JWT auth
  - Sidebar layout
  - Queue page with stats, filters, table
  - 3-panel plan review page
  - Modification capture modal
  - Reject modal
  - Analytics page
  - Admin user management (if admin role)
- Build Cloudflare Stream integration
- Build content CMS (admin tab 7 — Section Q9)
- Build media player (hls.js)
- Wire plan delivery to chat (celebration + plan card)
- Build plan status polling card

Create an initial admin user:
  Email: admin@izana.com
  Password: [tell Claude Code your preferred password]
  Role: ADMIN
```

### Phase 4 Completion Check:
```
✅ Plan generation runs when user completes onboarding
✅ Plan appears in nutritionist queue
✅ Nutritionist can log in at /nutritionist/login
✅ Nutritionist can view queue, assign, review plans
✅ 3-panel review editor works (edit, approve, modify, reject)
✅ Modification capture modal records changes for DPO
✅ Approved plan triggers push notification + celebration in chat
✅ Plan card shows in chat with tabs and "Done" buttons
✅ Plan status card polls and updates during review
✅ Content CMS can upload to Cloudflare Stream
✅ Media player plays videos and audios inline
```

---

## S8. PHASE 5: SUPPORTING SYSTEMS

**What gets built:** Admin dashboard (8 tabs), partner system, provider portal, FIE pipeline, background jobs

**Sessions needed:** 2

### Session Start Message:

```
Continuing Izana build. Phase 4 is complete — plan generation 
works, nutritionist portal works, content CMS + Cloudflare 
Stream working.

Please start PHASE 5: SUPPORTING SYSTEMS
- Build admin dashboard with all 8 tabs (Section Q):
  Tab 1: Dashboard (KPIs, charts)
  Tab 2: Analytics (gaps, citations, sentiment)
  Tab 3: Feedback (DPO distribution)
  Tab 4: Training (DPO export)
  Tab 5: Health (swarm monitoring)
  Tab 6: Prompts (editable swarm prompts)
  Tab 7: Content Manager (already built in Phase 4, wire it here)
  Tab 8: Plans Queue (admin view of nutritionist queue)
- Build partner system (Section C12):
  - Partner invite flow (code generation, share)
  - Partner onboarding (abbreviated)
  - Partner view ("Supporting stims · day 10")
  - Encouragement messages
- Build provider portal (Section C10 "Doctor" button):
  - Share modal (configure what to include)
  - PDF report generation (reportlab)
  - Token-based access for doctors
  - PHI audit logging
- Build FIE pipeline (Section G):
  - Feature extractor
  - Training data generator
  - Insight engine
  - All in fie.* schema, READ-ONLY on production data
- Build background jobs:
  - Phase transition checks
  - Disengagement sensing
  - Nudge scheduling
  - Evening summary generation
  - FIE daily extraction
```

### Phase 5 Completion Check:
```
✅ Admin dashboard loads at /admin with all 8 tabs populated
✅ Health tab shows all 11 swarms with real metrics
✅ Prompts tab can edit and save swarm prompts
✅ Partner invite generates code, partner can join
✅ Partner sees "Supporting stims" view with coaching
✅ Provider share generates PDF report
✅ Doctor can access report via token link
✅ FIE extracts features (test with mock completed cycle)
✅ Background jobs run on schedule
```

---

## S9. PHASE 6: POLISH & DEPLOY

**What gets built:** Offline support, PWA, Capacitor (iOS/Android), testing, production deployment

**Sessions needed:** 1-2

**⚠️ BEFORE THIS PHASE:**
```
1. Create Netlify account: https://netlify.com
2. Create Render account: https://render.com
3. Generate VAPID keys (for push notifications):
   npx web-push generate-vapid-keys
   Save both Public Key and Private Key
```

### Session Start Message:

```
Continuing Izana build. Phase 5 is complete — admin dashboard, 
partner system, provider portal, FIE all working.

My deployment credentials:
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...

Please start PHASE 6: POLISH & DEPLOY
- Build offline support:
  - Service worker (sw.js)
  - IndexedDB offline store (today's plan, check-in, last 2 days)
  - Offline queue for actions
  - Sync on reconnect
  - Amber "offline" banner
- Build PWA manifest
- Add Capacitor 8 for iOS/Android:
  - Configure for static export
  - Add native push notifications
  - Add safe area handling
  - Build iOS + Android projects
- Write E2E tests (Playwright) for critical flows:
  - Landing → signup → onboarding → chat
  - Chat message → sourced response
  - Bloodwork upload → analysis
  - Plan approval → delivery to user
- Deploy:
  - Frontend to Netlify (custom domain: chat.izana.ai)
  - Backend to Render (Singapore region)
  - Configure all production env vars
- Final verification: full flow works in production
```

### Phase 6 Completion Check:
```
✅ App works offline (check-in, meal logging)
✅ Syncs when connection returns
✅ PWA installable from browser
✅ Capacitor builds for iOS and Android
✅ Push notifications work
✅ All E2E tests pass
✅ Frontend live at chat.izana.ai
✅ Backend live on Render
✅ Full flow works: landing → signup → onboarding → chat → 
   plan delivery → daily rhythm → phase transition
```

---

## S10. Session Recovery (When Claude Code Disconnects)

Claude Code sessions can time out. Here's your recovery message:

```
I'm building Izana Chat from scratch. 

[attach IZANA_COMPLETE_BUILD_GUIDE_FINAL.md]

Previous sessions completed through PHASE [X]. 
All verification checks passed.

The codebase is in [your repo location, e.g., ~/projects/izana].

My env vars:
[paste your izana_env.txt]

Please continue with PHASE [X+1].
```

## S11. Cost Summary

| Phase | External Costs |
|-------|---------------|
| Phase 1: Foundation | $0 (Supabase free tier) |
| Phase 2: AI Brain | ~$3-5 (OpenAI embeddings for PDF ingestion) |
| Phase 3: User App | $0 |
| Phase 4: Plans & Content | ~$5 (Cloudflare Stream base fee) |
| Phase 5: Supporting | $0 |
| Phase 6: Deploy | ~$7/month (Render) + ~$0-19/month (Netlify) |
| **Total to launch** | **~$15-35** |

Monthly running costs at 1,000 users: ~$150-230/month (Supabase $25-75, Groq ~$20-50, OpenAI ~$5-10, Render $25, Cloudflare Stream ~$50, Netlify ~$19).


# SECTION T: DETAILED UI/UX SPECIFICATIONS
# Every feature, flow, and function — specified, not coded

---

## T1. GLOBAL RULES (Apply Everywhere)

### Every Screen Must:
- Work at 375px width (iPhone SE) and scale up to 1440px (desktop)
- Support light mode and dark mode using CSS variables (Section B2), never hardcoded colors
- Respect prefers-reduced-motion (disable all motion except opacity fades)
- Show a warm shimmer skeleton (not grey pulse, not spinner) when loading data
- Show human-friendly error messages (Section D4) on failure
- Show inviting empty states (Section D2) when no data exists
- Auto-save any user input on every keystroke/selection (no explicit save buttons except password)
- Never require more than 3 taps to complete any action

### Every Interactive Element Must Have 5 States:
1. **Default** — normal resting appearance
2. **Hover/Focus** — subtle highlight (desktop hover, mobile focus ring)
3. **Active/Pressed** — slight scale-down (97% scale) for tactile feel
4. **Loading** — inline spinner or shimmer replacing content, element disabled
5. **Disabled** — 50% opacity, no pointer events

### Data Fetching Rules:
- Every GET request uses SWR (stale-while-revalidate) with appropriate cache times
- Every POST/PUT/DELETE is optimistic where possible (show success immediately, rollback on error)
- Every API call has a 30-second timeout (60 seconds for file uploads)
- Every API failure shows a toast (not an alert, not a modal)
- Every API that returns user data includes the user's timezone for time-based logic

### Scroll Behavior:
- New messages auto-scroll to bottom (unless user has scrolled up manually)
- If user is scrolled up, show a floating "↓ New message" pill at the bottom
- All lists use virtual scrolling if they exceed 50 items
- Pull-to-refresh on mobile for all data-fetching screens

---

## T2. BOTTOM NAVIGATION

### What It Is
A fixed bar at the very bottom of every screen with 3 text labels: "Today", "Journey", "You". No icons.

### When It Appears
- Always visible on every screen after authentication
- Visible but greyed out and non-functional on the landing page (pre-auth)
- Hidden on: nutritionist portal, admin dashboard, provider portal public view

### How It Behaves
- The active tab has a soft pill background in the brand's light purple, with purple text and medium font weight
- Inactive tabs are small muted text in the tertiary color
- Tapping a tab navigates to its route instantly. The tab indicator updates immediately (no delay)
- The page content crossfades when switching tabs: the outgoing content fades and slides slightly in the direction of the tab (e.g., switching from Today→Journey, content slides left and fades; Journey→Today, content slides right and fades). Duration: 250ms.
- The nav bar itself never animates — only the content above it changes
- Height: 52px plus the device safe area bottom inset (for phones with home indicators)
- Background: elevated surface color. Top border: 0.5px default border color

### Tab Routes
- "Today" → the main chat/phase screen (default on login)
- "Journey" → timeline, bloodwork, trends, doctor sharing
- "You" → profile, partner, content library, achievements, settings

---

## T3. LANDING PAGE

### Purpose
Convert a stranger into a user. Show value before asking for anything.

### What the User Sees (First 100vh — No Scrolling Required)

The entire landing page fits in one phone screen without scrolling:

**Top bar:** The Izana logo (✦ symbol + "izana" text) on the left. A language selector dropdown on the right showing current language code (e.g., "EN"). Tapping it opens a dropdown with all 11 supported languages.

**Izana's introduction message:** Displayed as a chat bubble from Izana (with her ✦ avatar). The headline uses the serif display font: "Your fertility journey is unique. Your support should be too." Below it, body text in the regular font explains what Izana does: personalised plans, reviewed by a real nutritionist, adapts to every phase. Ends with "Try me — ask anything ↓"

**Three suggested questions:** Displayed as tappable pill-shaped chips below Izana's message. The 3 default questions:
1. "What to eat during IVF?"
2. "Is my AMH normal?"
3. "Help with TWW anxiety"

**Trust badges:** Three small pills in a row: "Anonymous" · "Nutritionist reviewed" · "11 languages"

**Bottom section (fixed):** Contains three elements stacked:
1. Primary CTA button: "Start my journey — free & anonymous" (full width, brand primary color)
2. Chat input bar: placeholder "Ask about your fertility journey..." with send button
3. Text link: "Already have an account? Log in"

### Pre-Cached Response System

The 3 suggested questions have pre-computed responses stored on the backend (refreshed daily). When the landing page loads, the frontend fetches these cached responses in the background.

**When user taps a suggested question:**
1. The question appears as a user message bubble (right-aligned, purple)
2. The Perplexity-style search animation begins immediately (details in T4)
3. Because the response is already cached, the animation is timed (not waiting for real API):
   - "Understanding your question..." appears, gets ✓ after 0.5 seconds
   - "Searching clinical literature..." appears, gets ✓ after 1.0 seconds
   - "Found N relevant sources..." appears with sources sliding in one by one (0.5 seconds)
   - "Crafting your answer..." appears briefly (0.5 seconds)
   - Total animation: ~2.5 seconds
4. The response text streams in word by word from the cache (simulating real-time generation)
5. Sources appear as small citation pills below the response
6. The CTA button text changes to: "Want advice personalised to YOUR treatment? Start my journey"

**When user types their OWN question:**
1. The question appears as a user message
2. The real API is called (POST /preview/ask) — rate limited to 1 per 10 minutes per IP
3. The search animation plays with REAL timing (driven by actual SSE events from the backend)
4. Takes 5-10 seconds (normal for the swarm pipeline)
5. If rate limited: toast message "I need a moment to catch up. Try again in a few minutes."

**When cache is not available** (still loading or error):
- Suggested question taps fall back to the real API (same as custom questions)
- No visual difference to the user — just slightly slower

### After Preview Response
After the user sees any response (cached or real):
- The CTA button text changes to the personalised version
- A second prompt appears below the response: "Ask another question →" (tappable, sends back to input)
- The user can continue asking questions (but custom ones are rate-limited)

### Language Selector Behavior
- Tapping the language code opens a dropdown listing all 11 languages
- Selecting a language:
  - Stores in localStorage
  - Reloads the page content in the new language (Izana's intro, suggested questions, CTA text)
  - Fetches cached responses in the new language
  - Does NOT change the URL (no /es/ or /hi/ paths — language is client-side only)

---

## T4. SEARCH ANIMATION (Perplexity-Style)

### Purpose
Show the user that Izana is actually searching real clinical literature, not just generating text. This builds trust and feels premium.

### When It Appears
Every time Izana generates a response — on the landing page, in the main chat, after onboarding questions. It runs between the user's message and Izana's response.

### The 4 Stages

**Stage 1: "Understanding your question..."**
- Appears immediately after user sends a message
- Icon: 🔍 (or a subtle magnifying glass)
- Text fades in with a slight upward slide (12px)
- While active: icon gently pulses
- Completes when: backend sends "searching" stage event (or after 0.5s in timed mode)
- On complete: icon changes to ✓, text color fades to muted tertiary

**Stage 2: "Searching clinical literature..."**
- Appears 300ms after Stage 1 completes
- Icon: 📚 (or a book icon)
- Same fade-in animation
- While active: icon gently pulses
- Completes when: backend starts sending source events (or after 1.0s in timed mode)

**Stage 3: "Found N relevant sources..."**
- N = the actual number of sources returned by the RAG engine
- Each source title appears one at a time, sliding in from the left with 200ms delay between each
- Sources shown as small muted text: "• ESHRE IVF Guidelines, 2024"
- After all sources shown: stage completes

**Stage 4: "Crafting your answer..."**
- Icon: ✨ (sparkle)
- The ✨ icon pulses continuously while waiting for the first response token
- Completes when: first response token arrives from the backend

### After All Stages Complete
The entire animation block smoothly collapses (height shrinks to 0 over 400ms). It's replaced by the actual response text, which streams in word by word. After the response is complete, a small "Sources" section remains — showing the source titles as tappable pills. Tapping a source pill could eventually link to the document (but for MVP, just shows the title).

### Izana's Avatar During Animation
While the animation is running, Izana's ✦ avatar (shown to the left of the animation block) has a gentle breathing/pulsing animation — subtle scale oscillation from 100% to 104% on a 4-second loop. This gives the impression of "thinking." When the response starts streaming, the pulse stops and the avatar becomes static.

---

## T5. SIGNUP FLOW

### Trigger
User taps "Start my journey" on the landing page.

### What Happens
A bottom-sheet modal slides up from the bottom of the screen. The landing page chat content remains visible but dimmed behind a warm semi-transparent overlay (not cold black — use a warm dark purple at 40% opacity).

### The Modal Contains (One Screen, No Scrolling):

**Drag handle:** A small horizontal bar centered at the top (40px wide, 4px tall) in the border color. User can swipe down to dismiss.

**Avatar + Name Row (combined to save space):**
- Left side: Large avatar (52px) showing the currently selected avatar emoji on a gradient background. A small refresh icon (↻) in the bottom-right corner of the avatar.
- Right side: Small label "your anonymous identity" in tertiary text. Below it, the auto-generated pseudonym in 18px brand primary color with medium weight. Below the pseudonym, a tappable "new" link that regenerates the pseudonym.

**Avatar selection row:** A horizontal scrollable row of smaller avatars (36px each). The selected one has a thicker brand-colored border. Tapping any avatar:
- Updates the large avatar above
- Updates the border on the row
- Subtle scale bounce on the tapped one

**Pseudonym generation:**
- Format: {Adjective}{Noun}{2-digit number}
- 12 adjectives: Hopeful, Radiant, Brave, Serene, Vibrant, Gentle, Resilient, Luminous, Graceful, Steadfast, Tranquil, Fierce
- 12 nouns: Sunrise, Bloom, Journey, River, Meadow, Horizon, Garden, Aurora, Coral, Haven, Ocean, Willow
- Random 2-digit number: 10-99
- Total combinations: 12 × 12 × 90 = 12,960 unique names
- If a generated name is already taken (checked against Supabase), auto-regenerate

**Sex + Password Row (side by side):**
- Left: Sex toggle with two compact buttons "F" and "M". Default: Female. Selected button has brand primary background, unselected is plain. Small caption below: "(for bloodwork ranges)"
- Right: Password field. Placeholder: "At least 8 characters". Show/hide toggle on the right side of the field.

**Create button:** Full width, "Create my account", brand primary background, white text. Disabled (50% opacity) until password has 8+ characters.

**Caption:** "Anonymous · Terms & Privacy" (Terms and Privacy are tappable links)

### What Happens on "Create my account" (Decision 7 — Server-Side Transaction)

1. Button enters loading state (spinner replaces text)
2. Frontend calls: `POST /api/v1/auth/signup { pseudonym, password, gender, avatar, timezone }`
   **This is a single backend call that handles everything atomically (Decision 7).**
3. **Backend (single transaction):**
   a. Create Supabase auth user with email = `{pseudonym}@users.izana.ai`
   b. Insert profile row (pseudonym, gender, avatar, timezone)
   c. Create gamification record (0 points, 0 streak)
   d. Generate recovery phrase (XXXX-XXXX-XXXX-XXXX)
   e. Store SHA-256(phrase + salt) in recovery_phrases table
   f. **If ANY step fails → roll back ALL steps (delete auth user if created)**
   g. Return: `{ user_id, access_token, recovery_phrase }`
4. **If pseudonym is taken:** Backend returns 409. Frontend auto-regenerates a new pseudonym, shows toast "That name was taken — here's a new one!", keeps the modal open with new pseudonym displayed
5. **If signup succeeds:**
   a. Frontend stores the access_token (for subsequent API calls with `Authorization: Bearer` header — Decision 1)
   b. Close the signup modal
   c. Open the recovery phrase modal (separate bottom sheet) showing the recovery_phrase from the response
6. **If signup fails for other reason:** Show toast with human-friendly error

### Recovery Phrase Modal

After successful signup, a new bottom sheet appears:

- Key emoji (🔑) centered at top
- Headline: "Save your recovery phrase"
- Explanation: "Since Izana is anonymous, this is your only way back in. Keep it somewhere safe."
- The phrase itself: displayed in a bordered box, monospace font, large text, centered. Format: XXXX-XXXX-XXXX-XXXX (16 characters, 4 groups of 4)
- "Copy to clipboard" button. On tap: copies phrase, toast "Copied ✓"
- Primary button: "I've saved it — continue"

**Backend:** The phrase is generated server-side. A SHA-256 hash of the phrase (with a random salt) is stored in the recovery_phrases table. The plaintext phrase is returned to the frontend ONCE and never stored.

**On "I've saved it — continue":**
- Modal closes
- User lands in the chat interface with the onboarding flow starting (the "Getting started" header)
- The chat input is visible with placeholder "Ask anything..."

---

## T6. LOGIN FLOW

### Trigger
User taps "Log in" on the landing page.

### Login Modal
Same bottom-sheet pattern as signup. Contains:
- "Welcome back ✨" header
- Pseudonym input field (text, placeholder: pseudonym)
- Password input field (show/hide toggle)
- "Welcome back" primary button
- "Forgot password?" link below

### Login Process (Decision 6 — Anti-Enumeration)
1. User enters pseudonym + password
2. Frontend calls: `GET /auth/lookup?pseudonym=BraveOcean42`
3. **(Decision 6) Backend ALWAYS returns 200** with `{ email: "BraveOcean42@users.izana.ai" }` — regardless of whether the pseudonym exists. This prevents enumeration of the ~13,000 possible pseudonyms. Rate limited: 10 requests/min/IP.
4. Frontend calls Supabase `signInWithPassword({ email, password })`
5. **If login fails (wrong pseudonym OR wrong password — same error):** Show inline error: "Pseudonym or password is incorrect. Try again or use your recovery phrase." The user CANNOT distinguish "pseudonym doesn't exist" from "wrong password" — this is intentional.
6. **If success:** Close modal, navigate to /chat, fetch profile

### Recovery Flow
User taps "Forgot password?" → New modal appears:

- "Account recovery" header
- Pseudonym input
- Recovery phrase input (formatted as XXXX-XXXX-XXXX-XXXX, auto-dashes as user types)
- New password input
- "Reset my password" button

**Process:**
1. Backend receives pseudonym + recovery phrase
2. Looks up user by pseudonym
3. Hashes submitted phrase with the stored salt
4. Compares with stored hash
5. **If match:** Allows password reset via Supabase admin API. User logs in with new password.
6. **If no match:** "That recovery phrase doesn't match. Please check and try again."
7. **Rate limiting:** Maximum 3 recovery attempts per hour per IP address. After 3: "Too many attempts. Please try again in an hour."

---

## T7. CONVERSATIONAL ONBOARDING

### Purpose
Collect the 13 pieces of information Izana needs to generate a personalised plan, in under 3 minutes, in a way that feels like a conversation not a form.

### When It Happens
Immediately after signup + recovery phrase. User is in the chat interface. Header shows "Getting started" (no phase, no day count, no streak).

### Structure: 3 Rounds

The 13 questions are grouped into 3 themed rounds. Each round is presented as an Izana message followed by a card with grouped questions. The user answers all questions in a round, then taps "Next round →" to proceed.

A thin progress bar sits below the header showing "1 of 3" → "2 of 3" → "3 of 3". The bar fills with the brand primary color. It animates smoothly when advancing.

### Round 1: "Your Treatment"

Izana's message: "Round 1: Your treatment — Quick taps — this helps personalise everything."

The card contains these questions in order:

**Treatment type** (single-select, required):
Options: IVF 🔬, IUI 💉, Natural 🌱, Egg freezing ❄️, Exploring 🔍

**Current phase** (single-select, required — options depend on treatment type):
- If IVF selected: Preparing, Baseline, Stims, Retrieval, Two week wait
- If IUI selected: Preparing, Medication, Procedure day, Two week wait
- If Natural selected: Follicular, Fertile window, Two week wait
- If Egg Freezing selected: Preparing, Stims, Retrieval
- If Exploring selected: auto-set to "Learning", skip this question

**Day in phase** (only shows if phase is Stims, Baseline, TWW, or Medication):
- A horizontal number selector: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15+
- Scrollable if needed

**Age range** (single-select, required):
Options: 18–25, 26–30, 31–35, 36–40, 41+

"Next round →" button: disabled until treatment type, phase, and age range are all selected.

**After Round 1 submits:**
- The selections are sent to the backend
- Journey is created: POST /journey with treatment_type, phase, stim_day
- Chapter is auto-created by the backend
- The header updates to reflect the user's phase: e.g., "Your stims · day 8"
- Izana responds between the rounds: "IVF stims day 8 — you're in the home stretch. Let me learn about your lifestyle." This response appears as a normal Izana chat message.
- Progress bar advances to "2 of 3"

### Round 2: "Your Lifestyle"

Izana's message: "Round 2: Your lifestyle"

The card contains:

**Health conditions** (multi-select, "None" option clears others):
Options: PCOS, Endometriosis, Thyroid issues, Diabetes, Autoimmune, None

**Activity level** (single-select, required):
Options: Low, Moderate, Active

**Smoking** (single-select, required):
Options: Never, Former, Current

**Alcohol** (single-select, required):
Options: None, Occasional, Moderate

**Sleep** (single-select, required):
Options: Less than 6h, 6–7h, 7–8h, 8–9h, More than 9h

**Stress** (single-select, required):
Options: Rarely, Sometimes, Often, Always

"Next round →" button: disabled until all required fields selected.

**After Round 2 submits:**
- Izana responds: "Great — these details make a real difference to your plan. One more round about food."
- If user selected PCOS: Izana adds "I'll prioritise insulin-friendly nutrition for you."
- If user selected Thyroid: Izana adds "I'll make sure to include thyroid-supporting nutrients."
- Progress bar advances to "3 of 3"

### Round 3: "Food & Movement"

Izana's message: "Round 3: Food & movement"

The card contains:

**Allergies** (multi-select, "None" option clears others):
Options: Dairy, Gluten, Nuts, Soy, Eggs, Shellfish, None

**Dietary style** (multi-select or single-select):
Options: Vegetarian, Vegan, Pescatarian, Keto, Halal, Kosher, No restrictions

**Cuisines you love** (multi-select, at least 1 required):
Options: Mediterranean, Indian, Asian, Latin, Middle Eastern, Western, African

**Exercise preferences** (multi-select, at least 1 required):
Options: Yoga, Walking, Pilates, Swimming, Light gym, Stretching, Dance

**Exercise time per day** (single-select, required):
Options: 10 min, 20 min, 30 min, 45+ min

"Finish setup ✓" button: disabled until at least cuisine and exercise preferences selected.

**After Round 3 submits:**
- ALL wellness data saved to profile: POST /nutrition/wellness-profile
- Plan generation triggered automatically by the backend
- Confetti animation fires (80 particles, brand colors)
- Grand reveal message appears (see T8)
- The onboarding questions above collapse into a single summary line: "onboarding complete ✓ ▸"

### Auto-Linking Rules Within Rounds
- If "Dairy" selected in allergies → "dairy-free" auto-added to dietary restrictions (with a subtle note: "I've noted dairy-free based on your allergy")
- If "Gluten" selected → "gluten-free" auto-added
- If "Vegan" selected in dietary style → "Dairy" and "Eggs" auto-checked in allergies
- If "None" tapped in any multi-select → all other selections in that group are cleared
- If any specific option tapped after "None" → "None" is deselected

### Selection Chip Behavior
- Unselected: elevated background, brand primary text, subtle border, 10px text
- Selected: brand light purple background, brand primary text, thicker brand border
- Tapping a selected chip deselects it (toggle behavior for multi-select)
- Tapping an unselected chip selects it
- Subtle scale-down on tap (95% → 100% over 150ms)
- Single-select groups: selecting one automatically deselects others

### What If User Closes App Mid-Onboarding?
- State is saved after every round submission
- On re-open, the app checks: does this user have a completed wellness profile?
- If not: resume from the last incomplete round
- If Round 1 is complete but not Round 2: show Round 2 card with Izana's bridging message
- If nothing submitted yet: restart from Round 1
- If all 3 complete but grand reveal not shown: show grand reveal

---

## T8. GRAND REVEAL

### What It Is
The moment after onboarding when Izana shows the user what she knows about them and what happens next. It's the transition from "setup" to "your journey."

### What Shows

**Izana's message:** "You're all set, BraveOcean42 ✨" followed by "I'm creating your plan now — a nutritionist will review it. I'll let you know the moment it's ready. In the meantime, I'm here for anything you need."

**What happens next card:** A bordered card appearing below Izana's message with:
- ① "Your plan is being created. A nutritionist will review it — usually within a day."
- ② "While you wait, you can ask me anything or try a meditation."
- ③ "Tomorrow morning, I'll check in with you."

**Immediate action chips:** Three tappable buttons below the card:
- "🩸 Upload bloodwork" → navigates to bloodwork upload flow
- "🧘 Try a meditation" → opens the first phase-appropriate meditation in the media player
- A question chip with a phase-relevant question like "What to expect in stims?" → sends as a chat message

### Chat Input
Now active with placeholder: "Ask anything about your fertility journey..."
The chat is fully functional. The user can start asking questions immediately.

### What Happens in the Background
1. Profile saved with all wellness data
2. Cycle record created
3. Chapter/phase record created with the user's treatment info
4. Plan generation pipeline starts (Section J3)
5. Plan enters the approval queue with "normal" priority
6. All active nutritionists receive a push notification and email
7. Gamification record created: 0 points, streak = 1 (first day!)

---

## T9. THE GAP PERIOD (Between Signup and Plan Approval)

### Duration
Typically 1-24 hours. Target: under 4 hours.

### What the User Can Do
- Ask any question → full AI pipeline responds with sourced answers
- Upload bloodwork → get biomarker analysis
- Browse and play content (meditation, exercise videos) from the content library
- Check their profile in the "You" tab

### What the User Cannot See
- Any specific meal plan (the plan hasn't been approved yet)
- The "Your day" plan card does not appear
- No "Done" buttons for meals
- No points awarded for meal completion (no plan to compare against)

### What Shows Instead of the Plan Card

**Plan Status Card** (see T13 for full spec): Shows the progress of plan review:
- "Created: [time] ✓"
- "In review: — ⏳" (pulsing)
- "Ready: —"
- Caption: "Usually takes a few hours."
- Polls every 30 seconds for status changes

**Phase tips:** Izana proactively sends a message with general phase-appropriate tips:
"While your plan is being prepared, here are some general stims-day tips:
- Stay hydrated — aim for 2-3 litres of water
- Protein-rich foods support follicle development  
- Gentle movement like walking is ideal right now
- Avoid high-impact exercise during stims

Your personalised plan will be much more specific to your preferences. I'll let you know as soon as it's ready!"

These tips come from the phase_content table (pre-seeded data, not AI-generated).

**If the user asks "where's my plan?":**
Izana responds: "Your plan is currently being reviewed by our nutrition team. This usually takes a few hours. I'll notify you the moment it's ready!"

**If the plan is pending for more than 4 hours:**
- Backend triggers escalation: email to ALL nutritionists + admin with "OVERDUE" flag
- Any nutritionist can now review (not just the assigned one)
- User sees no difference — just continues waiting

**If the plan is pending for more than 24 hours:**
- Admin alert triggered
- User gets an updated message: "Your plan is taking a little longer than usual. Our team is on it — I'll let you know as soon as it's ready."

---

## T10. PLAN DELIVERY

### Trigger
The nutritionist approves (or modifies + approves) the plan in the nutritionist portal.

### What Happens (in order)

1. **Backend updates:** Plan status → APPROVED. Plan associated with user's active chapter.

2. **Push notification** sent to user's device:
   - Title: "Your plan is ready! 🎉"
   - Body: "Your personalised nutrition, exercise, and meditation plan has arrived."
   - Tapping the notification opens the app to the Today tab.

3. **In the chat** (when user opens or is already in the app):
   - The PlanStatusCard (if visible) animates: the "Ready" row gets a ✓, then the entire card briefly glows, then transforms.
   - Confetti fires (80 particles if first plan, standard celebration)
   - Izana's celebration message appears: "Your personalised plan is ready! 🎉 Your nutritionist reviewed and approved a plan designed for your [treatment phase], [dietary restriction] [cuisine] preferences, and [activity level] activity level."
   - The plan card appears below the message (see T12 for full plan card spec)

### The Plan Card
A bordered card with 3 tabs: Nutrition, Exercise, Meditation.

**Nutrition tab (default):** Shows today's meals in a vertical list:
- Each meal has: an emoji (🌅 breakfast, ☀️ lunch, 🌙 dinner), name, a one-line nutritional reason, and a "Done" action
- The first undone meal is the "next action" — shown at full opacity with the "Done" button visible
- Future meals are dimmed (50% opacity) — they become active as earlier ones are completed
- Completed meals show a green ✓ instead of "Done" and their text becomes muted

**Exercise tab:** Shows the assigned exercise:
- Video name, duration, intensity level
- A "▶ Play" button that opens the media player
- After completion: shows ✓ and duration logged

**Meditation tab:** Same pattern as exercise — audio name, duration, "▶ Play" button

**Progress indicator:** At the very bottom of the card, a thin 2px line shows completion progress. It fills from left to right as items are marked done. Below the line: "N of M done" in small muted text.

---

## T11. DAILY MORNING FLOW

### This is the core daily loop. Every morning follows this exact sequence.

### Trigger
User opens the app between 5am and 11pm (in their timezone). The app detects: has this user done a mood check-in today?

### If No Mood Check-in Yet (Morning State)

**Step 1: Yesterday collapses**
If there are messages from yesterday, they collapse to a single summary line:
"yesterday · [mood emoji] · [N/M] done ▸"
Tapping ▸ expands yesterday's full content (read-only).

If there are messages from even earlier (past week), they collapse to:
"Days 1–7 ▸"

**Step 2: Day marker**
A centered date label appears: "today · day [N]" (e.g., "today · day 9")
Style: small muted text, centered

**Step 3: Izana's morning message**
Izana sends a warm greeting with phase-specific context:

The greeting is time-sensitive:
- 5am-11am: "Good morning ✨"
- 11am-5pm: "Good afternoon ✨"
- 5pm-9pm: "Good evening ✨"
- 9pm-5am: "Hope you're resting well ✨"

Followed by a phase-specific line:
- Stims day 8: "Day 8 — you're getting close."
- Stims day 10: "Day 10 — you might hear about trigger timing soon."
- TWW day 5: "Day 5 of your wait — hang in there."
- Baseline day 3: "Day 3 of baseline — your body is preparing."

Followed by the question: "How are you feeling?"

**Step 4: Mood selector**
Directly below Izana's message (NOT a separate card — it's part of the conversation flow), 4 emoji buttons appear in a row:
- 😊 (great), 🙂 (good), 😐 (okay), 😢 (low)
- Small caption below: "tap how you feel"
- This is a ONE TAP interaction. User taps one emoji and they're done.

### After Mood Tap

1. Selected emoji bounces briefly (scales up to 130% then back to 100%, spring animation)
2. Other emojis fade to 30% opacity
3. After 300ms, the entire mood selector smoothly collapses (height animates to 0)
4. Mood is sent to backend: POST /companion/checkin with mood and today's date
5. Streak increments (handled by backend)
6. Streak number in the header updates (🔥 N+1)
7. Izana responds conversationally based on the mood:
   - great: "Feeling great — that's wonderful for day 9! 😊"
   - good: "Feeling good — that's great for day 9! 🙂"
   - okay: "Thanks for sharing. Stims can be a lot. I'm here."
   - low: "I hear you. Day 9 can be tough. Want to talk about it, or would a meditation help?"
8. Below Izana's response, a subtle link appears: "+ log symptoms"
   - Tapping this expands a list of phase-specific symptoms (fetched from GET /companion/symptoms/{phase})
   - Symptoms shown as toggle chips (e.g., Bloating, Fatigue, Headache, Cramping, Mood swings)
   - User taps the relevant ones, then "Save"
   - Symptoms are optional. Most users will skip this most days.
9. After a 500ms delay, the plan card slides in from below (if plan exists)

### After Plan Card Appears

The user now sees:
- Collapsed section for yesterday (if any)
- Today's date marker
- Izana's greeting (collapsed to just the mood response)
- The plan card with today's meals, exercise, meditation

They can:
- Tap "Done" on meals as they eat them
- Tap "▶ Play" on exercise or meditation
- Type any question in the chat input at any time

### When User Sends a Chat Message

The morning section (mood response + plan card) collapses to a summary line:
"morning · [emoji] [mood] · [N/M] done ▸"

The conversation takes over the screen. The user's message appears, then the search animation, then Izana's response.

### Evening Summary

Between 8pm and 9pm (user's timezone), the backend generates an evening summary and delivers it as a chat card. This happens via a background job that:
1. Calculates today's completions (meals, exercise, meditation, check-in)
2. Calculates points earned
3. Generates the summary card
4. Inserts it as a chat_log with message_type='week_summary_card'
5. Sends a push notification: "Your day 9 summary is ready ✨"

When the user opens the app (or if already open, the card appears in real-time):

Earlier conversations collapse to: "2 messages about [topic] ▸"

The evening summary card shows:
- "day [N] — done" header
- Rows: Check-in (mood + ✓ or not), Meals (N/3 ✓), Exercise (name + duration or "skipped"), Meditation (name + duration or "skipped")
- Points earned: "+55 points"
- Streak: "🔥 N-day streak!"
- Izana's evening message below the card: a gentle recommendation. Example: "Try the 10-min visualisation before bed — it might help with the trigger timing nerves. Sleep well ❤️"

**Special cases:**
- If all items completed: card gets a subtle glow border, Izana says "Perfect day!"
- If streak milestone (7, 14, 30, 60, 100): confetti fires, special toast
- If grief mode: no points, no streak, softer language

---

## T12. PHASE TRANSITION

### How It Works
Each treatment phase has an expected duration (stored in phase_durations table). The backend tracks how many days the user has been in the current phase.

### Soft Check-in (at ~80% of expected duration)
When the user reaches approximately 80% of the expected phase duration (e.g., day 8 of ~10 for stims), Izana sends a conversational check-in:

"Day 10 — many people get their trigger shot around now. Any news from your clinic today?"

Below this message, 3 response options appear as tappable buttons:
1. "Yes, I've had my trigger shot" → triggers transition
2. "Not yet, still stimming" → Izana responds "No rush — everyone's timeline is different. I'll check back in a couple of days."
3. "I'm not sure" → Izana responds "That's okay! Just let me know when you hear from your clinic."

### Transition Confirmation (when user confirms)
If the user taps the confirmation option (e.g., "Yes, I've had my trigger shot"):

1. Izana responds warmly: "Trigger done! You're moving into the next phase. I'm updating your plan now."
2. Toast: "Moving to your trigger phase ✨"
3. **Backend actions:**
   a. Current chapter closed (ended_at = now, status = 'completed')
   b. AI generates a summary of the closing chapter
   c. New chapter opened for the next phase
   d. New plan generation triggered with URGENT_PHASE_CHANGE priority
   e. All nutritionists notified with urgency
4. **Frontend updates:**
   a. Chapter header changes: "Your trigger · day 1"
   b. Streak continues (doesn't reset on phase change)
   c. PlanStatusCard appears (since new plan is being generated)
   d. Phase-appropriate tips shown while waiting

### Follow-up Check-ins
If the user said "not yet" or "not sure", the backend schedules another check-in in 2-3 days. This continues until:
- The user confirms the transition, OR
- The phase exceeds its maximum expected duration, at which point Izana sends a more direct message: "You've been in stims for [N] days — that's longer than typical. Has anything changed with your clinic? Just let me know so I can keep your plan on track."

### User-Initiated Transitions
The user can also trigger a transition at any time by telling Izana in natural language: "I had my retrieval today" or "I just started TWW." Swarm 1 (Gatekeeper) and Swarm 9 (Context) detect transition-related statements and present the confirmation options.

### Phase Skipping (Decision 13)
If the user selects a phase that is NOT the immediate next phase (e.g., jumps from Stims to Retrieval, skipping Trigger), the app shows a confirmation:

```
"That skips the trigger phase. Are you sure?"
[Yes, I skipped trigger]  [No, go back]
```

On confirmation:
1. Auto-create intermediate chapter(s) for skipped phase(s) with:
   - `status = 'completed'`
   - `ended_at = now()`
   - `summary_text = 'Phase skipped by user'`
   - `day_count = 0`
2. Create the new chapter for the selected phase
3. Trigger plan generation for the new phase
4. All skipped phases appear in the Journey timeline as "Skipped" with a grey indicator

---

## T13. PLAN STATUS CARD

### What It Is
A card that appears in the chat when the user has a plan in the review queue (not yet approved). It shows the progress of the review process.

### When It Appears
- After onboarding completes (first plan being generated)
- After a phase transition (new plan being generated)
- When the user asks about their plan status

### How It Works
The card polls GET /plan-status every 30 seconds. The response includes:
- status: GENERATING, PENDING_NUTRITIONIST, IN_REVIEW, APPROVED, MODIFIED
- created_at: when the plan was generated
- assigned_at: when a nutritionist claimed it (null if not yet)

### Visual States (3 rows, showing progression)

**GENERATING state:**
- Row 1: "Created" — time — ✓ (green)
- Row 2: "In review" — — — ⏳ (pulsing)
- Row 3: "Ready" — — — (empty)
- Caption: "Your plan is being created..."

**PENDING_NUTRITIONIST state:**
- Row 1: "Created" — time — ✓
- Row 2: "In review" — — — ⏳ (pulsing)
- Row 3: "Ready" — — — (empty)
- Caption: "Waiting for a nutritionist to review..."

**IN_REVIEW state:**
- Row 1: "Created" — time — ✓
- Row 2: "In review" — time — ✓ (this ✓ appears with a fade-in when status changes)
- Row 3: "Ready" — — — ⏳ (pulsing)
- Caption: "Your nutritionist is reviewing now..."

**APPROVED/MODIFIED state:**
- Row 1: "Created" — time — ✓
- Row 2: "In review" — time — ✓
- Row 3: "Ready" — time — ✓ (appears with fade-in)
- All three rows green briefly
- Then: confetti fires, card transforms into the plan delivery celebration (Section T10)

### Pulsing ⏳ Animation
The hourglass/clock emoji on the active row gently pulses: opacity oscillates between 0.4 and 1.0 on a 1.5-second loop. This gives the card a sense of "alive, waiting."

---

## T14. MEDIA PLAYER

### What It Is
A slide-up overlay that plays exercise videos and meditation audios from Cloudflare Stream.

### When It Opens
User taps "▶ Play" on any exercise or meditation item in the plan card, content library, or suggestion chip.

### Opening Animation
1. Background overlay appears (warm dark, 40% opacity)
2. Player panel slides up from the bottom (spring-damped, slight bounce)
3. Content thumbnail is visible immediately (cached from Cloudflare)
4. While the stream URL loads: "Loading your session..." text with play button pulsing

### Player Layout

**For video:**
- Video fills the width of the screen
- Below video: title, duration, intensity badge
- Controls: play/pause (center), seek bar, time elapsed / total
- Close button: ✕ in top-right corner
- The video uses HLS adaptive bitrate streaming via hls.js

**For audio:**
- No video area — instead, a large calm illustration or gradient background
- Title and duration centered
- Play/pause button (large, centered)
- Seek bar
- Close button

### Progress Tracking
- As the user watches/listens, progress is saved every 30 seconds: POST /content/{id}/progress with progress_pct and position_seconds
- If the user closes and reopens, it resumes from where they left off
- Completion is recorded when progress reaches 90%+ : POST /content/{id}/progress with completed: true
- On completion: toast with points earned

### Closing
- Swipe down or tap ✕ to close
- Player slides back down (reverse of opening)
- Progress is saved on close
- If the content was completed (90%+), the plan card item shows ✓

---

## T15. JOURNEY TAB

### What It Is
The second tab. Shows the user's complete treatment timeline, bloodwork, mood trends, and doctor sharing.

### Layout

**Top:** Page header "Your journey" with treatment label below (e.g., "IVF Cycle 1")

**Quick action buttons:** Three buttons in a horizontal row:
- 🩸 Bloodwork — opens bloodwork upload and results sub-page
- 📊 Trends — opens mood and adherence trend charts
- 🩺 Doctor — opens the share-with-doctor modal

**Timeline:** A vertical timeline showing all phases (chapters) the user has been through:

Each phase is a card on the timeline with:
- A dot on the left connected by a vertical line to other phases
- Phase name and duration (or "day N →" if active)
- Date range
- Stats (streak, mood, adherence %) for the active phase

**Active phase:** Highlighted with a thicker brand-colored border, purple dot, and "day N →" instead of a duration.

**Completed phases:** Standard border, green dot, green "✓" with day count.

**Tapping a completed phase:** Opens it in a read-only view showing all messages from that phase. No input bar (can't send new messages to a completed phase). Back button returns to the timeline.

### Bloodwork Sub-Page
- Upload area: drag-and-drop or tap to select file (PDF, JPG, PNG, max 5MB)
- After upload: shows extracted biomarker values in a table (from Swarm 2)
- User confirms values are correct (can edit manually)
- After confirmation: analysis runs (Swarm 5 + 6)
- Analysis results shown as plain-language interpretation of each biomarker
- Historical comparison: if previous bloodwork exists, shows trends (arrows up/down)

### Trends Sub-Page
- Mood chart: line chart showing daily mood over time (last 30 days default, selectable range)
- Adherence chart: daily plan completion percentage
- Exercise minutes: bar chart by day
- All charts use the brand colors (purple primary, bronze for secondary data)

### Share With Doctor Modal
- Opens when user taps 🩺 or "Share with my doctor" from chapter header menu
- Checkboxes: what to include in the report:
  - ☑ Treatment timeline (default on)
  - ☑ Bloodwork results (default on)
  - ☑ Check-in history (default on)
  - ☐ Plan adherence (default off)
  - ☐ Wellness profile (default off)
- "Valid for" selector: 1 day, 7 days, 30 days, 90 days (default: 7 days)
- "Max views" selector: 1, 5, 10, 50, 100 (default: 10)
- "Generate report" button
- On generate: backend creates a PDF using reportlab, generates a unique token, returns a URL
- URL shown with "Copy link" button and share options (WhatsApp, SMS, email)
- The link is accessible without login (public, token-protected)
- Every access to the link is logged in the PHI audit table

---

## T16. YOU TAB

### What It Is
The third tab. The user's personal space — profile, partner, content, achievements, settings.

### Layout

**Header:** Avatar (large, with gradient background) + pseudonym + treatment info + level

**Stats row:** Three stat boxes:
- Points (number + "pts" label)
- Streak (number + "day streak" label + 🔥)
- Badges (number + badge emoji)

**Menu sections:** Two grouped lists of tappable rows:

**First group:**
- Partner → shows connection status ("Connected ✓" or "Invite partner")
- Content library → browse all exercise videos and meditation audios
- Achievements → badges earned and upcoming
- Settings → theme toggle, language, notification preferences

**Second group:**
- Privacy & data → GDPR controls, data export, account deletion
- About Izana → version, mission statement
- Log out → confirmation ("Are you sure?" → "Yes, log out" / "Not now"), then redirect to landing

### Partner Row Behavior
- If no partner linked: shows "Invite partner" in brand primary color
  - Tapping opens partner invite flow (generates 48-hour code, share options)
- If partner connected: shows "Connected ✓" in green
  - Tapping opens partner settings (visibility toggles: what the partner can see)
- If partner invite pending: shows "Invite sent — expires in [time]"

### Content Library Sub-Page
- Two tabs: "Exercise" and "Meditation"
- Grid or list of content items, each showing: thumbnail (from Cloudflare), title, duration, intensity
- Filter pills at top by phase (showing only content appropriate for current phase, but "All" option available)
- Tapping any item opens the media player
- Items already completed show a green ✓ badge

### Achievements Sub-Page
- Grid of badge circles
- Earned badges: full color with earned date
- Unearned badges: greyed out with criteria text (e.g., "Log meals for 7 days")
- Badge categories: Streak, Nutrition, Exercise, Couple, Special
- Earning a badge triggers confetti + toast

### Settings Sub-Page
- Theme: three options (System, Light, Dark) — tapping one applies immediately
- Language: selector with 11 options — changing reloads all UI text
- Notifications: toggle for push notifications (enable/disable)
- Daily check-in time: when should Izana's morning message arrive? (default: auto-detect from timezone, but user can override)

### Privacy & Data Sub-Page
- **"Generate new recovery phrase"** (Decision 14):
  - Button opens a modal requiring the user's current password
  - On password verification: calls `POST /recovery/regenerate`
  - Backend generates new phrase, replaces old SHA-256 hash in `recovery_phrases` table
  - New phrase displayed once in the same modal (monospace, copy button)
  - Old phrase immediately becomes invalid
  - This prevents permanent account loss if the user lost their original phrase
- "Download my data" → generates a JSON export of all user data, emailed or downloaded
- "Delete my account" → serious action:
  - Warning: "This will permanently delete your account, all conversations, plans, and bloodwork data. This cannot be undone."
  - Requires typing the pseudonym to confirm
  - On confirm: backend marks all user data for deletion, logs out, redirects to landing
  - Grace period: 30 days before permanent deletion (user can log back in to cancel)

---

## T17. PARTNER VIEW

### What It Is
When a partner joins via invite code, they get their own Izana account with a modified experience focused on supporting the primary user.

### Partner Onboarding (Abbreviated)
The partner only goes through:
1. Signup modal (same as primary: pseudonym, avatar, sex, password)
2. Recovery phrase
3. Landing directly in their partner chat — no wellness rounds, no treatment selection

### Partner's Header
Instead of "Your stims · day 8", the partner sees: "Supporting stims · day 8"
The word "Supporting" makes them feel like an active participant, not a spectator.

### Partner's Morning Message
Izana's greeting is partner-specific:
"Your partner is on day 10 of stims — they might get trigger timing news today. They're feeling good and keeping up with their plan."

The information included depends on what the primary user has made visible (configurable in partner visibility settings):
- Mood: visible by default → "They're feeling good"
- Phase and day: visible by default → "day 10 of stims"
- Symptoms: hidden by default → not mentioned
- Plan adherence: hidden by default → "keeping up with their plan" (generic)
- Bloodwork: NEVER visible to partner

### Partner's Action Buttons
Below the morning message, 3 contextual actions:
- "💬 Send encouragement" → opens a text input to send a kind message (delivered to primary user as a partner card in their chat)
- "🧘 Couples meditation" → opens a meditation designed for couples (content tagged partner_suitable=true)
- "❓ Ask about supporting [phase]" → sends a question to the AI specifically about how to support someone in this treatment phase

### Partner's Chat
The partner can ask Izana any question. The AI knows they're a partner and tailors responses accordingly. For example:
- "How can I support my partner during stims?" → Gets specific, practical advice
- "What foods should I cook for her?" → Gets nutrition recommendations aligned with the primary user's plan (but not the specific plan details)
- "Is it normal to feel helpless?" → Gets emotional support for the partner

### Couple Streaks and Goals
If both partners are active on the same day, a "couple streak" increments. This is visible to both users. The partner can also see shared couple goals (set by either user) and contribute to them.

---

## T18. GRIEF MODE

### Trigger
The primary user records a NEGATIVE outcome, CHEMICAL pregnancy, MISCARRIAGE, or ECTOPIC via the outcome recording flow.

### Immediate Changes (Day 0)

**Visual:**
- Brand primary color shifts to a muted tone (the deep amethyst becomes a softer greyed purple)
- Brand secondary (bronze) becomes muted
- The data attribute `data-grief-mode="true"` is set on the root element

**Hidden elements:**
- Streak indicator in header: hidden
- Points display: hidden everywhere
- Badge celebrations: suppressed
- Confetti: disabled entirely
- Gamification toasts ("+10 points"): suppressed

**Chat behavior:**
- Izana's response to the outcome: pure empathy. No advice, no "silver linings," no "at least." Just: "I'm so sorry. This is a loss, and there's nothing I can say to make it better. I'm here with you."
- No check-in prompt that day
- No plan card
- No evening summary

### Day 1
Izana sends (gently, once): "I'm here whenever you're ready. No pressure at all."

### Day 3
Izana sends: "When you're ready, I have some options for you. No rush."
Below this, three buttons:
- "Show me a recovery plan" → generates a gentle recovery-focused plan
- "I want to talk about what happened" → opens supportive conversation
- "I need more time" → Izana responds "Take all the time you need. I'm not going anywhere."

### Day 5+
If the user returns and interacts:
- Actions are logged but NOT scored (no points)
- Plans are shown if requested but with no gamification
- Tone remains gentle

### Resumption
The user opts back in by either:
- Recording a new cycle start
- Explicitly saying "I'm ready to start again"
- Choosing a new treatment path

When they resume:
- Streak resets to 1 (no "you lost your streak" messaging — it just quietly starts fresh)
- Gamification reactivates
- Colors return to normal
- Izana: "Welcome back. I'm glad you're here. Let's start fresh."

---

## T19. DISENGAGEMENT SENSING

### What It Is
Izana detects when a user goes silent and adjusts its behavior accordingly. It never guilt-trips, never says "I missed you," never implies the user did something wrong by being away.

### Behavior by Days of Silence

**1 day of no interaction:** Normal. No special behavior. Many users skip a day.

**2 days:** Backend flags the user as "quiet." Changes:
- Meal/activity reminder nudges are paused
- Only critical notifications continue (phase transition timing, plan approved)
- Izana's tone becomes softer in any generated content

**3-5 days:** All non-critical nudges pause. Only phase transition checks continue if a transition is imminent. No push notifications for reminders.

**5+ days:** Complete silence from Izana. No push notifications, no nudges, nothing. The user's choice to step away is respected completely.

### When the User Returns

Regardless of how long they've been away, Izana's first message is always:
"Welcome back! How are you today?"

No mention of the gap. No "where have you been?" No "you've been away for X days." Just a warm, fresh greeting as if they were never gone.

If their phase has likely changed during the absence (e.g., they were on day 8 of stims and 14 days have passed), Izana will ask: "It's been a little while — where are you in your treatment now?" with phase options to update.

---

## T20. OFFLINE BEHAVIOR

### What Happens When Connection is Lost

**Immediate:**
- A thin amber banner slides down from below the header: "You're offline — some features may be limited"
- The banner is dismissible (tap ✕) but reappears if user tries an action that requires connection

**What Still Works Offline:**
- Reading cached messages (today's messages + last 2 days)
- Viewing the current plan card (cached in IndexedDB)
- Completing mood check-in (queued locally)
- Marking meals as "Done" (queued locally)
- Viewing downloaded content (if any was cached — audio only, videos are too large)

**What Doesn't Work Offline:**
- Sending chat messages (input shows "Available when connected")
- Uploading bloodwork
- Playing videos (not cached)
- Loading new content from the library
- Any navigation to screens that require fresh data

**Offline Queue:**
All actions taken offline (mood check-ins, meal completions, etc.) are stored in IndexedDB. Each action includes a timestamp and the action data.

### When Connection Returns
1. Amber banner changes to: "Reconnecting..." (briefly)
2. Offline queue syncs: each action sent to the backend in chronological order
3. If any action fails (e.g., duplicate check-in for a date): silently skip it
4. After sync complete: banner changes to "All caught up ✓" (2 seconds, then disappears)
5. Fresh data fetches for all visible screens
6. Sync uses exponential backoff if reconnection is intermittent

---

*End of Section T. This section specifies every user-facing feature, flow, state, and interaction in the app. Claude Code should reference this alongside the earlier sections for design tokens, microcopy, and technical architecture.*

---

# END OF BUILD GUIDE

**20 sections (A through T). 6 build phases. ~13 Claude Code sessions.**

This document contains everything needed to build Izana from an empty directory: product definition, design system, 13 screen layouts, microcopy tables, animation specs, edge cases, tech stack, database schema, backend architecture with 60+ API endpoints, 11 AI swarm configurations, chatbot persona rules, plan system, nutritionist portal, admin dashboard, FIE pipeline, infrastructure setup, and now component-level behavioral specifications for every feature, flow, state, and interaction.

Give this file to Claude Code with your environment variables and start building.
