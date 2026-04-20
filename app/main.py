import os
import sys

# Ensure project root is on sys.path when running the script directly
if os.path.basename(sys.path[0]) == "app":
    sys.path.insert(0, os.path.dirname(sys.path[0]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sticker, user, device, auth, bundle
from app.db.init_db import init_db

app = FastAPI(title="WonderBox Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(sticker.router, prefix="")
app.include_router(user.router, prefix="")
app.include_router(device.router, prefix="")
app.include_router(auth.router, prefix="")
app.include_router(bundle.router, prefix="")


if __name__ == "__main__":
    # Allow running the app module directly for convenience in development.
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
