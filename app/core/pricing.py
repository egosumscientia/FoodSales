import re

def calculate_total(product, cantidad):
    clean_product = {k.strip().lower(): v for k, v in product.items()}
    nombre  = clean_product.get("nombre", "Producto sin nombre")
    formato = clean_product.get("formato", "")
    info_descuento = str(clean_product.get("descuento_mayorista_volumen", "")).strip()

    try:
        precio = float(str(clean_product.get("precio_lista", 0)).replace(",", "."))
    except ValueError:
        precio = 0.0

    # --- Descuento por volumen, patrón fijo según catálogo ---
    porcentaje = 0.0
    umbral = 0
    m = re.search(r"(\d+(?:[.,]\d+)?)%\s*a\s+partir\s+de\s+(\d+)\s+unidades", info_descuento, re.IGNORECASE)
    if m:
        porcentaje = float(m.group(1).replace(",", "."))
        umbral = int(m.group(2))

    subtotal = precio * cantidad
    texto = f"{cantidad} × {nombre} ({formato}) = ${subtotal:,.0f} COP"

    # --- Aplicar descuento ---
    if porcentaje > 0 and cantidad >= umbral:
        descuento_valor = subtotal * (porcentaje / 100.0)
        total = subtotal - descuento_valor
        texto += (
            f"\nDescuento aplicado: {porcentaje:.1f}% (-${descuento_valor:,.0f})"
            f"\nTotal: ${total:,.0f} COP"
        )
    else:
        total = subtotal
        texto += f"\nTotal: ${total:,.0f} COP"

    return texto
