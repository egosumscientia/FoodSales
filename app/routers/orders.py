# app/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.storage.db import get_db
from app.storage.models import Order
from app.storage.sync_relational import sync_order_to_relational  # <-- Nuevo import
from datetime import datetime
from app.storage.order_serial import next_order_serial

router = APIRouter(prefix="/orders", tags=["Orders"])


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
        status = order_data.get("status", "pending")

        if not user_id or not items:
            raise HTTPException(
                status_code=400,
                detail="Faltan campos obligatorios: user_id o items."
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
