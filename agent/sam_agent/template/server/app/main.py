from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health_check import router
from app.db.session import lifespan

def create_app() -> FastAPI:
    app = FastAPI(title="AI Agent Service", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:80", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app

# Create the ASGI app instance
app = create_app()