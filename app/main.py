import os
import sys

# Ensure project root is on sys.path when running the script directly
if os.path.basename(sys.path[0]) == "app":
    sys.path.insert(0, os.path.dirname(sys.path[0]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.routes import sticker, user, device, auth, bundle, story
from app.db.init_db import init_db

app = FastAPI(title=settings.PROJECT_NAME)

# Ensure storage directory exists and mount for static asset downloads
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint for cloud load balancers and monitoring."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.on_event("startup")
def startup():
    init_db()


app.include_router(sticker.router, prefix="")
app.include_router(user.router, prefix="")
app.include_router(device.router, prefix="")
app.include_router(auth.router, prefix="")
app.include_router(bundle.router, prefix="")
app.include_router(story.router, prefix="")


if __name__ == "__main__":
    # Allow running the app module directly for convenience in development.
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
