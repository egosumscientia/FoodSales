import json
import redis
from time import time
from app.core.carts.models import Cart, CartItem
import logging

log = logging.getLogger(__name__)

class RedisCartStore:
    """Persistencia con auditoría y TTL renovable."""
    def __init__(self, url="redis://localhost:6379/0", ttl_seconds=3600, client=None):
        self.client = client or redis.Redis.from_url(url, decode_responses=True)
        self.ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"cart:{session_id}"

    def get_or_create(self, session_id: str, currency: str = "COP") -> Cart:
        raw = self.client.get(self._key(session_id))
        if raw:
            data = json.loads(raw)
            items = {
                i["sku"]: CartItem(**{k: v for k, v in i.items() if k != "line_total"})
                for i in data["items"]
            }
            return Cart(
                session_id=session_id,
                items=items,
                currency=data.get("currency", currency),
                created_at=data.get("created_at", time()),
                updated_at=data.get("updated_at", time()),
                version=data.get("version", 1),
            )
        cart = Cart(session_id=session_id, items={}, currency=currency)
        self.save(cart)
        return cart

    def save(self, cart: Cart) -> None:
        cart.updated_at = time()
        cart.version += 1
        data = cart.to_summary()
        data["created_at"] = cart.created_at
        serialized = json.dumps(data)
        key = self._key(cart.session_id)
        with self.client.pipeline() as pipe:
            pipe.set(key, serialized)
            pipe.expire(key, self.ttl)
            pipe.execute()
        log.info(f"Cart {cart.session_id} actualizado. Versión {cart.version}")

    def clear(self, session_id: str) -> None:
        self.client.delete(self._key(session_id))
        log.info(f"Carrito {session_id} eliminado.")
