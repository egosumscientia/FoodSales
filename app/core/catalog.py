import csv, difflib, json, os, re, unicodedata

CATALOG_FILE = os.path.join(os.path.dirname(__file__), "../data/Catalog.csv")
SYNONYMS_FILE = os.path.join(os.path.dirname(__file__), "../data/synonyms.json")

# ----------------------------------------------------------------------
# 1️⃣ CARGA DEL CATÁLOGO Y SINÓNIMOS
# ----------------------------------------------------------------------
def load_catalog():
    """Carga el CSV del catálogo detectando codificación automáticamente."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(CATALOG_FILE, encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError("No se pudo leer el catálogo con las codificaciones conocidas.")

CATALOG = load_catalog()

if os.path.exists(SYNONYMS_FILE):
    with open(SYNONYMS_FILE, encoding="utf-8-sig") as f:
        SYNONYMS = json.load(f)
else:
    SYNONYMS = {}

# ----------------------------------------------------------------------
# 2️⃣ NORMALIZACIÓN DE TEXTO
# ----------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """Convierte texto a minúsculas, sin tildes ni caracteres raros."""
    text = text.lower().strip()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"(\b\w+)s\b", r"\1", text)  # plural → singular simple
    return text

# ----------------------------------------------------------------------
# 3️⃣ FUNCIÓN DE SIMILITUD Y COINCIDENCIA INTELIGENTE
# ----------------------------------------------------------------------
def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def find_product_from_message(message: str) -> str | None:
    """
    Busca el producto más probable en el catálogo.
    Incluye coincidencia difusa, sinónimos y control de umbral.
    """
    print("✅ EJECUTANDO VERSION CORRECTA DE catalog.py")

    msg = normalize_text(message)
    words = msg.split()
    best_match = None
    best_score = 0.0

    # 🔹 Prioridad 1: sinónimos (si existe synonyms.json)
    for key, variants in SYNONYMS.items():
        for variant in variants:
            norm_variant = normalize_text(variant)
            # Ignorar palabras demasiado cortas para evitar falsos positivos
            if len(norm_variant) <= 2:
                continue
            if re.search(rf"\b{re.escape(norm_variant)}\b", msg):
                print(f"[DEBUG] Coincidencia exacta por sinónimo: {key}")
                return key


    # 🔹 Prioridad 2: coincidencia directa o parcial
    for row in CATALOG:
        name = normalize_text(row["nombre"])
        for w in words:
            if w in name or name in w:
                score = similarity(msg, name)
                if score > best_score:
                    best_match, best_score = row["nombre"], score

    # 🔹 Prioridad 3: coincidencia difusa más general
    all_names = [normalize_text(r["nombre"]) for r in CATALOG]
    for w in words:
        matches = difflib.get_close_matches(w, all_names, n=1, cutoff=0.65)
        if matches:
            for r in CATALOG:
                if normalize_text(r["nombre"]) == matches[0]:
                    score = similarity(msg, matches[0])
                    if score > best_score:
                        best_match, best_score = r["nombre"], score

  # 🔹 Filtro final para evitar falsos positivos (como 'detergente' → 'té verde')
    # ------------------------------------------------------------------
    # 🔹 Filtro final y retorno controlado
    # ------------------------------------------------------------------
    if not best_match:
        print(f"[DEBUG] Ninguna coincidencia fuerte (max score={best_score:.2f})")
        return None

    # 🔹 Evita falsos positivos (ej. 'detergente' → 'té verde')
    if best_score < 0.65:
        print(f"[DEBUG] Coincidencia débil descartada (score={best_score:.2f})")
        return None

    print(f"[DEBUG] Mejor coincidencia aceptada: {best_match} (score={best_score:.2f})")
    return best_match



# ----------------------------------------------------------------------
# 4️⃣ ACCESO A UNA FILA COMPLETA DEL CATÁLOGO
# ----------------------------------------------------------------------
def get_product_row(product_name: str) -> dict | None:
    """Devuelve la fila completa del producto por nombre o coincidencia aproximada."""
    if not product_name:
        return None
    normalized = normalize_text(product_name)
    for row in CATALOG:
        if normalize_text(row["nombre"]) == normalized:
            return row

    # Buscar coincidencia cercana si no hay exacta
    names = [normalize_text(row["nombre"]) for row in CATALOG]
    match = difflib.get_close_matches(normalized, names, n=1, cutoff=0.4)
    if match:
        for row in CATALOG:
            if normalize_text(row["nombre"]) == match[0]:
                return row
    return None

# ----------------------------------------------------------------------
# 5️⃣ PRUEBA LOCAL
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[DEBUG] Archivo cargado: {CATALOG_FILE}")
    print(f"[DEBUG] Total productos: {len(CATALOG)}")
    if CATALOG:
        print("[DEBUG] Primeras 5 filas del catálogo:")
        for row in CATALOG[:5]:
            print(" -", row["nombre"])
    else:
        print("[ERROR] Catálogo vacío o mal leído")

    # Prueba rápida
    tests = [
        "cuánto valen las papas",
        "precio del queso mozzarella",
        "cuánto cuesta la torta de vainilla",
        "precio del detergente en polvo",
        "aceite de girasol",
        "galletas integrales",
    ]
    for t in tests:
        print(f"\n[TEST] {t} → {find_product_from_message(t)}")
