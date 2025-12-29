from time import time
from app.core.carts.models import Cart, CartItem
import logging

log = logging.getLogger(__name__)


class MemoryCartStore:
    """Almacenamiento en memoria para desarrollo o fallback cuando Redis no está disponible."""

    def __init__(self):
        self._store = {}

    def get_or_create(self, session_id: str, currency: str = "COP") -> Cart:
        cart = self._store.get(session_id)
        if cart:
            return cart
        cart = Cart(session_id=session_id, items={}, currency=currency)
        self._store[session_id] = cart
        return cart

    def save(self, cart: Cart) -> None:
        cart.updated_at = time()
        cart.version += 1
        self._store[cart.session_id] = cart
        log.info(f"Cart {cart.session_id} actualizado en memoria. Versión {cart.version}")

    def clear(self, session_id: str) -> None:
        if session_id in self._store:
            del self._store[session_id]
        log.info(f"Carrito {session_id} eliminado en memoria.")
