from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import settings
from app.db import engine, init_db
from app.routers import applications, auth, demo, me, specialist
from app.seed import ensure_demo_queue, seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_if_empty(session)
        ensure_demo_queue(session)
    yield


app = FastAPI(
    title="Умный кредитный кабинет предпринимателя",
    description="Цифровой кредитный конвейер для действующих клиентов малого и микробизнеса.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(specialist.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
