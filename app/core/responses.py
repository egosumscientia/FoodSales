"""
Módulo de generación de respuestas AI-FoodSales
Versión: v1.4.0-courtesy-intents
Autor: Paulo & GPT-5 Lab
Descripción:
  - Prioridad total a reclamos (escalamiento antes que FAQ o logística)
  - Bloque de cortesía para saludos, agradecimientos y cierres naturales
  - Flujo semántico ordenado: cortesía → escalation → devolución → descuentos → FAQ → logística → productos
  - 100 % compatible con formato JSON y manejo de multiproducto
"""

from unittest import result
from app.core.summary import build_summary
from app.core.escalation import should_escalate


# --- BLOQUE NUEVO: Cortesía Contextual ---
courtesy_keywords = [
    "hola", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "muy amable", "te agradezco", "muchas gracias",
    "listo", "perfecto", "de acuerdo", "vale", "ok", "entendido"
]


def detect_courtesy_intent(message: str) -> bool:
    """Detecta saludos o expresiones de cortesía para evitar fallback innecesario."""
    message_lower = message.lower()
    return any(kw in message_lower for kw in courtesy_keywords)


def generate_courtesy_response(message: str) -> dict:
    """Genera respuestas empáticas para cierres o saludos."""
    lower = message.lower()
    if any(greet in lower for greet in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
        text = "¡Hola! 😊 ¿En qué puedo ayudarte hoy?"
    elif any(thanks in lower for thanks in ["gracias", "muy amable", "te agradezco", "muchas gracias"]):
        text = "¡Con gusto! Si necesitas algo más, estoy aquí para ayudarte. 🙌"
    elif any(close in lower for close in ["listo", "perfecto", "de acuerdo", "vale", "ok", "entendido"]):
        text = "Excelente 👍. Quedo atento por si deseas continuar con tu pedido o consulta."
    else:
        text = "Estoy aquí si necesitas más información. 😊"

    return {
        "agent_response": text,
        "should_escalate": False,
        "summary": build_summary(message, text),
    }
# --- FIN BLOQUE NUEVO ---


def generate_response(product_data: dict, message: str):
    """
    Genera la respuesta del agente de ventas.
    """

    if not message or not isinstance(message, str):
        return {
            "agent_response": "No entendí tu mensaje. ¿Podrías reformularlo?",
            "should_escalate": False,
            "summary": build_summary(message, "Entrada inválida o vacía."),
        }

    msg = message.lower().strip()
    should_escalate_flag = False
    response_text = ""

    # --- EXCEPCIÓN: consultas sobre IVA ---
    import re
    if re.search(r"\biva\b", msg) or "incluye iva" in msg or "precio con iva" in msg:
        response_text = (
            "Todos nuestros precios incluyen IVA, salvo que se indique lo contrario en la descripción del producto."
        )
        return {
            "agent_response": response_text,
            "should_escalate": False,
            "summary": build_summary(message, response_text),
        }

    # --- EXCEPCIÓN: consultas sobre INVIMA ---
    if "invima" in msg or "certificado invima" in msg:
        response_text = (
            "Sí, todos nuestros productos cuentan con registro sanitario INVIMA vigente "
            "y cumplen con las normas de calidad establecidas por las autoridades."
        )
        return {
            "agent_response": response_text,
            "should_escalate": False,
            "summary": build_summary(message, response_text),
        }
    
    # --- EXCEPCIÓN: tiempos de entrega por ciudad o región ---
    if "entrega" in msg or "llegada" in msg:
        import re

        # Detecta ciudad tras "en", "a" o "para", incluso con frases intermedias
        match = re.search(
            r"(?:en|a|para)\s+(?:la\s+entrega\s+a\s+)?([A-ZÁÉÍÓÚÑa-záéíóúñ]{3,}(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+)*)",
            message,
            re.UNICODE | re.IGNORECASE
        )

        ciudad = ""
        if match:
            posible = match.group(1).strip()
            # Evita falsos positivos como "entrega", "pedido", etc.
            if not re.search(r"\b(entrega|pedido|compra|envío|orden|la|el|los|las|para|en|a)\b", posible, re.IGNORECASE):
                ciudad = " ".join([p.capitalize() for p in posible.split()])

        # Si no detectó ciudad pero la frase tiene 'para' seguido de un nombre, capturarlo igualmente
        if not ciudad:
            match_alt = re.search(
                r"para\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]{3,}(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+)*)",
                message,
                re.UNICODE | re.IGNORECASE
            )
            if match_alt:
                posible = match_alt.group(1).strip()
                if not re.search(r"\b(entrega|pedido|compra|envío|orden|la|el|los|las|para|en|a)\b", posible, re.IGNORECASE):
                    ciudad = " ".join([p.capitalize() for p in posible.split()])

        if ciudad:
            response_text = f"El tiempo estimado de entrega en {ciudad} es de 2 a 5 días hábiles, según disponibilidad logística."
        else:
            response_text = "Los tiempos de entrega son de 2 a 5 días hábiles en ciudades principales y de 4 a 6 días en zonas regionales."

        return {
            "agent_response": response_text,
            "should_escalate": False,
            "summary": build_summary(message, response_text),
        }

    # 💬 2️⃣ Cortesía natural (saludos, agradecimientos, cierres)
    if detect_courtesy_intent(msg):
        return generate_courtesy_response(msg)


    # 💔 3️⃣ Bloque empático: producto dañado, mal olor, vencido
    import re
    if re.search(r"dañad|mal\s+olor|defectuos|vencid|en\s+mal\s+estado", msg):
        return {
            "agent_response": (
                "Lamentamos el inconveniente. Si un producto llegó dañado o en mal estado, "
                "puedes solicitar una devolución o cambio dentro de las 48 horas siguientes. "
                "¿Deseas que te envíe las instrucciones?"
            ),
            "should_escalate": True,
            "summary": build_summary(message, "Caso tratado como devolución por defecto de producto."),
        }

    # 🧠 4️⃣ Intenciones adicionales (descuentos, FAQ, etc.)
    from app.core.nlp_rules import detect_additional_intents
    intents = detect_additional_intents(message)
    if intents["should_escalate"]:
        should_escalate_flag = True

    if intents["discount_info"]:
        response_text = build_discount_response(message)
        return {
            "agent_response": response_text,
            "should_escalate": should_escalate_flag,
            "summary": build_summary(message, response_text),
        }

    if intents["faq"]:
        response_text = (
            "Pedidos mínimos: 4 unidades (Congelados), 5 (Lácteos), 12 (Bebidas) o $200.000 COP mixto.\n"
            "Tiempos de entrega: 2–3 días hábiles principales / 4–6 regionales.\n"
            "Formas de pago: transferencia, tarjeta o contraentrega (zonas urbanas).\n"
            "Devoluciones: máximo 24h con evidencia.\n"
            "¿Quieres que te gestione una cotización o más información?"
        )
        return {
            "agent_response": response_text,
            "should_escalate": should_escalate_flag,
            "summary": build_summary(message, response_text),
        }

    # 🚚 5️⃣ Logística
    from app.core.nlp_rules import detect_logistics_intent
    logistic_detected, logistic_data = detect_logistics_intent(message)
    if logistic_detected:
        subtype = logistic_data.get("type")
        city = logistic_data.get("city")
        response_text = build_logistics_response(subtype, city)
        return {
            "agent_response": response_text,
            "should_escalate": should_escalate_flag,
            "summary": build_summary(message, response_text),
        }
    # 📦 6️⃣ Productos (soporte multiproducto con cálculo de precios)
    print(f"[DEBUG] product_data recibido en responses: {product_data}", flush=True)

    # 📦 Productos (soporte multiproducto con cálculo de precios)
    if product_data:
        from app.core.pricing import calculate_total
        response_lines = []
        total_general = 0

        # Soporte multiproducto
        if isinstance(product_data, list):
            for p in product_data:
                cantidad = int(p.get("cantidad", 1))
                print(f"[RESPONSES] Invocando calculate_total() para {p.get('nombre')}", flush=True)
                print(f"[TRACE] p keys: {list(p.keys())}", flush=True)

                # calculate_total retorna string, pero podemos extraer valor numérico
                line_text = calculate_total(p, cantidad)
                response_lines.append(line_text)

                # Captura numérica del total por producto (solo números)
                import re
                m = re.search(r"Total: \$([\d,.]+)", line_text)
                if m:
                    total_general += float(m.group(1).replace(",", ""))

        else:
            cantidad = int(product_data.get("cantidad", 1))
            print(f"[RESPONSES] Invocando calculate_total() para {product_data.get('nombre')}", flush=True)
            line_text = calculate_total(product_data, cantidad)
            response_lines.append(line_text)
            import re
            m = re.search(r"Total: \$([\d,.]+)", line_text)
            if m:
                total_general += float(m.group(1).replace(",", ""))

        if total_general > 0:
            response_lines.append(f"Total general: ${total_general:,.0f} COP")

        response_text = "\n".join(response_lines)
    else:
        response_text = "No pude identificar el producto en tu mensaje. ¿Podrías darme más detalles?"


def build_logistics_response(subtype: str, city: str | None = None) -> str:
    city_delivery_map = {
        "bogota": "Para Bogotá: entrega en 2–3 días hábiles.",
        "medellin": "Para Medellín: entrega en 2–3 días hábiles.",
        "cali": "Para Cali: entrega en 3–4 días hábiles.",
        "barranquilla": "Para Barranquilla: entrega en 3–5 días hábiles.",
        "cartagena": "Para Cartagena: entrega en 3–5 días hábiles.",
        "bucaramanga": "Para Bucaramanga: entrega en 3–5 días hábiles.",
        "pereira": "Para Pereira: entrega en 3–4 días hábiles.",
        "manizales": "Para Manizales: entrega en 3–4 días hábiles.",
        "cucuta": "Para Cúcuta (zona regional): entrega en 4–6 días hábiles.",
    }

    if subtype == "weekend":
        return (
            "Realizamos entregas de lunes a sábado. "
            "Los domingos están sujetos a disponibilidad del operador logístico. "
            "¿Deseas que te confirme si tu zona tiene cobertura en fin de semana?"
        )
    elif subtype == "time_window":
        return (
            "Nuestros repartos se programan por franjas horarias: "
            "mañana (8–12), tarde (12–17) y noche (17–20), según cobertura. "
            "¿Deseas que te confirme la franja disponible para tu zona?"
        )
    elif subtype == "coverage":
        return (
            "Realizamos envíos a nivel nacional. Cobertura directa en ciudades principales "
            "y vía transportadora para zonas regionales. ¿Deseas que valide si llegamos a tu municipio?"
        )
    elif subtype == "city_delivery":
        if city:
            key = city.lower()
            city_text = city_delivery_map.get(key, "")
            return (city_text + " ¿Deseas que te confirme el tiempo exacto de entrega en esa zona?").strip()
    return (
        "Los tiempos de entrega son de 2 a 3 días hábiles en ciudades principales "
        "y de 4 a 6 días en regionales. ¿Deseas que te confirme la disponibilidad para tu zona?"
    )


def build_discount_response(message: str) -> str:
    msg = message.lower()
    if any(k in msg for k in ["bebida", "jugos", "agua", "gaseosa"]):
        return "Actualmente tenemos 10% de descuento en bebidas y jugos seleccionados."
    elif any(k in msg for k in ["lácteo", "queso", "yogurt", "leche"]):
        return "Tenemos 8% de descuento en lácteos esta semana."
    elif any(k in msg for k in ["congelado", "carne", "pollo", "pescado"]):
        return "Promoción del 12% en congelados hasta el domingo."
    else:
        return "Tenemos promociones activas en varias categorías. ¿Te gustaría conocer las ofertas actuales?"
