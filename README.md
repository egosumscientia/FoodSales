# Food Sales Agent API

API en FastAPI para el asistente de ventas. Usa PostgreSQL para persistencia y Redis para carrito (con fallback en memoria solo para desarrollo).

## Requisitos
- Python 3.11+
- PostgreSQL en localhost con DB `foodsalesdb` y usuario `fooduser`/`123`
- Redis instalado y en PATH (en Windows puedes correr `redis-server` directamente)

## Instalacion
```powershell
cd D:\Documentos\FoodSales
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Variables de entorno
```powershell
set DATABASE_URL=postgresql+psycopg://fooduser:123@localhost:5432/foodsalesdb
set REDIS_URL=redis://localhost:6379/0
```

## Arrancar servicios
- PostgreSQL: servicio levantado y base creada.
- Redis (PowerShell, ya en PATH):
  - Servidor: `redis-server`
  - Verificar: `redis-cli PING` (debe responder `PONG`)

## Ejecutar la API
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Uso rapido
- Documentacion interactiva: http://127.0.0.1:8000/docs
- GUI del agente: http://127.0.0.1:8000/static/agent.html
