from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import chat, health, orders, reports
from app.storage import models  # noqa: F401  # Mantener import para registrar modelos
from app.storage.db import Base, engine


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se ejecuta al iniciar la app
    Base.metadata.create_all(bind=engine)
    print("[startup] Base de datos inicializada y tablas creadas (si no existen).")
    yield
    # Al apagar la app
    print("[shutdown] App finalizada correctamente.")


# --- Inicializacion de la app ---
app = FastAPI(
    title="Food Sales Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Routers ---
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(orders.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    return {"message": "API del Asistente de Ventas en linea"}
