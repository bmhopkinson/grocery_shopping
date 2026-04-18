# Grocery Shopping Meal Planner

AI-powered meal planning app that searches recipes, extracts ingredients, and adds them to Apple Reminders.

## Quick Start

```bash
# Start all services (proxy + Docker + frontend)
make start-all

# Or manually:
make proxy        # Terminal 1: reminders proxy on Mac
make docker-up    # Terminal 2: backend container
cd frontend && npm run dev  # Terminal 3: frontend
```

## Architecture

- **Backend**: Python 3.11, FastAPI, LangGraph (agentic workflow with interrupts)
- **Frontend**: React 18, Vite, Material-UI
- **LLM**: OpenAI GPT-5.2 via LangChain
- **Database**: PostgreSQL 16 (LangGraph checkpointer for session persistence)
- **Communication**: Server-Sent Events (SSE) for real-time streaming

## Project Structure

```
src/
  meal_planner.py         # Main orchestrator, LangGraph workflow builder
  meal_planner_server.py  # FastAPI server with SSE streaming
  models.py               # Pydantic data models (Recipe, Ingredient, MealPlannerState)
  prompts.py              # LLM prompt templates
  reminders_server.py     # HTTP proxy for AppleScript (runs on Mac host)
  reminders.py            # Reminders API abstraction
  collate.py              # Smart ingredient merging logic
  ui.py                   # CLI output formatting

  nodes/                  # Graph node implementations
    __init__.py           # Re-exports all nodes
    base.py               # Shared LLM, search tool, HTTP client
    html_utils.py         # JSON-LD and text extraction
    routing.py            # Conditional edge functions
    search.py             # Search flow nodes
    processing.py         # Processing and interrupt nodes
    reminders_node.py     # Apple Reminders integration

  server/                 # Server components
    __init__.py           # Re-exports
    sse.py                # SSE event factory and serialization
    interrupts.py         # Interrupt type registry and handlers

frontend/src/
  App.jsx                 # Main component, SSE event handling
  CuisineInput.jsx        # Input form for cuisine/URL
  MealSelection.jsx       # Recipe selection UI
  IngredientReview.jsx    # Ingredient modification UI

docker/
  Dockerfile              # Python 3.11-slim container
  docker-compose.yml      # Service orchestration

docs/
  graph-architecture.md   # Mermaid diagrams of graph structure and state
```

## Key Commands

```bash
make help          # Show all commands
make proxy         # Start reminders proxy (required on Mac host)
make docker-up     # Build and start Docker container
make docker-down   # Stop container
make docker-shell  # Exec into container
make run-local     # Run without Docker
make start-all     # Start everything (proxy, Docker, frontend)
make stop-all      # Stop everything
```

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - OpenAI API key
- `CLI_MODE` - Set to enable CLI mode vs web server
- `REMINDERS_PROXY_PORT` - Port for reminders proxy (default 8765)

## Workflow

1. User enters cuisine type or recipe URL
2. If search: DuckDuckGo search → LLM parses → validates URLs
3. **Interrupt**: User selects a recipe
4. LLM extracts ingredients from recipe HTML
5. **Interrupt**: User reviews/modifies ingredients
6. Smart collation with existing reminders
7. Items added to Apple Reminders "Groceries" list

## Development Notes

- Backend runs on port 8000, frontend proxies `/api` requests
- PostgreSQL runs on port 5432 (persists LangGraph checkpoints)
- Reminders proxy (port 8765) must run on Mac host for AppleScript access
- Falls back to MemorySaver if `DATABASE_URL` not set (for local dev without Docker)
- SSE endpoints: `/api/plan` (start), `/api/resume` (continue after interrupt)

## Testing

```bash
# In Docker container
python -m pytest src/test_meal_planner_server.py
```

---

## API Reference (for future Claude sessions — no re-exploration needed)

### Reminders Proxy (`reminders_server.py`) — port 8765

