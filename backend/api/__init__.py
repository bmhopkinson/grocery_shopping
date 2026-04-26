from api.planning.router import router as planning_router
from api.recipes.router import router as recipes_router
from api.lists.router import router as lists_router
from api.reminders.router import router as reminders_router
from api.usuals.router import router as usuals_router
from api.weekly.router import router as weekly_router

all_routers = [
    planning_router,
    recipes_router,
    lists_router,
    reminders_router,
    usuals_router,
    weekly_router,
]
