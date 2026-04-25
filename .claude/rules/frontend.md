---
paths:
  - "frontend/**/*"
---

# Frontend Reference

## App Modes (`App.jsx`)

`mode` state: `home` | `meal_plan` | `usuals` | `reorder` | `weekly_planner`

## Components

| Component | Purpose |
|-----------|---------|
| `CuisineInput` | Input form for cuisine type or recipe URL |
| `MealSelection` | Recipe selection UI (after search) |
| `IngredientReview` | Ingredient modification UI |
| `RemindersPrompt` | Confirm adding to Reminders |
| `CompletionScreen` | Success screen after adding groceries |
| `StatusDisplay` | Streaming status messages |
| `HomeScreen` | Landing/home view |
| `UsualsList` | Manage usual grocery items |
| `ReorderReminders` | Trigger LLM reorder of a Reminders list |
| `WeeklyPlanner` | Weekly meal planner with accordion view by week |

## SSE Event Handling

Frontend connects to `/api/plan` (start) or `/api/sessions/{id}/resume` (continue after interrupt) and handles these event types:

`session_start`, `status`, `meal_options`, `ingredient_review`, `reminders_prompt`, `grocery_list`, `complete`, `error`

## Dev Setup

```bash
cd frontend && npm run dev
```

Frontend proxies `/api/*` → `http://localhost:8000` via Vite config.
