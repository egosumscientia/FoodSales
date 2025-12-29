import os
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.catalog import find_product_from_message, get_product_row
from app.core.responses import generate_response, build_logistics_response
from app.core.summary import build_summary
from app.core.nlp_rules import detect_purchase_intent, detect_logistics_intent

from app.core.carts.service import CartService
from app.core.carts.models import CartItem
cart_service = CartService(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None
    channel: str | None = None

# --- BLOQUE NUEVO: detección de cortesía ---
courtesy_keywords = [
    "hola", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "muy amable", "te agradezco", "muchas gracias",
    "listo", "perfecto", "de acuerdo", "vale", "ok", "entendido"
]

def detect_courtesy_intent(message: str) -> bool:
    message_lower = message.lower()
    return any(kw in message_lower for kw in courtesy_keywords)

def generate_courtesy_response(message: str) -> str:
    lower = message.lower()
    if any(greet in lower for greet in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
        return "¡Hola! 😊 ¿En qué puedo ayudarte hoy?"
    elif any(thanks in lower for thanks in ["gracias", "muy amable", "te agradezco", "muchas gracias"]):
        return "¡Con gusto! Si necesitas algo más, estoy aquí para ayudarte. 🙌"
    elif any(close in lower for close in ["listo", "perfecto", "de acuerdo", "vale", "ok", "entendido"]):
        return "Excelente 👍. Quedo atento por si deseas continuar con tu pedido o consulta."
    else:
        return "Estoy aquí si necesitas más información. 😊"
# --- FIN BLOQUE NUEVO ---

@router.post("/")
async def chat_endpoint(data: ChatMessage):
    try:
        user_input = data.message.lower().strip()

        # --- COMANDOS DE CARRITO ---
        if "ver carrito" in user_input:
            cart = cart_service.show(data.session_id)
            if not cart["items"]:
                return {"agent_response": "Tu carrito está vacío.", "should_escalate": False}
            items_txt = [f"- {i['name']} x{i['qty']} = ${i['line_total']:,.0f} COP" for i in cart["items"]]
            total_txt = f"🟩 Total carrito: ${cart['total']:,.0f} COP"
            return {"agent_response": "\n".join(items_txt + [total_txt]), "should_escalate": False}

        if "vacía carrito" in user_input or "limpia carrito" in user_input:
            cart_service.clear(data.session_id)
            return {"agent_response": "Carrito vaciado.", "should_escalate": False}

        if user_input.startswith("quita ") or user_input.startswith("elimina "):
            from app.core import nlp_rules
            palabra = user_input.replace("quita", "").replace("elimina", "").strip()

            # 1. Detectar producto(s) usando el mismo pipeline que agregar
            detected = nlp_rules.extract_products_and_quantities(palabra)

            if not detected:
                # Fallback para comandos sin cantidad ("quita nuggets")
                posible = find_product_from_message(palabra)
                if posible:
                    detected = [{"nombre": posible, "cantidad": 1}]
                else:
                    return {
                        "agent_response": "No encontré ese producto en nuestro catálogo actual. ¿Quieres que lo confirme un asesor?",
                        "should_escalate": False,
                    }

            removed_items = []

            for item in detected:
                prod_name = item["nombre"]

                # 2. Resolver nombre canónico
                prod_row = find_product_from_message(prod_name)
                if not prod_row:
                    continue

                # 3. Generar SKU igual que en la carga del carrito
                sku = prod_row.lower().replace(" ", "-")

                # 4. Quitar del carrito
                cart_service.remove(data.session_id, sku)
                removed_items.append(prod_row)

            cart = cart_service.show(data.session_id)

            if cart["items"]:
                items_txt = [f"- {i['name']} x{i['qty']} = ${i['line_total']:,.0f} COP" for i in cart["items"]]
                total_txt = f"🟩 Total carrito: ${cart['total']:,.0f} COP"
                carrito_txt = "\n".join(items_txt + [total_txt])
            else:
                carrito_txt = "🛒 Carrito vacío."

            return {
                "agent_response": f"Producto(s) eliminado(s): {', '.join(removed_items)}\n\n🛒 Carrito actualizado:\n{carrito_txt}",
                "should_escalate": False,
            }


        # --- FIN COMANDOS DE CARRITO ---

        # 🧠 Evaluar reclamos o sarcasmo antes de cualquier otra cosa
        from app.core.escalation import should_escalate

        import re
        if re.search(
            r"("
            # --- Producto o pedido dañado / incorrecto ---
            r"dañad|roto|defectuos|vencid|podrid|abiert|derramad|mojad|maltratad|golpead|rasg|"
            r"equivocad|no\s+(recibi|recibí|entregaron)|"
            r"pedido\s+(incompleto|mal)|"
            r"producto\s+(malo|incorrecto)|"
            r"falta(n|ba)|demora|tarde|retrasad|"
            # --- Reclamos e insatisfacción general ---
            r"inconform|insatisfech|descontent|molest[oa]|decepcionad[oa]|frustrad[oa]|indignad[oa]|"
            r"pesim|pésim|horribl|terribl|asco|inacept|mal\s+servicio|servicio\s+malo|"
            r"no\s+(me\s+gusto|me\s+agrada|estoy\s+content[oa]|funciona)|"
            r"maltrato|mala\s+atencion|mala\s+atención|trato\s+malo|deficiente|"
            r"me\s+siento\s+(mal|decepcionad[oa]|inconforme|insatisfech[oa])"
            r")",
            user_input,
            re.IGNORECASE,
        ) and not re.search(r"(cuanto|cuánto|precio|vale|cost|oferta|promocion|promoción)", user_input):
            return {
                "agent_response": (
                    "Lamento el inconveniente. Escalaré tu caso para revisión del pedido o producto por parte del área de calidad."
                ),
                "should_escalate": True,
                "summary": {
                    "tipo": "reclamo_producto_o_pedido",
                    "mensaje": user_input,
                },
            }

        # --- Escalamiento semántico como fallback ---
        escalation_result = should_escalate(user_input)


        # ✅ si el mensaje es reclamo o sarcasmo, salir inmediatamente
        if escalation_result and escalation_result.get("should_escalate"):
            return escalation_result  # usamos el texto original de escalation.py

        import re
        # 🔹 Detección robusta de consulta de precio
        if re.search(r"(cu(a|á)nto\s+(vale|cuesta)|precio\s+de)", user_input, re.IGNORECASE):
            # 1) Intentar multiproducto primero
            from app.core import nlp_rules
            items = nlp_rules.extract_products_and_quantities(user_input)

            if items:
                response_lines = []
                total_general = 0

                for item in items:
                    prod_name = item["nombre"]
                    qty = int(item.get("cantidad", 1))
                    prod_row = get_product_row(prod_name)

                    if not prod_row:
                        # ignora “tvs”, etc.
                        continue

                    from app.core.pricing import calculate_total
                    resultado = calculate_total(prod_row, qty)
                    response_lines.append(resultado)

                    m = re.search(r"Total:\s*\$([\d,]+)", resultado)
                    if m:
                        total_general += int(m.group(1).replace(",", ""))

                # Si al menos un producto válido fue calculado, responder y salir
                if response_lines:
                    if total_general > 0:
                        response_lines.append(f"🟩 Total general: ${total_general:,.0f} COP")
                    return {
                        "agent_response": "\n".join(response_lines),
                        "should_escalate": False,
                        "summary": {
                            "tipo": "consulta_precio_multiproducto",
                            "productos": [i["nombre"] for i in items],
                            "cantidad_items": len([i for i in items if get_product_row(i["nombre"])]),
                            "total_general": total_general
                        }
                    }

            # 2) Fallback a producto único si no se detectó multiproducto
            canonical_name = find_product_from_message(user_input)
            prod_row = get_product_row(canonical_name)
            if prod_row:
                return {
                    "agent_response": (
                        f"El precio de {prod_row['nombre']} es ${int(prod_row['precio_lista']):,} COP "
                        f"por presentación de {prod_row['formato']}. "
                        f"Descuento mayorista: {prod_row['descuento_mayorista_volumen']}."
                    ),
                    "should_escalate": False,
                    "summary": {
                        "tipo": "consulta_precio",
                        "producto": prod_row["nombre"]
                    }
                }
            else:
                return {
                    "agent_response": (
                        "No encontré ese producto en el catálogo. "
                        "¿Quieres que un asesor te confirme el precio?"
                    ),
                    "should_escalate": False
                }

        # 🔍 Detección de producto
        canonical_name = find_product_from_message(user_input)
        product_row = get_product_row(canonical_name) if canonical_name else None

        # 🧮 Detección de múltiples productos y cantidades
        from app.core import nlp_rules, pricing
        items = nlp_rules.extract_products_and_quantities(user_input)

        if items:
            response_lines = []
            total_general = 0
            for item in items:
                prod_name = item["nombre"]
                qty = item["cantidad"]
                prod_row = get_product_row(prod_name)
                if not prod_row:
                    response_lines.append(f"No encontré '{prod_name}' en el catálogo.")
                    continue

                from app.core.pricing import calculate_total
                resultado = calculate_total(prod_row, qty)
                response_lines.append(resultado)

                # --- NUEVO: actualizar carrito ---
                cart_item = CartItem(
                    sku=prod_row["nombre"].lower().replace(" ", "-"),
                    name=prod_row["nombre"],
                    qty=qty,
                    unit_price=float(str(prod_row["precio_lista"]).replace(",", ".")),
                )
                cart_service.add(data.session_id, cart_item, merge=True)
                # --- FIN NUEVO ---              

                import re
                match = re.search(r"Total: \$([\d,]+)", resultado)
                if match:
                    monto = int(match.group(1).replace(",", ""))
                    total_general += monto

            # --- MOSTRAR CARRITO ACTUALIZADO (sin repetir totales parciales) ---
            cart = cart_service.show(data.session_id)
            if cart["items"]:
                carrito_text = "\n".join(
                    [f"- {i['name']} x{i['qty']} = ${i['line_total']:,.0f} COP" for i in cart["items"]]
                    + [f"🟩 Total carrito: ${cart['total']:,.0f} COP"]
                )
                # Agrega el bloque una sola vez al final
            else:
                carrito_text = "🛒 Carrito vacío."
            # --- FIN MOSTRAR CARRITO ACTUALIZADO ---

            if total_general > 0:
                response_lines.append(f"🟩 Total general: ${total_general:,.0f} COP")

            return {
                "agent_response": "\n".join(response_lines + ["", "🛒 Carrito actualizado:", carrito_text]),
                "should_escalate": False,
                "summary": {
                    "pedido_o_consulta": user_input,
                    "accion_del_agente": f"Cálculo múltiple para {len(items)} productos",
                    "carrito": cart_service.show(data.session_id),
                },
            }


        # 👇 Si no hay productos, continúa flujo general
        intent_level = detect_purchase_intent(user_input)
        response = generate_response(product_row, user_input)

        # --- Prioridad de respuestas informativas directas (INVIMA, IVA, etc.) ---
        if "invima" in user_input or "certificado invima" in user_input:
            return response
        if "iva" in user_input or "incluye iva" in user_input or "precio con iva" in user_input:
            return response

        # 🧩 failsafe
        if response is None:
            response = {}

        # 🧠 Detección de intenciones adicionales antes de logística
        from app.core.nlp_rules import detect_additional_intents
        intents = detect_additional_intents(user_input)
        if intents.get("should_escalate"):
            response["should_escalate"] = True

        # 🚚 Detección logística
        logistic_detected, logistic_info = (False, {})
        if not intents.get("should_escalate") and not intents.get("discount_info"):
            logistic_detected, logistic_info = detect_logistics_intent(user_input)

        if not response or "agent_response" not in response:
            response = {"agent_response": "", "should_escalate": False}

        if logistic_detected and "entrega" not in response["agent_response"]:
            subtype = logistic_info.get("type")
            city = logistic_info.get("city")
            logistics_text = build_logistics_response(subtype, city)
            if product_row:
                response["agent_response"] += f"\n\n{logistics_text}"
            else:
                return {
                    "agent_response": logistics_text,
                    "should_escalate": False,
                    "summary": {
                        "pedido_o_consulta": user_input,
                        "accion_del_agente": "Información logística entregada.",
                        "intencion_compra": intent_level,
                        "delivery_info": {
                            "detected": True,
                            "type": subtype,
                            "city": city,
                        },
                    },
                }

        response = response or {}

        # 🧩 Caso: producto no encontrado y sin intención logística
        if not product_row and not logistic_detected and not response.get("agent_response"):
            response["agent_response"] = (
                "No encontré ese producto en nuestro catálogo actual. "
                "¿Quieres que lo confirme un asesor o te muestro opciones similares?"
            )
            response["should_escalate"] = response.get("should_escalate", False)

        # 🗣️ Ajustar respuesta según intención
        if intent_level == "high":
            response["agent_response"] += (
                "\nParece que estás listo para una cotización. ¿Deseas que la gestione ahora?"
            )
        elif intent_level == "medium":
            response["agent_response"] += (
                "\nPuedo darte un valor estimado o gestionar una cotización formal. ¿Qué prefieres?"
            )

        # 📋 Crear resumen final
        summary = build_summary(user_input, response["agent_response"])

        return {
            "agent_response": response["agent_response"],
            "should_escalate": response["should_escalate"],
            "summary": summary,
        }

    except Exception as e:
        import traceback
        print("[ERROR] chat_endpoint:", e)
        traceback.print_exc()
        return {
            "agent_response": "Ocurrió un error interno en el servidor.",
            "should_escalate": True,
            "summary": {"error": str(e)},
        }
