# app/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.storage.db import get_db
from app.storage.models import Order
from app.storage.sync_relational import sync_order_to_relational  # <-- Nuevo import
from datetime import datetime
from app.storage.order_serial import next_order_serial
from typing import Optional

router = APIRouter(prefix="/orders", tags=["Orders"])

ALLOWED_STATUSES = {
    "pending",
    "confirmed",
    "preparing",
    "ready",
    "shipped",
    "delivered",
    "cancelled",
    "escalated",
}

# Estado -> set de estados permitidos como siguiente paso
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled", "escalated"},
    "confirmed": {"preparing", "cancelled", "escalated"},
    "preparing": {"ready", "cancelled", "escalated"},
    "ready": {"shipped", "delivered", "escalated"},
    "shipped": {"delivered", "escalated"},
    "delivered": set(),
    "cancelled": set(),
    "escalated": set(),
}


def _normalize_status(status: Optional[str]) -> str:
    return (status or "pending").strip().lower()


def _can_transition(current: str, target: str) -> bool:
    current_n = _normalize_status(current)
    target_n = _normalize_status(target)
    if target_n not in ALLOWED_STATUSES:
        return False
    # Si no hay regla explícita, se permite cualquier avance (fallback seguro)
    if current_n not in ALLOWED_TRANSITIONS:
        return True
    return target_n in ALLOWED_TRANSITIONS[current_n]


@router.post("/")
def create_order(order_data: dict, db: Session = Depends(get_db)):
    """
    Inserta una nueva orden en la base de datos.
    Calcula el total automáticamente a partir de los items.
    Además, sincroniza las tablas relacionales (customers, products, order_items).
    """
    try:
        user_id = order_data.get("user_id")
        items = order_data.get("items", [])
        status = _normalize_status(order_data.get("status", "pending"))

        if not user_id or not items:
            raise HTTPException(
                status_code=400,
                detail="Faltan campos obligatorios: user_id o items."
            )

        if status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Estado no permitido. Usa uno de: {', '.join(sorted(ALLOWED_STATUSES))}"
            )

        # Calcular total automáticamente
        total = sum(
            float(item.get("cantidad", 0)) * float(item.get("precio_unitario", 0))
            for item in items
        )

        from app.storage.order_serial import next_order_serial
        serial = next_order_serial()

        # Crear la orden principal
        new_order = Order(
            user_id=user_id,
            items=items,
            total=total,
            status=status,
            order_serial=serial,
            created_at=datetime.utcnow()
        )

        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # === NUEVO: sincronización relacional ===
        try:
            sync_order_to_relational(db, new_order)
        except Exception as sync_err:
            # No rompemos la creación de la orden si falla la sincronización
            print(f"⚠️ Error sincronizando la orden {new_order.id}: {sync_err}")

        return {
            "message": "Orden creada correctamente",
            "order_id": new_order.id,
            "order_serial": new_order.order_serial, 
            "total": total,
            "items": items
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_orders(db: Session = Depends(get_db)):
    """
    Lista todas las órdenes almacenadas en la base de datos.
    """
    orders = db.query(Order).all()
    return {"total_orders": len(orders), "orders": orders}




@router.get("/status")
def get_order_status(
    user_id: str | None = None,
    order_serial: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Consulta el estado de las ordenes de un usuario (para sesiones posteriores).
    - Si envias order_serial, devuelve solo esa orden.
    - Si no, devuelve todas las ordenes del usuario.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="Debes enviar user_id.")

    q = db.query(Order).filter(Order.user_id == user_id)
    if order_serial:
        q = q.filter(Order.order_serial == order_serial)
    orders = q.order_by(Order.id.desc()).all()

    return {
        "total_orders": len(orders),
        "orders": orders,
    }


@router.put("/{order_id}/status")
def update_order_status(order_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    Actualiza el estado de una orden validando una m·lima m quina de estados.
    Estados permitidos: pending, confirmed, preparing, ready, shipped, delivered, cancelled, escalated.
    """
    new_status = _normalize_status(payload.get("status"))
    if not new_status:
        raise HTTPException(status_code=400, detail="Debes enviar el campo 'status'.")
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no permitido. Usa uno de: {', '.join(sorted(ALLOWED_STATUSES))}",
        )

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    current_status = _normalize_status(order.status)
    if not _can_transition(current_status, new_status):
        raise HTTPException(
            status_code=400,
            detail=f"Transición inválida: {current_status} -> {new_status}",
        )

    order.status = new_status
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "Estado actualizado",
        "order_id": order.id,
        "order_serial": order.order_serial,
        "status": order.status,
        "total": order.total,
    }




@router.post("/escalate")
def escalate_order(payload: dict, db: Session = Depends(get_db)):
    """
    Marca una orden para escalamiento humano (detalle o reclamo).
    Requiere user_id; opcional order_serial para elegir una orden especifica.
    """
    user_id = payload.get("user_id")
    order_serial = payload.get("order_serial")
    motivo = payload.get("motivo", "detalle")

    if not user_id:
        raise HTTPException(status_code=400, detail="Debes enviar user_id.")

    q = db.query(Order).filter(Order.user_id == user_id)
    if order_serial:
        q = q.filter(Order.order_serial == order_serial)
    order = q.order_by(Order.id.desc()).first()

    if not order:
        raise HTTPException(status_code=404, detail="No se encontro una orden para este usuario.")

    # Evitar re-escalar la misma orden
    if (order.status or "").lower() == "escalated":
        return {
            "message": "Esta orden ya fue escalada. Un asesor humano se comunicara en menos de 24 horas.",
            "should_escalate": False,
            "summary": {
                "order_id": order.id,
                "order_serial": order.order_serial,
                "status": order.status,
            },
        }

    # Marcar como escalada
    order.status = "escalated"
    db.add(order)
    db.commit()
    db.refresh(order)

    summary = {
        "order_id": order.id,
        "order_serial": order.order_serial,
        "total": order.total,
        "status": order.status,
        "created_at": order.created_at,
        "items": order.items,
        "motivo": motivo,
        "user_id": user_id,
    }

    return {
        "message": "Orden escalada a soporte humano. Un asesor te contactara en menos de 24 horas.",
        "should_escalate": True,
        "summary": summary,
    }
