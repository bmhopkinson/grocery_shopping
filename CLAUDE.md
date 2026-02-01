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
  nodes.py                # Graph node implementations (search, validate, extract)
  models.py               # Pydantic data models (Recipe, Ingredient, MealPlannerState)
  reminders_server.py     # HTTP proxy for AppleScript (runs on Mac host)
  reminders.py            # Reminders API abstraction
  prompts.py              # LLM prompt templates
  collate.py              # Smart ingredient merging logic
frontend/src/
  App.jsx                 # Main component, SSE event handling
  CuisineInput.jsx        # Input form for cuisine/URL
  MealSelection.jsx       # Recipe selection UI
  IngredientReview.jsx    # Ingredient modification UI
docker/
  Dockerfile              # Python 3.11-slim container
  docker-compose.yml      # Service orchestration
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