| Method | Path | Body / Params | Response |
|--------|------|---------------|----------|
| POST | `/reminder` | `{list_name, reminder_text}` | `{success: bool}` |
| POST | `/lists` | `{list_name}` | `{success: bool}` |
| GET | `/lists` | — | `{lists: [str]}` |
| GET | `/lists/{list_name}/exists` | — | `{exists: bool}` |
| GET | `/lists/{list_name}/items` | — | `{items: [str]}` |
| DELETE | `/reminder` | `{list_name, reminder_text}` | `{success: bool}` |
| DELETE | `/reminders/batch` | `{list_name, reminder_texts: [str]}` | `{success: bool}` |
| GET | `/health` | — | `{status, reminders_accessible, default_list, error}` |

### Reminders Client (`reminders.py`) — functions

```python
create_reminder(list_name, reminder_text) -> bool
list_exists(list_name) -> bool
create_list(list_name) -> bool
get_all_lists() -> list[str]
get_reminders(list_name) -> list[str]   # returns raw reminder texts e.g. "eggs (3 large)"
delete_reminder(list_name, reminder_text) -> bool
delete_reminders_batch(list_name, reminder_texts) -> bool
```

Dual mode: uses `REMINDERS_PROXY_URL` env var (HTTP to proxy) or direct PyObjC EventKit.

### Meal Planner API (`meal_planner_server.py`) — port 8000

| Method | Path | Notes |
|--------|------|-------|
| POST | `/plan` | SSE stream; body: `{cuisine_type, direct_url, preferred_sources}` |
| POST | `/sessions/{id}/resume` | SSE stream; body: `{input: str\|dict}` |
| GET | `/sessions/{id}` | Debug state |
| DELETE | `/sessions/{id}` | — |
| GET | `/reminder-lists` | Returns `{lists: [str]}` |
| POST | `/reorder-reminders` | Body: `{list_name}`; fetches list, LLM-reorders by store layout, rewrites; returns `{list_name, reordered_items, count}` |
| GET | `/usuals` | — |
| POST | `/usuals` | `{name, category?}` |
| PUT | `/usuals/{id}` | `{name, category?}` |
| DELETE | `/usuals/{id}` | — |
| POST | `/usuals/add-to-reminders` | `{usual_ids: [str], list_name}` |
| GET | `/health` | `{status, active_sessions}` |

### SSE Event Types (from `/plan` and `/sessions/{id}/resume`)

`session_start`, `status`, `meal_options`, `ingredient_review`, `reminders_prompt`, `grocery_list`, `complete`, `error`

### Key Models (`models.py`)

```python
Ingredient(name, amount, unit)          # e.g. name="eggs", amount="3", unit="large"
MealOption(id, name, description, recipe_url)
Recipe(name, description, url)
MealPlannerState(TypedDict)             # full graph state
```

Reminder text format: `"name (amount unit)"` or `"name (amount)"` — parsed/formatted by `collate.py`.

### Frontend Modes (`App.jsx`)

`mode` state: `home` | `meal_plan` | `usuals` | `reorder`

Components: `CuisineInput`, `MealSelection`, `IngredientReview`, `RemindersPrompt`, `CompletionScreen`, `StatusDisplay`, `HomeScreen`, `UsualsList`, `ReorderReminders`

Frontend proxies `/api/*` → `http://localhost:8000` via Vite config.

### LLM Access (`nodes/base.py`)

```python
get_llm() -> ChatOpenAI(model="gpt-5.2", temperature=0)
invoke_structured(output_model, prompt) -> T   # structured output via with_structured_output
```

Use `await llm.ainvoke([HumanMessage(content=prompt)])` for async calls in server endpoints.

### Store Section Order (for reorder feature)

`produce → meat → canned and dry goods → snacks → dairy → frozen → beer and wine → paper items`
Defined as `STORE_SECTION_ORDER` list in `meal_planner_server.py`.
