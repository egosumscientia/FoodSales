# app/storage/models.py
# ======================================================
# Modelos ORM de AI-FoodSales
# Fase 2: ampliación del modelo relacional
# ======================================================

from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


# ======================================================
# MODELO BASE: Order (mantener sin cambios semánticos)
# ======================================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    items = Column(JSON, nullable=False)  # Lista o dict con los ítems del pedido
    total = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending")
    order_serial = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

    def __repr__(self):
        return f"<Order id={self.id} user_id={self.user_id} total={self.total}>"


# ======================================================
# NUEVAS TABLAS RELACIONALES
# ======================================================

class Customer(Base):
    """
    Representa un cliente. En esta fase no se altera la lógica del agente:
    simplemente se guarda la relación con user_id existente.
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("Order", back_populates="customer")

    def __repr__(self):
        return f"<Customer user_id={self.user_id} name={self.name}>"


class Product(Base):
    """
    Representa un producto del catálogo.
    En el futuro puede sincronizarse con Catalog.csv.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)
    sku = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product name={self.name} price={self.price}>"


class OrderItem(Base):
    """
    Representa la relación entre una orden y los productos comprados.
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"
