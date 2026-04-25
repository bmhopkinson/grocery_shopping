# Grocery Shopping Meal Planner

An AI-powered meal planning app that finds recipes, extracts their ingredients, and adds them to Apple Reminders. You describe a cuisine or paste a recipe URL; the app handles the rest — searching, parsing, de-duplicating against what you already have, and writing directly to your Reminders list.

---

## Table of Contents

- [System Overview](#system-overview)
- [Services](#services)
  - [Frontend](#frontend-react--vite)
  - [FastAPI Server (meal\_planner\_server)](#fastapi-server-meal_planner_server)
  - [LangGraph Workflow (meal\_planner)](#langgraph-workflow-meal_planner)
  - [Reminders Proxy (reminders\_server)](#reminders-proxy-reminders_server)
- [Database](#database-postgresql)
- [How the Services Talk to Each Other](#how-the-services-talk-to-each-other)
- [Key Design Concepts](#key-design-concepts)
- [Data Models](#data-models)
- [Ingredient Collation](#ingredient-collation)
- [Running the App](#running-the-app)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)

---

## System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite)                                           │
│  port 3000 → proxies /api to port 8000                           │
└──────────────────────────┬────────────────────────────────────────┘
                           │  HTTP + SSE
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│  FastAPI Server  (meal_planner_server.py)  port 8000              │
│  · Owns user sessions                                             │
│  · Streams SSE events to browser                                  │
│  · Detects LangGraph interrupts and converts them to SSE events   │
└─────────┬────────────────────────────────────┬────────────────────┘
          │  astream_events                    │ reads/writes
          ▼                                    ▼
┌─────────────────────┐              ┌──────────────────────────────┐
│  LangGraph Workflow │              │  PostgreSQL 16   port 5432   │
│  (meal_planner.py)  │              │  · Persists graph checkpoints │
│  · Graph execution  │              │  · Survives server restarts  │
│  · Node calls       │              └──────────────────────────────┘
└──┬──────┬───────────┘
   │      │
   │      │  HTTP (from Docker container)
   │      ▼
   │  ┌──────────────────────────────────────────────┐
   │  │  Reminders Proxy  (reminders_server.py)      │
   │  │  port 8765  — runs on the Mac host           │
   │  │  · Receives REST calls from the container    │
   │  │  · Executes osascript on the host            │
   │  └─────────────────────┬────────────────────────┘
   │                        │  osascript
   │                        ▼
   │                   Reminders.app (macOS)
   │
   │  Direct API calls (OpenAI, DuckDuckGo)
   ▼
External: OpenAI GPT-5.2 · DuckDuckGo Search
```

Four distinct runtime components, each with a clear responsibility:

| Component | Where it runs | Port | Key job |
|---|---|---|---|
| React frontend | Mac host | 3000 | User interface + SSE rendering |
| FastAPI server | Docker container | 8000 | Session management, SSE streaming |
| PostgreSQL | Docker container | 5432 | Graph checkpoint persistence |
| Reminders proxy | Mac host | 8765 | Bridge from Docker to macOS Reminders |

---

## Services

### Frontend (React + Vite)

**`frontend/src/`**

The frontend is a single-page React app built with Vite and Material-UI. It has no application logic of its own — it is entirely event-driven by the SSE stream it receives from the backend.

#### Lifecycle

1. User fills in a cuisine name or pastes a recipe URL in **CuisineInput**.
2. App opens an SSE connection to `/api/plan` and begins processing events.
3. Each `meal_options`, `ingredient_review`, or `reminders_prompt` event causes the app to pause and render an interactive component asking for user input.
4. When the user responds, the frontend POSTs to `/api/sessions/{id}/resume` and opens a new SSE stream to continue.
5. A `complete` event ends the flow and renders the **CompletionScreen**.

#### Components

| Component | Purpose |
|---|---|
| `App.jsx` | Root component; owns stage state and SSE event dispatch |
| `CuisineInput.jsx` | Cuisine search or direct URL input; optional source site filtering |
| `MealSelection.jsx` | Radio-button list of 5 recipe options with descriptions |
| `IngredientReview.jsx` | Checkbox review of extracted ingredients; supports freeform removal commands |
| `RemindersPrompt.jsx` | Dropdown of existing lists or text field for a new list name |
| `CompletionScreen.jsx` | Final summary: recipe chosen, grocery list, Reminders result |
| `StatusDisplay.jsx` | Live progress chip strip showing the last 5 status events |

#### SSE Parsing

The browser receives a raw `text/event-stream`. `App.jsx` manually parses the `event:` / `data:` pairs (standard SSE format), then routes each event type to the appropriate state update. There is no third-party SSE library involved; the browser `EventSource` API is used directly.

#### API Communication

Vite proxies all `/api` requests to `http://localhost:8000`, so the frontend never hardcodes a backend host. Two HTTP patterns are used:

- `POST /api/plan` → opens an SSE stream, receiving events until interrupt or completion.
- `POST /api/sessions/{id}/resume` → resumes a paused graph; also returns an SSE stream.

---

### FastAPI Server (`meal_planner_server`)

**`backend/meal_planner_server.py`**

This is the HTTP boundary of the system. It translates between the browser's request/response model and the LangGraph event stream, while also managing session state.

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/plan` | Start a new planning session; returns SSE stream |
| `POST` | `/sessions/{id}/resume` | Resume from an interrupt; returns SSE stream |
| `GET` | `/sessions/{id}` | Inspect current session state (debug) |
| `DELETE` | `/sessions/{id}` | Remove a session from memory |
| `GET` | `/health` | Liveness check |

#### Session Management

Sessions are kept in a plain in-memory dict (`sessions: dict`). Each entry stores:

- A `MealPlanner` graph instance
- A LangGraph `thread_id` (used as the checkpointer key)
- The latest `graph_state` snapshot

Sessions survive graph interrupts because the LangGraph checkpointer (PostgreSQL or MemorySaver) persists the full execution state. The in-memory dict only needs to survive as long as the user's browser session.

#### SSE Streaming

Both `/plan` and `/resume` return a `EventSourceResponse` from `sse-starlette`. The server runs `graph.astream_events(...)` in an async generator and yields each event as an SSE frame. Events are newline-delimited JSON with an `event:` type field.

#### Interrupt Detection

When LangGraph hits an `interrupt()` call inside a node, `astream_events` surfaces it as a special event type. The server uses the **interrupt registry** (`backend/server/interrupts.py`) to inspect the interrupt's payload and decide which SSE event to emit:

```
Interrupt payload contains "existing_lists"  →  reminders_prompt
Interrupt payload contains "options" list    →  meal_options
Interrupt payload contains "remove" keyword  →  ingredient_review
Anything else                                →  generic_interrupt
```

This pattern means the server never needs to know about specific node names — the payload structure determines the event type.

#### SSE Event Reference

| Event | Payload | Meaning |
|---|---|---|
| `session_start` | `{session_id}` | Session created; ID for future resume calls |
| `status` | `{node, message}` | Progress update from a running node |
| `meal_options` | `{options[], prompt, instruction}` | **Interrupt** — user must pick a recipe |
| `ingredient_review` | `{ingredients[], prompt, instruction}` | **Interrupt** — user reviews extracted ingredients |
| `reminders_prompt` | `{items[], existing_lists[], prompt, instruction}` | **Interrupt** — user picks target Reminders list |
| `grocery_list` | `{items[]}` | Final consolidated ingredient list |
| `complete` | `{selected_meal, grocery_list[], reminders_added}` | Workflow finished |
| `error` | `{message}` | Something went wrong |

---

### LangGraph Workflow (`meal_planner`)

**`backend/meal_planner.py`** and **`backend/nodes/`**

The core AI workflow. It is a directed graph where each node is a Python function, edges are conditional routing functions, and human input is handled via `interrupt()` calls that pause execution until the server resumes them.

For a full diagram of the graph structure and state transitions, see [`docs/graph-architecture.md`](docs/graph-architecture.md).

#### Graph Structure

The main graph has two entry paths depending on whether the user typed a cuisine or pasted a URL:

```
                    ┌── search_meals
                    │   parse_meals
cuisine input ──────┤   validate_recipes ──(needs refining?)── refine_search ──┐
                    │   should_refine                                            │
                    │   present_options  ⚡ INTERRUPT                           │
                    │        │           ←─────────────────────────────────────┘
                    │        ▼
                    └── process_meal subgraph ─────────────────────────────────────
                              │
direct URL ───────────────────┘
(create_meal_from_url)

process_meal subgraph:
  extract_ingredients
  review_ingredients   ⚡ INTERRUPT
  add_to_reminders     ⚡ INTERRUPT
```

#### Nodes

**Search nodes** (`backend/nodes/search.py`)

| Node | What it does |
|---|---|
| `search_meals` | DuckDuckGo search: `"{cuisine} dinner recipe with ingredients"` |
| `parse_meals` | LLM extracts 5 structured recipes (name, description, URL) from raw search results |
| `validate_recipes` | Filters out aggregator/collection URLs; sets `refine_dishes` if fewer than 3 valid recipes found |
| `refine_search` | Re-searches for specific dish names and merges results, deduplicating by URL |

**Processing nodes** (`backend/nodes/processing.py`)

| Node | What it does |
|---|---|
| `create_meal_from_url` | Fetches the target URL, extracts the recipe title, and auto-selects it |
| `present_options` | Emits the meal options interrupt; resumes with the user's string selection (e.g. `"2"`) |
| `extract_ingredients` | Fetches the recipe HTML; tries JSON-LD structured data first, falls back to plain text; LLM extracts a structured ingredient list |
| `review_ingredients` | Emits the ingredient review interrupt; supports checkbox JSON or freeform `"remove X, Y"` commands |

**Reminders node** (`backend/nodes/reminders_node.py`)

| Node | What it does |
|---|---|
| `add_to_reminders` | Reads the user's existing Reminders list; runs smart collation; batch-deletes outdated items; adds new/combined items; supports skip and new-list creation |

**Routing functions** (`backend/nodes/routing.py`)

| Function | Decision |
|---|---|
| `route_by_input` | `direct_url` present → `create_meal_from_url`; else → `search_meals` |
| `should_refine` | `refine_dishes` set → `refine_search`; else → `present_options` |

#### HTML Extraction (`backend/nodes/html_utils.py`)

Recipe pages are parsed in two passes:

1. **JSON-LD** — most cooking sites embed `@type: Recipe` structured data. When present this gives a clean, structured ingredient list.
2. **Plain text fallback** — BeautifulSoup strips navigation, scripts, and ads; the remaining text is truncated to ~30 KB and passed to the LLM.

#### LLM Usage

All LLM calls use **structured output** via `with_structured_output(PydanticModel)`. This guarantees the LLM returns parseable JSON conforming to a schema, rather than free-form text. Prompt templates live in `backend/prompts.py`. The LLM singleton is initialised once in `backend/nodes/base.py` and reused across all nodes.

---

### Reminders Proxy (`reminders_server`)

**`backend/reminders_server.py`** and **`backend/reminders.py`**

macOS Reminders can only be accessed via AppleScript, which requires running `osascript` on the Mac host. Because the FastAPI server runs inside a Docker container, it cannot call `osascript` directly.

The proxy solves this with a small FastAPI app that runs on the Mac host itself. The Docker container calls it over HTTP; the proxy executes the AppleScript and returns the result.

#### Why a separate proxy and not just host networking?

AppleScript and the macOS TCC (Transparency, Consent, and Control) system require the calling process to have been granted Reminders access explicitly. A process running inside a Docker VM does not appear to the TCC daemon as a trusted process. Running the proxy as a native Mac Python process means the TCC grant is given once to that process and then works reliably.

The proxy also batches delete operations into a single AppleScript call. Issuing many rapid `delete reminder` commands triggers repeated TCC permission checks that can hang the Reminders app.

#### Proxy Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/reminder` | Create a single reminder in a list |
| `GET` | `/lists` | Return all Reminders list names |
| `POST` | `/lists` | Create a new list |
| `GET` | `/lists/{name}/exists` | Check if a list exists |
| `GET` | `/lists/{name}/items` | Return all reminder texts in a list |
| `DELETE` | `/reminder` | Delete a single reminder |
| `DELETE` | `/reminders/batch` | Delete multiple reminders in one AppleScript call |
| `GET` | `/health` | Liveness check |

#### reminders.py Abstraction

`backend/reminders.py` provides a single API to the rest of the application regardless of execution mode:

- If `REMINDERS_PROXY_URL` is set → delegates to the HTTP proxy
- Otherwise → calls `osascript` directly (local dev without Docker)

This means the node code (`reminders_node.py`) is never aware of which mode is active.

---

## Database (PostgreSQL)

PostgreSQL serves one purpose: **LangGraph checkpoint persistence**.

LangGraph's checkpointer snapshots the full graph state (all accumulated `MealPlannerState` fields, the message history, the current node position) after every node execution. This means:

- The server can be restarted between a user selecting a recipe and reviewing ingredients without losing their session.
- Interrupt/resume cycles work reliably — the graph resumes from exactly the state it was in when it paused.
- Multiple concurrent users each have their own isolated `thread_id` checkpoint stream.

The checkpointer uses the `langgraph-checkpoint-postgres` package with an async `AsyncConnectionPool`. At startup, `meal_planner_server.py` calls `setup_checkpointer()`, which either creates an `AsyncPostgresSaver` connected to `DATABASE_URL` or falls back to an in-memory `MemorySaver` if no database is available.

```
DATABASE_URL=postgresql://mealplanner:mealplanner@postgres:5432/mealplanner
```

The Docker Compose setup runs PostgreSQL on port 5433 externally (5432 internally) so it doesn't clash with any locally installed Postgres.

---

## How the Services Talk to Each Other

### Starting a session

```
Browser                FastAPI               LangGraph            PostgreSQL
  │                       │                      │                     │
  │── POST /plan ─────────▶                      │                     │
  │                       │── create session ────▶                     │
  │                       │── astream_events() ──▶                     │
  │                       │                      │── checkpoint ───────▶
  │◀── SSE: session_start ─                      │                     │
  │◀── SSE: status ────────                      │                     │
  │◀── SSE: status ────────                      │                     │
  │                       │       (interrupt)    │                     │
  │◀── SSE: meal_options ──                      │                     │
```

### Resuming from an interrupt

```
Browser                FastAPI               LangGraph            PostgreSQL
  │                       │                      │                     │
  │── POST /resume ────────▶                      │                     │
  │   {input: "2"}        │── Command(resume) ───▶                     │
  │                       │                      │── load checkpoint ──▶
  │                       │                      │◀── state ───────────│
  │◀── SSE: status ────────                      │                     │
  │◀── SSE: ingredient_review                    │── checkpoint ───────▶
```

### Adding to Reminders (from Docker)

```
LangGraph node         Reminders Proxy         Reminders.app
(inside Docker)        (Mac host :8765)
  │                          │                      │
  │── GET /lists ────────────▶                      │
  │                          │── osascript ─────────▶
  │                          │◀── list names ────────│
  │◀── ["Groceries", ...] ───│                      │
  │                          │                      │
  │── DELETE /reminders/batch▶                      │
  │   (old items)            │── osascript ─────────▶
  │◀── 200 OK ───────────────│                      │
  │                          │                      │
  │── POST /reminder ─────────▶  (×N new items)     │
  │                          │── osascript ─────────▶
  │◀── 200 OK ───────────────│                      │
```

---

## Key Design Concepts

### Interrupts as the user input mechanism

Rather than polling or websockets, the app uses LangGraph's `interrupt()` primitive. When a node calls `interrupt(value=payload)`, LangGraph:

1. Saves the full graph state to the checkpointer.
2. Raises an internal exception that bubbles up through `astream_events`.
3. The server catches this, inspects the payload, and emits the appropriate SSE event.
4. The SSE stream ends.

When the user responds, the browser POSTs to `/resume`. The server loads the graph from its checkpoint and calls `graph.astream_events(Command(resume=user_input), ...)`, which picks up exactly where it left off.

This means the server is stateless between interrupt and resume — all state lives in PostgreSQL.

### SSE rather than WebSockets

Server-Sent Events (SSE) are unidirectional (server → browser) and work over plain HTTP/1.1. They are simpler to implement and proxy than WebSockets. Because user input is infrequent (three interrupts per session), a separate POST for each resume is clean and easy to reason about. The browser never needs to maintain a long-lived bidirectional connection.

### Structured LLM output

Every LLM call uses `with_structured_output(PydanticModel)`. This forces the model to return JSON conforming to the schema rather than free text. Benefits:

- No regex or string parsing of LLM output
- Type safety throughout the graph state
- Predictable failure modes (the call raises if the schema is violated)

### Singleton services

`backend/nodes/base.py` initialises the LLM client, DuckDuckGo search tool, and HTTP client once and reuses them. This avoids repeatedly re-reading environment variables and re-establishing connections on every node invocation.

---

## Data Models

Defined in `backend/models.py`.

### `MealPlannerState`

The single TypedDict that flows through the entire graph. Nodes read fields they care about and return a partial dict with only the fields they update. LangGraph merges these partials into the running state.

| Field | Type | Set by |
|---|---|---|
| `cuisine_type` | `str` | Initial input |
| `direct_url` | `Optional[str]` | Initial input |
| `search_results` | `Optional[str]` | `search_meals` |
| `meal_options` | `Optional[List[MealOption]]` | `parse_meals` |
| `refine_dishes` | `Optional[List[str]]` | `validate_recipes` |
| `selected_meal` | `Optional[MealOption]` | `present_options` (post-interrupt) |
| `grocery_list` | `Optional[List[Ingredient]]` | `extract_ingredients` |
| `messages` | `List` | All LLM-calling nodes |
| `refinement_count` | `int` | `validate_recipes` |
| `reminders_added` | `Optional[bool]` | `add_to_reminders` |
| `error` | `Optional[str]` | Any node on failure |

### `Ingredient`

```python
name:   str   # "chicken breast"
amount: str   # "2", "1/2", ""
unit:   str   # "cups", "lbs", ""
```

### `MealOption`

```python
id:          int
name:        str    # "Chicken Tikka Masala"
description: str
recipe_url:  str
```

---

## Ingredient Collation

**`backend/collate.py`**

Before writing to Reminders, the app reads the current contents of the target list and merges the new ingredients with what's already there. This prevents duplicate entries when planning multiple meals.

The algorithm:

1. **Normalize names**: lowercase, strip whitespace, basic singularization (`eggs` → `egg`).
2. **Parse existing reminders**: Reminder texts are stored as `"chicken breast (2 lbs)"`. The parser extracts name, amount, and unit.
3. **Match**: For each new ingredient, check whether a normalized version exists in the current list.
4. **Combine amounts**:
   - Same unit → add numerically: `3 eggs + 2 eggs = 5 eggs`
   - Different units → concatenate: `2 cups olive oil + 1 tbsp olive oil = 2 cups + 1 tbsp`
5. **Output**:
   - `items_to_add` — ingredients with no existing match (new reminders)
   - `items_to_update` — `(old_text, combined_Ingredient)` pairs (delete old, create combined)

The node batch-deletes all `items_to_update` in one AppleScript call, then creates each new/updated reminder individually.

---

## Running the App

### Prerequisites

- Docker Desktop
- Node.js 18+
- Python 3.11 (on Mac host, for the proxy)
- macOS Reminders access granted to Python

### Start everything

```bash
make start-all
```

This:
1. Builds the Docker image
2. Starts PostgreSQL and the FastAPI server in Docker
3. Starts the Reminders proxy on the Mac host (port 8765)
4. Starts the Vite dev server in the background (port 3000)

Logs are written to `proxy.log` and `frontend.log` in the project root.

Open [http://localhost:3000](http://localhost:3000).

### Stop everything

```bash
make stop-all
```

### Individual services

```bash
make proxy        # Mac host: Reminders proxy on :8765
make docker-up    # Docker: FastAPI on :8000 + PostgreSQL on :5433
make docker-shell # Shell into the running container
```

### Local development (no Docker)

```bash
make run-local
```

Runs the LangGraph workflow as a CLI. Uses `MemorySaver` instead of PostgreSQL. Prompts appear in the terminal. Useful for testing graph logic without the full stack.

---

## Environment Variables

Place these in a `.env` file in the project root:

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `CLI_MODE` | No | `false` | Enables terminal output for local dev; suppressed in web mode |
| `REMINDERS_PROXY_PORT` | No | `8765` | Port the proxy listens on |
| `DATABASE_URL` | No | — | PostgreSQL connection string; falls back to MemorySaver if unset |

The Docker container also receives:
- `REMINDERS_PROXY_URL=http://host.docker.internal:8765` (set in `docker-compose.yml`)
- `DATABASE_URL=postgresql://mealplanner:mealplanner@postgres:5432/mealplanner`

---

## Project Structure

```
grocery_shopping/
│
├── backend/
│   ├── meal_planner.py         # LangGraph graph builder + checkpointer init
│   ├── meal_planner_server.py  # FastAPI server: sessions, SSE, interrupt handling
│   ├── reminders_server.py     # HTTP proxy: REST → AppleScript (runs on Mac host)
│   ├── reminders.py            # Reminders abstraction (proxy or direct osascript)
│   ├── models.py               # Pydantic models: MealPlannerState, Ingredient, MealOption
│   ├── prompts.py              # LLM prompt templates
│   ├── collate.py              # Smart ingredient merging logic
│   └── ui.py                   # CLI output helpers (gated on CLI_MODE)
│
│   ├── nodes/
│   │   ├── __init__.py         # Re-exports all nodes
│   │   ├── base.py             # LLM, search tool, HTTP client singletons
│   │   ├── html_utils.py       # JSON-LD and BeautifulSoup text extraction
│   │   ├── routing.py          # Conditional edge functions
│   │   ├── search.py           # search_meals, parse_meals, validate_recipes, refine_search
│   │   ├── processing.py       # create_meal_from_url, present_options, extract_ingredients, review_ingredients
│   │   └── reminders_node.py   # add_to_reminders
│   │
│   └── server/
│       ├── __init__.py
│       ├── sse.py              # SSE event factory and serialisation helpers
│       └── interrupts.py       # Interrupt type detection registry
│
├── frontend/
│   └── src/
│       ├── App.jsx             # Root component, SSE event handling, stage routing
│       ├── config.js           # Default recipe source sites
│       ├── main.jsx            # React entry point
│       └── components/
│           ├── CuisineInput.jsx
│           ├── MealSelection.jsx
│           ├── IngredientReview.jsx
│           ├── RemindersPrompt.jsx
│           ├── CompletionScreen.jsx
│           └── StatusDisplay.jsx
│
├── docker/
│   ├── Dockerfile              # python:3.11-slim, installs deps, mounts backend/
│   └── docker-compose.yml      # meal-planner (port 8000) + postgres (port 5433)
│
├── docs/
│   └── graph-architecture.md   # Mermaid diagrams of the full LangGraph structure
│
├── Makefile                    # start-all, stop-all, proxy, docker-up, etc.
├── CLAUDE.md                   # Claude Code project instructions
└── README.md                   # This file
```
