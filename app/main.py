from fastapi import FastAPI
from app.routers import chat, health, orders

# 🔹 Importar capa de persistencia
from app.storage.db import Base, engine
from app.storage import models  # noqa: F401  # Mantener import para registrar modelos

from contextlib import asynccontextmanager
from app.routers import reports
from fastapi.staticfiles import StaticFiles

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔹 Se ejecuta al iniciar la app
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada y tablas creadas (si no existían).")
    yield
    # 🔹 (opcional) Al apagar la app
    print("👋 App finalizada correctamente.")

# --- Inicialización de la app ---
app = FastAPI(
    title="Food Sales Agent API",
    version="1.0.0",
    lifespan=lifespan,  # ✅ importante
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Routers ---
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(orders.router)
app.include_router(reports.router)

@app.get("/")
async def root():
    return {"message": "API del Asistente de Ventas en línea ✅"}
