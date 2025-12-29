# app/storage/sync_relational.py
from sqlalchemy.orm import Session
from . import models

def sync_order_to_relational(db: Session, order: models.Order):
    """
    Sincroniza una orden con las tablas relacionales:
    customers, products y order_items.
    Evita duplicados y múltiples commits.
    """
    # --- 1. Cliente ---
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.user_id == order.user_id)
        .first()
    )
    if not customer:
        customer = models.Customer(user_id=order.user_id)
        db.add(customer)
        db.flush()  # aún sin commit
    order.customer_id = customer.id

    # --- 2. Limpiar ítems antiguos ---
    db.query(models.OrderItem).filter(
        models.OrderItem.order_id == order.id
    ).delete()

    # --- 3. Productos e ítems ---
    for item in order.items:
        name = item.get("nombre")
        price = float(item.get("precio_unitario", 0))
        qty = int(item.get("cantidad", 1))

        # Buscar o crear producto
        product = (
            db.query(models.Product)
            .filter(models.Product.name == name)
            .first()
        )
        if not product:
            product = models.Product(name=name, price=price)
            db.add(product)
            db.flush()

        # Crear ítem
        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                price=price,
            )
        )

    # --- 4. Commit único ---
    db.commit()
    print(f"✅ Orden {order.id} sincronizada correctamente.")
