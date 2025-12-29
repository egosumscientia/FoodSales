# FoodSales – Asistente de ventas y dashboard

Asistente conversacional (FastAPI) que cotiza, gestiona carrito y órdenes con NLP en español. Usa PostgreSQL para órdenes, Redis para carrito (fallback en memoria) y ofrece una UI ligera para el agente y un dashboard con gráficos.

## Objetivo y descripción
- Responder consultas de productos/precios, armar carrito y confirmar órdenes.
- Detección NLP de productos con sinónimos, cantidades y guardrails contra falsos positivos.
- Escalamiento automático por insultos/ironías o reclamos detectados.
- Dashboard de reportes con gráfico de barras de ventas por producto (Chart.js) y tablas exportables a CSV.

## Requisitos
- Python 3.11+
- PostgreSQL (DB `foodsalesdb`, usuario `fooduser`/`123` en local por defecto)
- Redis (si no está disponible, el carrito cae a memoria; instalar `redis-server` es recomendable)

## Instalación
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

## Arrancar servicios base
- PostgreSQL: levantar servicio y crear DB `foodsalesdb` (usuario `fooduser`, pass `123` o ajusta `DATABASE_URL`).
- Redis: `redis-server` (opcional, pero recomendado); verificar con `redis-cli PING`.

## Ejecutar la API
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Interfaces disponibles
- Docs Swagger: http://127.0.0.1:8000/docs
- UI del agente (chat + carrito): http://127.0.0.1:8000/static/agent.html
- Dashboard de reportes (tabs Resumen/Ventas/Detalle + gráfico de barras): http://127.0.0.1:8000/static/dashboard.html

## Flujo principal
1) El usuario pide productos: se detectan cantidades y sinónimos y se añaden al carrito (`CartService` via Redis/memoria).
2) Consultas de precio/ventas: se responden y se actualiza carrito.
3) Confirmar pedido: envía items a `/orders/` y limpia carrito.
4) Escalamiento: insultos/ironías o reclamos → `should_escalate=True` y derivación humana.

## Detalles técnicos clave
- NLP: `app/core/nlp_rules.py` con sinónimos enriquecidos cacheados, extracción multiproducto y guardrails de similitud.
- Escalamiento: `app/core/escalation.py` con vocabulario de reclamos, sarcasmo/ironía e insultos (se fuerza escalamiento).
- Carrito: `app/core/carts/service.py` con fallback en memoria si Redis no responde; persistencia en Redis si está disponible.
- Órdenes: `app/routers/orders.py` con máquina de estados básica (pending→confirmed→…→delivered/cancelled/escalated).
- Dashboard: `app/static/dashboard.html` usa Chart.js desde CDN; gráfico de barras para ventas por producto y exportación CSV.
- UI del agente: `app/static/agent.html` con estilo moderno (Manrope), burbujas, acciones rápidas y botones ordenados.

## Datos y archivos
- Catálogo: `app/data/Catalog.csv`
- Sinónimos: `app/data/synonyms.json`
- FAQ y respuestas: `app/data/faq.json`

## Tips de despliegue
- Ajusta `DATABASE_URL`/`REDIS_URL` según entorno.
- En producción, desactiva `--reload` y usa un servidor ASGI (gunicorn/uvicorn workers).
- Asegura que Redis esté accesible o valida el fallback en memoria si es un entorno sin cache.

## Exportar reportes
- En el dashboard, botón “Exportar CSV” genera un archivo con todas las secciones disponibles (resumen, ventas, detalle).
