from dataclasses import dataclass, asdict, field
from typing import Dict, Optional
from time import time
import logging

log = logging.getLogger(__name__)

def _now() -> float:
    return time()

@dataclass
class CartItem:
    sku: str
    name: str
    qty: int
    unit_price: float
    currency: str = "COP"
    discount: float = 0.0
    meta: Optional[dict] = field(default_factory=dict)
    updated_at: float = field(default_factory=_now)

    def __post_init__(self):
        if not self.sku or not isinstance(self.sku, str):
            raise ValueError("SKU inválido")
        if self.qty <= 0:
            raise ValueError("Cantidad debe ser > 0")
        if self.unit_price < 0:
            raise ValueError("Precio no puede ser negativo")
        if self.discount < 0:
            raise ValueError("Descuento no puede ser negativo")

    def line_total(self) -> float:
        return max(0.0, (self.unit_price - self.discount)) * self.qty

    def to_dict(self) -> dict:
        d = asdict(self)
        d["line_total"] = self.line_total()
        return d


@dataclass
class Cart:
    session_id: str
    items: Dict[str, CartItem]
    currency: str = "COP"
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    version: int = 1

    def subtotal(self) -> float:
        return sum(i.line_total() for i in self.items.values())

    def total(self) -> float:
        return self.subtotal()

    def to_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "currency": self.currency,
            "version": self.version,
            "items": [i.to_dict() for i in self.items.values()],
            "subtotal": self.subtotal(),
            "total": self.total(),
            "updated_at": self.updated_at,
        }
