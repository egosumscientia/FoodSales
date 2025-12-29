# app/routers/reports.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.storage import models, db
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["Reports"])

def _filter_dates(query, model, desde, hasta):
    if desde:
        try:
            fecha_desde = datetime.fromisoformat(desde)
            query = query.filter(model.created_at >= fecha_desde)
        except ValueError:
            pass
    if hasta:
        try:
            fecha_hasta = datetime.fromisoformat(hasta)
            query = query.filter(model.created_at <= fecha_hasta)
        except ValueError:
            pass
    return query


# === 1. Resumen por cliente ===
@router.get("/order_summary")
def order_summary(
    cliente: str | None = Query(None),
    producto: str | None = Query(None),
    orden_id: int | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    db: Session = Depends(db.get_db),
):
    q = (
        db.query(
            models.Customer.user_id.label("cliente"),
            func.count(models.Order.id).label("num_ordenes"),
            func.sum(models.Order.total).label("total_comprado"),
        )
        .join(models.Order, models.Customer.id == models.Order.customer_id)
        .group_by(models.Customer.user_id)
        .order_by(func.sum(models.Order.total).desc())
    )

    if cliente:
        q = q.filter(models.Customer.user_id == cliente)
    if orden_id:
        q = q.filter(models.Order.id == orden_id)

    q = _filter_dates(q, models.Order, desde, hasta)
    results = q.all()
    return [dict(r._mapping) for r in results]


# === 2. Detalle completo de órdenes ===
@router.get("/order_full_detail")
def order_full_detail(
    cliente: str | None = Query(None),
    producto: str | None = Query(None),
    orden_id: int | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    db: Session = Depends(db.get_db),
):
    q = (
        db.query(
            models.Order.id.label("orden_id"),
            models.Customer.user_id.label("cliente"),
            models.Product.name.label("producto"),
            models.OrderItem.quantity.label("cantidad"),
            models.OrderItem.price.label("precio_unitario"),
            (models.OrderItem.quantity * models.OrderItem.price).label("subtotal"),
            models.Order.total.label("total_orden"),
            models.Order.created_at.label("fecha"),
        )
        .join(models.Customer, models.Customer.id == models.Order.customer_id)
        .join(models.OrderItem, models.OrderItem.order_id == models.Order.id)
        .join(models.Product, models.Product.id == models.OrderItem.product_id)
        .order_by(models.Order.id)
    )

    if cliente:
        q = q.filter(models.Customer.user_id == cliente)
    if producto:
        q = q.filter(models.Product.name == producto)
    if orden_id:
        q = q.filter(models.Order.id == orden_id)

    q = _filter_dates(q, models.Order, desde, hasta)
    results = q.all()
    return [dict(r._mapping) for r in results]


# === 3. Ventas por producto ===
@router.get("/sales_by_product")
def sales_by_product(
    cliente: str | None = Query(None),
    producto: str | None = Query(None),
    orden_id: int | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    db: Session = Depends(db.get_db),
):
    q = (
        db.query(
            models.Product.name.label("producto"),
            func.sum(models.OrderItem.quantity).label("total_unidades"),
            func.sum(models.OrderItem.quantity * models.OrderItem.price).label("total_ventas"),
        )
        .join(models.OrderItem, models.Product.id == models.OrderItem.product_id)
        .join(models.Order, models.Order.id == models.OrderItem.order_id)
        .group_by(models.Product.name)
        .order_by(func.sum(models.OrderItem.quantity * models.OrderItem.price).desc())
    )

    if producto:
        q = q.filter(models.Product.name == producto)
    if cliente:
        q = q.join(models.Customer, models.Customer.id == models.Order.customer_id)\
             .filter(models.Customer.user_id == cliente)
    if orden_id:
        q = q.filter(models.Order.id == orden_id)

    q = _filter_dates(q, models.Order, desde, hasta)
    results = q.all()
    return [dict(r._mapping) for r in results]


# === 4. Consolidado de todos los reportes ===
@router.get("/summary_all")
def summary_all(
    cliente: str | None = Query(None),
    producto: str | None = Query(None),
    orden_id: int | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    db: Session = Depends(db.get_db),
):
    # --- Reutilizar las consultas existentes ---

    # 1️⃣ Resumen por cliente
    q1 = (
        db.query(
            models.Customer.user_id.label("cliente"),
            func.count(models.Order.id).label("num_ordenes"),
            func.sum(models.Order.total).label("total_comprado"),
        )
        .join(models.Order, models.Customer.id == models.Order.customer_id)
        .group_by(models.Customer.user_id)
    )
    if cliente:
        q1 = q1.filter(models.Customer.user_id == cliente)
    if orden_id:
        q1 = q1.filter(models.Order.id == orden_id)
    q1 = _filter_dates(q1, models.Order, desde, hasta)
    resumen_clientes = [dict(r._mapping) for r in q1.all()]

    # 2️⃣ Ventas por producto
    q2 = (
        db.query(
            models.Product.name.label("producto"),
            func.sum(models.OrderItem.quantity).label("total_unidades"),
            func.sum(models.OrderItem.quantity * models.OrderItem.price).label("total_ventas"),
        )
        .join(models.OrderItem, models.Product.id == models.OrderItem.product_id)
        .join(models.Order, models.Order.id == models.OrderItem.order_id)
        .group_by(models.Product.name)
    )
    if producto:
        q2 = q2.filter(models.Product.name == producto)
    if cliente:
        q2 = q2.join(models.Customer, models.Customer.id == models.Order.customer_id)\
               .filter(models.Customer.user_id == cliente)
    if orden_id:
        q2 = q2.filter(models.Order.id == orden_id)
    q2 = _filter_dates(q2, models.Order, desde, hasta)
    ventas_productos = [dict(r._mapping) for r in q2.all()]

    # 3️⃣ Detalle completo de órdenes
    q3 = (
        db.query(
            models.Order.id.label("orden_id"),
            models.Customer.user_id.label("cliente"),
            models.Product.name.label("producto"),
            models.OrderItem.quantity.label("cantidad"),
            models.OrderItem.price.label("precio_unitario"),
            (models.OrderItem.quantity * models.OrderItem.price).label("subtotal"),
            models.Order.total.label("total_orden"),
            models.Order.created_at.label("fecha"),
        )
        .join(models.Customer, models.Customer.id == models.Order.customer_id)
        .join(models.OrderItem, models.OrderItem.order_id == models.Order.id)
        .join(models.Product, models.Product.id == models.OrderItem.product_id)
    )
    if cliente:
        q3 = q3.filter(models.Customer.user_id == cliente)
    if producto:
        q3 = q3.filter(models.Product.name == producto)
    if orden_id:
        q3 = q3.filter(models.Order.id == orden_id)
    q3 = _filter_dates(q3, models.Order, desde, hasta)
    detalle_ordenes = [dict(r._mapping) for r in q3.all()]

    return {
        "order_summary": resumen_clientes,
        "sales_by_product": ventas_productos,
        "order_full_detail": detalle_ordenes,
    }
