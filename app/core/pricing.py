import re


def compute_discount_data(product, cantidad: int) -> dict:
    """
    Retorna datos de precio y descuento por volumen.
    {
      "precio": float,
      "porcentaje": float,
      "umbral": int,
      "per_unit_discount": float,
      "aplica": bool
    }
    """
    clean_product = {k.strip().lower(): v for k, v in product.items()}
    info_descuento = str(clean_product.get("descuento_mayorista_volumen", "")).strip()

    try:
        precio = float(str(clean_product.get("precio_lista", 0)).replace(",", "."))
    except ValueError:
        precio = 0.0

    porcentaje = 0.0
    umbral = 0
    m = re.search(r"(\d+(?:[.,]\d+)?)%\s*a\s+partir\s+de\s+(\d+)\s+unidades", info_descuento, re.IGNORECASE)
    if m:
        porcentaje = float(m.group(1).replace(",", "."))
        umbral = int(m.group(2))

    aplica = porcentaje > 0 and cantidad >= umbral
    per_unit_discount = precio * (porcentaje / 100.0) if aplica else 0.0

    return {
        "precio": precio,
        "porcentaje": porcentaje,
        "umbral": umbral,
        "per_unit_discount": per_unit_discount,
        "aplica": aplica,
    }


def calculate_total(product, cantidad):
    clean_product = {k.strip().lower(): v for k, v in product.items()}
    nombre  = clean_product.get("nombre", "Producto sin nombre")
    formato = clean_product.get("formato", "")

    discount_data = compute_discount_data(product, cantidad)
    precio = discount_data["precio"]
    subtotal = precio * cantidad
    texto = (
        f"{cantidad} × {nombre} ({formato})\n"
        f"Subtotal: ${subtotal:,.0f} COP"
    )

    # --- Aplicar descuento ---
    if discount_data["aplica"]:
        descuento_valor = discount_data["per_unit_discount"] * cantidad
        total = subtotal - descuento_valor
        texto += (
            f"\nDescuento: {discount_data['porcentaje']:.1f}% (-${descuento_valor:,.0f})"
            f"\nTotal: ${total:,.0f} COP"
        )
    else:
        total = subtotal
        texto += f"\nTotal: ${total:,.0f} COP"

    return texto
