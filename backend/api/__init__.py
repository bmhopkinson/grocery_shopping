from api.planning.router import router as planning_router
from api.recipes.router import router as recipes_router
from api.groups.router import router as groups_router
from api.lists.router import router as lists_router
from api.reminders.router import router as reminders_router
from api.usuals.router import router as usuals_router
from api.weekly.router import router as weekly_router
from api.data_transfer.router import router as data_transfer_router

all_routers = [
    planning_router,
    recipes_router,
    groups_router,
    lists_router,
    reminders_router,
    usuals_router,
    weekly_router,
    data_transfer_router,
]
