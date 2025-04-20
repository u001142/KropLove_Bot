from app.routers.start_router import router as start_router
from app.routers.profile_router import router as profile_router
from app.routers.like_router import router as like_router
from app.routers.chat_router import router as chat_router
from app.routers.premium_router import router as premium_router

all_routers = [
    start_router,
    profile_router,
    like_router,
    chat_router,
    premium_router
]
