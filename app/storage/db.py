# app/storage/db.py
from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# === CONFIGURACIÓN: conexión a PostgreSQL ===
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://fooduser:123@localhost:5432/foodsalesdb"
)

# === ENGINE ===
engine = create_engine(
    DATABASE_URL,
    echo=False,          # Cambia a True para ver el SQL en consola
    future=True,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
)

# === BASE ORM ===
class Base(DeclarativeBase):
    """Clase base para los modelos ORM."""
    pass

# === SESIÓN ===
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# === DEPENDENCIA PARA FASTAPI ===
def get_db() -> Generator:
    """Genera una sesión por request (para inyección en FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# === CONTEXTO OPCIONAL ===
@contextmanager
def session_scope():
    """Contexto transaccional (para scripts/tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
