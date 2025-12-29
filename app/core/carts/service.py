from time import time
from app.core.carts.models import CartItem
from app.core.carts.store_redis import RedisCartStore
import logging

log = logging.getLogger(__name__)

class CartService:
    """Operaciones CRUD con validación y auditoría."""
    def __init__(self, redis_url="redis://localhost:6379/0", client=None):
        self.store = RedisCartStore(url=redis_url, client=client)

    def add(self, session_id: str, item: CartItem, merge=True):
        cart = self.store.get_or_create(session_id, item.currency)
        existing = cart.items.get(item.sku)
        if merge and existing:
            existing.qty += item.qty
            existing.unit_price = item.unit_price
            existing.discount = item.discount
        else:
            cart.items[item.sku] = item
        self.store.save(cart)
        log.info(f"Item {item.sku} agregado al carrito {session_id}")
        return cart.to_summary()

    def update_qty(self, session_id: str, sku: str, qty: int):
        cart = self.store.get_or_create(session_id)
        if qty <= 0:
            cart.items.pop(sku, None)
        elif sku in cart.items:
            cart.items[sku].qty = qty
            cart.items[sku].updated_at = time()
        self.store.save(cart)
        return cart.to_summary()

    def remove(self, session_id: str, sku: str):
        cart = self.store.get_or_create(session_id)
        cart.items.pop(sku, None)
        self.store.save(cart)
        return cart.to_summary()

    def clear(self, session_id: str):
        self.store.clear(session_id)
        return self.store.get_or_create(session_id).to_summary()

    def show(self, session_id: str):
        return self.store.get_or_create(session_id).to_summary()
