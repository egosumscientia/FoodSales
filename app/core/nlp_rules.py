# app/core/nlp_rules.py
from pydoc import text
import json, os, re
from difflib import SequenceMatcher

DATA_DIR = os.path.join('app', 'data')
SYNONYMS_FILE = os.path.join(DATA_DIR, 'synonyms.json')



# -------------------------------------------------------------
# INTENCIÓN GENERAL
# -------------------------------------------------------------
def detect_intent(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ['precio', 'cuánto', 'cotiza', 'total', 'cuenta']):
        return 'quote'
    if any(k in text for k in ['tiempo', 'entrega', 'mínimo', 'pago', 'invima', 'certificado']):
        return 'faq'
    return 'other'


# -------------------------------------------------------------
# INTENCIÓN DE COMPRA
# -------------------------------------------------------------
def detect_purchase_intent(text: str) -> str:
    text = text.lower()

    high_intent = [
        "envíame", "hazme la cuenta", "quiero pedir", "cotízame",
        "necesito para", "urgente", "mándame la cotización",
        "cómo te pago", "cuánto me sale", "ya tengo pedido"
    ]

    medium_intent = [
        "me interesa", "cuánto vale", "qué precio tiene",
        "pueden enviar", "cuánto demora", "quiero saber si tienen",
        "podrían cotizarme", "estoy mirando precios"
    ]

    if any(p in text for p in high_intent):
        return "high"
    elif any(p in text for p in medium_intent):
        intent = "medium"
    else:
        intent = "low"

    # Detección de pedidos grandes
    if re.search(r'(\b\d+\s*(unidades?|cajas?|bultos?|litros?|kilos?|sacos?)\b|\bpedido grande\b|\ben cantidad\b)', text):
        return "high"

    return intent


# -------------------------------------------------------------
# INTENCIÓN LOGÍSTICA
# -------------------------------------------------------------
def detect_logistics_intent(text: str) -> tuple[bool, dict]:
    """
    Detecta si el mensaje se refiere a temas logísticos (entrega, cobertura, etc.).
    Retorna (True/False, {"type": str, "city": Optional[str]}).
    """
    if not text:
        return False, {}

    import unicodedata

    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("¿", "").replace("?", "").replace("¡", "").replace("!", "")

    logistics_keywords = [
        r"\b(entrega|entregan|entregar|entregado|entregas)\b",
        r"\b(envio|envian|enviar|enviarlo|envios)\b",
        r"\b(despacho|despachos|despachan|despachar)\b",
        r"\b(reparto|repartos|domicilio|domicilios|mensajeria|repartidor)\b",
        r"\b(cobertura|cubren|alcance)\b",
        r"\b(horario|hora|horas|mañana|tarde|noche|noches|fines?\s+de\s+semana|sabados?|domingos?)\b"
    ]

    if not any(re.search(pat, text) for pat in logistics_keywords):
        return False, {}

    # Tipificación logística
    if re.search(r"\b(fines?\s+de\s+semana|sabados?|domingos?)\b", text):
        subtype = "weekend"
    elif re.search(r"\b(horario|hora|horas|mañana|tarde|noche|noches)\b", text):
        subtype = "time_window"
    elif re.search(r"\b(cobertura|cubren|alcance|otras?\s+ciudades|fuera|nacional|envian\s+a)\b", text):
        subtype = "coverage"
    elif re.search(r"\b(cuanto\s+tardan?|tiempos?\s+de\s+entrega|plazo)\b", text):
        subtype = "delivery_time"
    else:
        subtype = "generic"

    city_match = re.search(
        r"\b(en|a)\s+(bogota|medellin|cali|barranquilla|cartagena|bucaramanga|pereira|manizales|cucuta)\b",
        text,
    )
    city = city_match.group(2).title() if city_match else None
    if city and subtype == "generic":
        subtype = "city_delivery"

    return True, {"type": subtype, "city": city}


