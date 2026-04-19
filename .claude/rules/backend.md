---
paths:
  - "src/**/*"
---

# Backend Reference

## Reminders Proxy (`reminders_server.py`) — port 8765

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

## Reminders Client (`reminders.py`)

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

## Meal Planner API (`meal_planner_server.py`) — port 8000

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

## SSE Event Types (from `/plan` and `/sessions/{id}/resume`)

`session_start`, `status`, `meal_options`, `ingredient_review`, `reminders_prompt`, `grocery_list`, `complete`, `error`

## Key Models (`models.py`)

```python
Ingredient(name, amount, unit)          # e.g. name="eggs", amount="3", unit="large"
MealOption(id, name, description, recipe_url)
Recipe(name, description, url)
MealPlannerState(TypedDict)             # full graph state
```

Reminder text format: `"name (amount unit)"` or `"name (amount)"` — parsed/formatted by `collate.py`.

## LLM Access (`nodes/base.py`)

```python
get_llm() -> ChatOpenAI(model="gpt-5.2", temperature=0)
invoke_structured(output_model, prompt) -> T   # structured output via with_structured_output
```

Use `await llm.ainvoke([HumanMessage(content=prompt)])` for async calls in server endpoints.

## Store Section Order (for reorder feature)

`produce → meat → canned and dry goods → snacks → dairy → frozen → beer and wine → paper items`
Defined as `STORE_SECTION_ORDER` list in `meal_planner_server.py`.
