from time import time
from app.core.carts.models import CartItem
from app.core.carts.store_redis import RedisCartStore
from app.core.carts.store_memory import MemoryCartStore
import logging

log = logging.getLogger(__name__)


class CartService:
    """Operaciones CRUD con validación y fallback local."""

    def __init__(self, redis_url="redis://localhost:6379/0", client=None):
        # Intenta Redis y si falla usa memoria (para dev/local sin Redis).
        try:
            self.store = RedisCartStore(url=redis_url, client=client)
            self.store.client.ping()
            log.info("CartService usando Redis.")
        except Exception as err:
            log.warning(f"No se pudo conectar a Redis ({err}). Usando carrito en memoria.")
            self.store = MemoryCartStore()

    def _session(self, session_id: str) -> str:
        return session_id or "anon-session"

    def add(self, session_id: str, item: CartItem, merge=True):
        session_id = self._session(session_id)
        cart = self.store.get_or_create(session_id, item.currency)
        existing = cart.items.get(item.sku)
        if merge and existing:
            existing.qty += item.qty
            existing.unit_price = item.unit_price
            existing.discount = item.discount
        else:
            cart.items[item.sku] = item
        cart.last_action = {
            "action": "add",
            "sku": item.sku,
            "name": item.name,
            "qty": item.qty,
            "timestamp": time(),
        }
        self.store.save(cart)
        log.info(f"Item {item.sku} agregado al carrito {session_id}")
        return cart.to_summary()

    def update_qty(self, session_id: str, sku: str, qty: int):
        session_id = self._session(session_id)
        cart = self.store.get_or_create(session_id)
        if qty <= 0:
            cart.items.pop(sku, None)
        elif sku in cart.items:
            cart.items[sku].qty = qty
            cart.items[sku].updated_at = time()
        self.store.save(cart)
        return cart.to_summary()

    def remove(self, session_id: str, sku: str, qty: int | None = None):
        session_id = self._session(session_id)
        cart = self.store.get_or_create(session_id)
        item = cart.items.get(sku)
        if not item:
            cart.last_action = {
                "action": "remove_missing",
                "sku": sku,
                "qty": 0,
                "timestamp": time(),
            }
            self.store.save(cart)
            return cart.to_summary()
        if qty is None or qty >= item.qty:
            removed_qty = item.qty
            cart.items.pop(sku, None)
        else:
            removed_qty = qty
            item.qty -= removed_qty
            item.updated_at = time()
        cart.last_action = {
            "action": "remove",
            "sku": sku,
            "name": item.name,
            "qty": removed_qty,
            "timestamp": time(),
        }
        self.store.save(cart)
        return cart.to_summary()

    def clear(self, session_id: str):
        session_id = self._session(session_id)
        self.store.clear(session_id)
        # Re-crear carrito limpio y registrar acci¢n
        cart = self.store.get_or_create(session_id)
        cart.last_action = {
            "action": "clear",
            "qty": 0,
            "timestamp": time(),
        }
        self.store.save(cart)
        return cart.to_summary()

    def show(self, session_id: str):
        session_id = self._session(session_id)
        return self.store.get_or_create(session_id).to_summary()