# -------------------------------------------------------------
# NORMALIZACIÓN MULTIPRODUCTO
# -------------------------------------------------------------
def normalize_input(text: str) -> list[str]:
    """
    Busca todos los productos mencionados en el texto.
    Devuelve lista con nombres canónicos encontrados.
    Soporta plurales, errores menores y coincidencias parciales.
    """
    import unicodedata
    from difflib import SequenceMatcher

    # Cargar sinónimos
    try:
        with open(SYNONYMS_FILE, encoding='utf-8') as f:
            synonyms = json.load(f)
    except Exception:
        synonyms = {}

    # Normalizar texto (acentos y espacios)
    msg = text.lower().strip()
    msg = unicodedata.normalize("NFKD", msg)
    msg = "".join(c for c in msg if not unicodedata.combining(c))

    encontrados = set()

    for canonical, variants in synonyms.items():
        for v in variants:
            term = v.lower().strip()
            term = unicodedata.normalize("NFKD", term)
            term = "".join(c for c in term if not unicodedata.combining(c))

            # Coincidencia directa
            if term in msg:
                encontrados.add(canonical)
                continue

            # Coincidencia por palabras (una o más)
            if all(w in msg for w in term.split()):
                encontrados.add(canonical)
                continue

            # Coincidencia difusa (por similitud)
            ratio = SequenceMatcher(None, term, msg).ratio()
            if ratio > 0.65:
                encontrados.add(canonical)

    return list(encontrados)


# -------------------------------------------------------------
# INTENCIONES ADICIONALES
# -------------------------------------------------------------
def detect_additional_intents(text: str) -> dict:
    """
    Detecta intenciones adicionales: FAQ, discount_info, should_escalate.
    Prioridad: should_escalate > logistics > faq > discount.
    """
    text = text.lower()
    intents = {"faq": False, "discount_info": False, "should_escalate": False}

    # --- FAQ detection ---
    faq_keywords = [
        "mínimo", "minimos", "compra mínima", "pedido mínimo",
        "forma de pago", "formas de pago", "pago", "pagos",
        "contraentrega", "efectivo", "tarjeta", "crédito", "débito",
        "devolución", "devoluciones", "cambio", "cambios",
        "reembolso", "reembolsos", "tiempo de entrega", "entregan",
        "cuánto se demora la entrega", "disponibilidad", "stock", "existencias",
        "dañado", "mal olor", "defectuoso", "combinar", "mezclar", "mismo pedido",
        "certificado", "invima", "iva"
    ]
    if any(k in text for k in faq_keywords):
        intents["faq"] = True

    # --- Discounts detection ---
    discount_keywords = [
        "promocion", "promoción", "oferta", "descuento", "descuentos",
        "rebaja", "promo", "en oferta"
    ]
    if any(k in text for k in discount_keywords):
        intents["discount_info"] = True

    # --- Escalation detection ---
    escalate_keywords = [
        "reclamo", "problema", "queja", "error", "equivocado",
        "confusión", "pedido incorrecto", "producto equivocado",
        "pedido incompleto", "demora", "retraso", "no ha llegado", "todavía no llega",
        "repartidor", "cobrado", "cobro incorrecto", "precio distinto",
        "olvidó", "olvido", "esperando", "falta", "dañado", "cambio", "incompleto otra vez"
    ]

    if any(k in text for k in escalate_keywords):
        intents["should_escalate"] = True

    # --- Priority rules ---
    if intents["should_escalate"]:
        intents["faq"] = False
        intents["discount_info"] = False

    # --- Safe overrides ---
    # Frases informativas que nunca deben escalar
    safe_keywords = ["invima", "certificado invima", "iva", "descuento", "promoción", "oferta", "certificado"]
    if any(sk in text for sk in safe_keywords):
        intents["should_escalate"] = False
        intents["faq"] = True

    return intents

# --- Extraer múltiples productos y cantidades ---
def extract_products_and_quantities(message: str) -> list[dict]:
    import json, os, re, unicodedata
    from rapidfuzz import fuzz  # Asegúrate de tener instalado rapidfuzz

    # --- Definir normalización ---
    def norm(s: str) -> str:
        s = s.lower().strip()
        s = unicodedata.normalize("NFKD", s)
        return "".join(c for c in s if not unicodedata.combining(c))

    def strip_accents(s: str) -> str:
        s = unicodedata.normalize("NFKD", s)
        return "".join(c for c in s if not unicodedata.combining(c))

    txt = norm(message or "")
    txt = strip_accents(txt)

    # --- Normalización rápida antes del match ---
    txt = txt.lower()
    txt = txt.replace(";", ",").replace("+", ",").replace("/", ",")
    txt = txt.replace(" y ", ",").replace(" e ", ",").replace(" con ", ",")
    txt = re.sub(r'(?<=\d)(?=[a-záéíóúñ])', ' ', txt)
    txt = re.sub(r'(?<=[a-záéíóúñ])(?=\d)', ' ', txt)  # separa 8leches -> 8 leches
    txt = re.sub(r'\s+', ' ', txt).strip(',')
    txt = re.sub(r'(?<=\d)(?=[a-z])', ' ', txt)  # separa 9mm -> 9 mm

    DATA_DIR = os.path.join("app", "data")
    SYNONYMS_FILE = os.path.join(DATA_DIR, "synonyms.json")

    # --- Cargar sinónimos ---
    try:
        with open(SYNONYMS_FILE, encoding="utf-8") as f:
            synonyms = json.load(f)
    except Exception:
        return []

    print("DEBUG TXT:", txt)

    found_items = []

    # 🔹 Crear mapa enriquecido con plurales automáticos
    enriched = {}
    for canonical, variants in synonyms.items():
        sset = set()
        for v in variants:
            base = strip_accents(v.lower().strip())
            sset.add(base)
            if not base.endswith("s"):
                sset.add(base + "s")
            else:
                sset.add(base[:-1])
        enriched[canonical] = list(sset)

    # --- Reparar productos pegados sin espacios ---
    for canonical, variants in enriched.items():
        for v in variants:
            compact = v.replace(" ", "")
            if compact in txt:
                txt = txt.replace(compact, v)

    # 🔹 Buscar cantidades + sinónimo dentro del texto completo
    for canonical, variants in enriched.items():
        qty_total = 0
        matched = False

        # --- Coincidencia exacta ---
        for variant in variants:
            pattern = rf"(?<![a-záéíóúñ])(\d+)\s+(?:de\s+)?{re.escape(variant)}(?:\s*9\s*mm)?(?![\wáéíóúñ])"
            matches = list(re.finditer(pattern, txt))
            if matches:
                qty_total = int(matches[0].group(1))  # toma solo la primera coincidencia
                matched = True
                break  # evita contar duplicados

        # --- Coincidencia difusa (si no hubo match exacto) ---
        if not matched:
            tokens = txt.split()
            for token in tokens:
                for variant in variants:
                    if fuzz.ratio(token, variant) >= 80:
                        qty_total = 1
                        matched = True
                        break
                if matched:
                    break

        # --- Agregar si hubo match ---
        if matched:
            found_items.append({
                "nombre": canonical,
                "cantidad": qty_total
            })

    # 🔹 Ordenar según posición en el texto original (para coherencia en la respuesta)
    found_items.sort(
        key=lambda i: min(
            (txt.find(v) for v in enriched.get(i["nombre"], []) if txt.find(v) != -1),
            default=9999
        )
    )

    # 🔹 Si hay productos sin número explícito, contar 1 (solo si no se detectó ya con cantidad)
    for canonical, variants in enriched.items():
        if any(f["nombre"] == canonical and f["cantidad"] > 0 for f in found_items):
            continue
        if any(v in txt for v in variants):
            found_items.append({
                "nombre": canonical,
                "cantidad": 1
            })

    return found_items
