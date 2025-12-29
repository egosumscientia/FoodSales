print("🔥 escalation.py CARGADO desde:", __file__)

# -*- coding: utf-8 -*-
"""
AI-FoodSales • Escalamiento v1.4.1
Autor: Paulo & GPT-5 Lab

Descripción:
    Detección avanzada de reclamos:
      - Cobertura completa del vocabulario original
      - Fuzzy matching (errores ortográficos comunes)
      - Traducción ligera inglés→español
      - Detección de sarcasmo o frustración
      - Regla: reclamo > cortesía
      - Respuesta y summary estructurados
"""

import re, difflib
from dataclasses import dataclass
from typing import Dict, List


# ---------------------------
# Léxicos base
# ---------------------------

POLITENESS = {
    "por favor","porfa","gracias","mil gracias","buen dia","buen día",
    "buenas","buenas tardes","buenas noches","hola","agradezco","si son tan amables",
    "muy amable","de acuerdo","vale","ok","entendido"
}

# Todas las frases del escalation_keywords original + raíces abreviadas
COMPLAINT_ROOTS = {
    # Reclamos y problemas generales
    "reclamo","problema","queja","error","equivocado","mal","malo","defectuoso",
    "descompuesto","deteriorado","confusion","confundi","en mal estado",
    "no entiendo","no corresponde","dañado","inservible","roto","podrido","vencido",
    "quebrado","incompleto","faltantes","menos productos","menos de lo solicitado",
    "precio diferente","precio distinto","factura diferente",
    # Reclamos y problemas generales
    "reclamo","problema","queja","error","equivocado","mal","malo","defectuoso",
    "inaceptable","esperando","espera","demasiado","tardo","pedido","entrega","demorado",
    # Pedidos y entregas con error
    "pedido incorrecto","producto equivocado","me llego mal","no ha llegado","no llego",
    "no me llego","no me ha llegado","vino incompleto","llego incompleto",
    "entregaron incompleto","pedido incompleto","entrega incompleta","faltante",
    "falto","faltaron","no completo","menos de lo pedido","demora","retraso","tarde",
    "no aparece","todavia no llega","entrega pendiente","repartidor","no pudo entregar",
    "no puede entregar","pedido vino incompleto","vino mal","vino con faltantes",
    "mal despachado","error de despacho","fria", "frío", "comida fria", "comida fría",
    # Casos administrativos o de soporte documental
    "contrato","certificado adicional","certificado invima","documento adicional",
    "invima","soporte adicional",
    # Casos de reembolso o devolución
    "reembolso", "reembolsar", "reembolsaron", "reembolsaronme", 
    "devolver dinero", "devolución", "devolucion", "dinero devuelto",
    "reintegro", "reintegrar", "me devolvieron", "quiero un reembolso",
    # Casos financieros o de cobro
    "cobrado","me cobraron","cobraron","cobrar","cobro incorrecto","precio distinto",
    "error en factura","cobro duplicado","error en cobro","factura mal",
    "valor diferente","costo equivocado","precio errado","precio equivocado",
    "precio incorrecto","sobreprecio","sobre cobro","me cobraron de mas",
    # Raíces genéricas abreviadas
    "cobr", "reembols", "devolu", "tard", "retras", "demor", "no lleg", "falt", "incomplet",
    "frustración", "frustracion", "frustr", "equivocad", "cancel", "estaf", "fraud", "frio", "malis", 
    "pesim", "horri", "terrible","molesto", "indig", "incompet", "neglig",
    #Otros con ironía
    "eficiencia", "eficiente", "respuesta", "atencion", "atención",
    "servicio", "entrega", "soporte"
}

FRUSTRATION_MARKS = {"😒","🙃","😤","😠","🤦","🤬","💢"}

EN_TO_ES_GLOSSARY = {
    # Cobros / facturación
    "charge":"cobr","charged":"cobr","charge me twice":"cobr","charged me twice":"cobr",
    "they charged me":"cobr","they charged me twice":"cobr","double charge":"cobr",
    "overcharge":"cobr","overcharged":"cobr","extra charge":"cobr","wrong charge":"cobr",
    "billing error":"cobr","invoice error":"cobr","wrong price":"cobr","wrong amount":"cobr",
    "double charged":"cobr","charged again":"cobr","charged extra":"cobr","twice":"duplicado",

    # Reembolsos
    "refund":"reembols","refunded":"reembols","refund me":"reembols","money back":"reembols",
    "need a refund":"reembols","return my money":"reembols","no refund":"reembols",

    # Entregas tardías o no llegadas
    "never arrived":"no lleg","didn't arrive":"no lleg","not delivered":"no lleg",
    "never delivered":"no lleg","hasn't arrived":"no lleg","delivery failed":"no lleg",
    "where is my order":"no lleg","late":"retras","too late":"retras","delay":"retras",
    "delayed":"retras","running late":"retras","still waiting":"demor","taking too long":"demor",

    # Faltantes / incompletos / errores
    "missing":"falt","missing item":"falt","missing items":"falt","incomplete":"incomplet",
    "incomplete order":"incomplet","partial order":"incomplet",
    "wrong item":"equivocad","wrong product":"equivocad","wrong order":"equivocad",

    # Calidad o estado del producto
    "bad":"mal","awful":"horrible","terrible":"terrible","cold":"frio",
    "cold food":"frio","food was cold":"frio","spoiled":"podrido","rotten":"podrido",
    "expired":"vencido","broken":"roto","damaged":"danado",

    # Cancelaciones
    "cancel":"cancel","canceled":"cancel","cancelled":"cancel",
    "please cancel":"cancel","cancel my order":"cancel","i want to cancel":"cancel",
}


SARCASM_POS_MARKERS = {
    # Positivos exagerados (comunes en sarcasmo)
    "increible","increíble","maravilloso","fantastico","fantástico",
    "genial","excelente","perfecto","magnifico","magnífico",
    "espectacular","grandioso","buenisimo","buenísimo","formidable",
    "impresionante","fenomenal","divino","maravilla","fantasia","fantasía",
    "de lujo","de maravilla","de diez","de pelicula","de película",

    # Ironías frecuentes en contexto de reclamo
    "claro","por supuesto","seguro","obvio","como no",
    "si claro","ah claro","ah buenisimo","ah buenísimo","ah excelente",
    "ah genial","ah perfecto","ah fantástico",

    # Sarcasmo informal / redes sociales
    "wow","super","súper","super bien","super bueno","super servicio",
    "re bien","rebueno","super rapido","super rápido","rapidisimo","rapidísimo",
    "que alegria","que alegría","felicidades","bravo","premio","aplausos",

    # Variantes con tono irónico / frustración disimulada
    "maravillosa atencion","excelente servicio","servicio impecable",
    "todo perfecto","como siempre","una joya","de lo mejor","mejor imposible",
    "sin palabras","buen trabajo","feliz con esto","todo un exito","todo un éxito"
}


NEGATIONS = {"no","nunca","jamás","ni"}

COMMON_FIXES = {
    # Reclamos / devoluciones / reembolsos
    "reembolzo":"reembolso","rebolso":"reembolso","reemborso":"reembolso","reembolco":"reembolso",
    "reembolo":"reembolso","reemboso":"reembolso","reembolsar":"reembolso",
    "rebolsaron":"reembolsaron","reembolzaron":"reembolsaron",
    "rebolsar":"reembolsar","reembolzar":"reembolsar",
    "rebolso mal":"reembolso mal","reembolzo mal":"reembolso mal",
    "debolucion":"devolucion","debolver":"devolver","debolvieron":"devolvieron",
    "devolber":"devolver","devolbieron":"devolvieron",

    # Tiempos / demoras / entregas
    "tade":"tarde","tardea":"tarde","retaso":"retraso","retasado":"retrasado",
    "demorao":"demorado","demorau":"demorado","demorardo":"demorado",
    "demoraronse":"demoraron","demorazado":"demorado",
    "retasaron":"retrasaron","retrasao":"retrasado","tadanza":"tardanza",
    "retrasado":"retraso","tardeza":"tardanza",

    # Faltantes / incompletos
    "fataron":"faltaron","faltaronse":"faltaron","farton":"faltaron",
    "faltate":"faltante","faltanres":"faltantes","faltane":"faltante",
    "falto":"faltó","faltan":"faltan","faltates":"faltantes",
    "falantes":"faltantes","faltente":"faltante","faltate":"faltante",

    # Cobros / precios / facturas
    "cobarro":"cobrar","cobor":"cobro","cobaron":"cobraron","cobrron":"cobraron",
    "cobrrado":"cobrado","cobaronme":"cobraronme","cobaro":"cobro",
    "cobrarro":"cobrar","cobrarron":"cobraron","cobarron":"cobraron",
    "cobrronme":"cobraronme","cobraronme":"cobraron","cobram":"cobran",
    "corbaron":"cobraron","cobrarr":"cobrar","cobro mal":"cobro mal",
    "sobreco":"sobrecobro","sobre cobr":"sobrecobro","sobrecobr":"sobrecobro",

    # Adjetivos / tono
    "exelente":"excelente","exelentee":"excelente","exselente":"excelente",
    "exelent":"excelente","eselente":"excelente","exclente":"excelente",
    "malo":"malo","malisimo":"malísimo","malisimo":"malísimo",
    "orible":"horrible","orrible":"horrible","horible":"horrible",
    "terrivle":"terrible","terible":"terrible","horrivle":"horrible",

    # Productos / pedidos
    "pedio":"pedido","peido":"pedido","pedidio":"pedido","pedidido":"pedido",
    "pidido":"pedido","pidio":"pedido","peddio":"pedido",
    "incomple":"incompleto","incompl":"incompleto","incoml":"incompleto",
    "incompletoo":"incompleto","incomplet":"incompleto","inconpleto":"incompleto",
    "incomplto":"incompleto","incomplleto":"incompleto",
    "prodcuto":"producto","prudcto":"producto","prdducto":"producto",
    "prodocto":"producto","produccto":"producto","prodcto":"producto",

    # Otros frecuentes
    "enrega":"entrega","entregaado":"entregado","entregra":"entrega",
    "entergaron":"entregaron","entrego":"entregó","entregon":"entregaron",
    "enviado mal":"envío mal","envioo":"envío","enbió":"envió",
    "enbvio":"envío","enbio":"envío","enbió":"envió",
    "comida fria":"comida fría","fria":"fría","frio":"frío",
    "cancelado":"cancelado","cancelaron":"cancelaron","cancelaro":"cancelaron",
    "cancelado mal":"cancelado mal","cancelaronme":"cancelaronme"
}


# ---------------------------
# Utilidades
# ---------------------------

def normalize(text: str) -> str:
    # Paso 1: todo a minúsculas
    t = text.lower()

    # Paso 2: traducción ligera inglés→español
    for k, v in EN_TO_ES_GLOSSARY.items():
        if k in t:
            t = t.replace(k, v)

    # Paso 3: normalizar tildes
    t = (t.replace("á","a").replace("é","e").replace("í","i")
           .replace("ó","o").replace("ú","u"))

    # Paso 4: correcciones ortográficas comunes
    for w, r in COMMON_FIXES.items():
        t = t.replace(w, r)

    # 🟢 Paso 5: conservar emojis y signos de frustración
    t = re.sub(r"[^a-z0-9\sñ😒😑🙃😠🤦🤷]", " ", t)

    # Paso 6: limpiar espacios duplicados
    return re.sub(r"\s+"," ",t).strip()

def tokens(text: str) -> List[str]:
    return re.findall(r"[\w¿?¡!']+", text.lower())

def ratio(a:str,b:str)->float:
    return difflib.SequenceMatcher(None,a,b).ratio()

def fuzzy_contains(text:str, root:str, threshold:float=0.82)->bool:
    for tok in tokens(text):
        if ratio(tok,root)>=threshold or root in tok:
            return True
    return False

def any_emoji(text:str)->bool:
    return any(e in text for e in FRUSTRATION_MARKS)

def map_english_to_spanish_roots(text:str)->List[str]:
    hits=[]
    for en,es in EN_TO_ES_GLOSSARY.items():
        if en in text.lower():
            hits.append(es)
    return hits


# ---------------------------
# Scoring
# ---------------------------

@dataclass
class Scores:
    complaint: float = 0.0
    sarcasm: float = 0.0
    politeness: float = 0.0
    cues: Dict[str, List[str]] = None
    def __post_init__(self):
        if self.cues is None:
            self.cues={"complaint":[], "sarcasm":[], "politeness":[]}


THRESHOLDS={"complaint":1.3,"soft":1.0,"sarcasm":0.4}
WEIGHTS={"exact":1.0,"fuzzy":0.8,"neg":0.5,"emoji":1.0,"eng":0.9,"sarc":1.4,"contrast":1.0}

def score_politeness(text:str, s:Scores):
    for p in POLITENESS:
        if p in text:
            s.politeness+=0.25; s.cues["politeness"].append(p)

def score_complaint(text:str, s:Scores):
    for r in COMPLAINT_ROOTS:
        if r in text:
            s.complaint+=WEIGHTS["exact"]; s.cues["complaint"].append(r)
        elif fuzzy_contains(text,r):
            s.complaint+=WEIGHTS["fuzzy"]; s.cues["complaint"].append("~"+r)
    for n in NEGATIONS:
        if re.search(rf"\b{n}\b",text):
            s.complaint+=WEIGHTS["neg"]; s.cues["complaint"].append("neg:"+n)
    if any_emoji(text):
        s.complaint+=WEIGHTS["emoji"]; s.cues["complaint"].append("emoji")
    for r in map_english_to_spanish_roots(text):
        s.complaint+=WEIGHTS["eng"]; s.cues["complaint"].append("en→"+r)
        # 🔹 Extensión ligera para reclamos comunes no cubiertos por raíces
    if re.search(r"(inaceptable|esperando|demasiado|tardo|demorado|pedido)", text):
        s.complaint += 1.0
        s.cues["complaint"].append("reclamo_extra")
    

def score_sarcasm(text: str, s: Scores):
    # sarcasmo positivo + negativo (base original)
    pos = any(p in text for p in SARCASM_POS_MARKERS)
    neg = any(n in text for n in NEGATIONS) or any(r in text for r in COMPLAINT_ROOTS)
    if pos and neg:
        s.sarcasm += WEIGHTS["sarc"]
        s.cues["sarcasm"].append("pos+neg")

    # sarcasmo con elogio + espera o frustración
    elif pos and re.search(r"(pedido|esperando|lleg|comida|tarde|nada|fr[ií]a|frio|demora|aun|todav[ií]a)", text):
        s.sarcasm += WEIGHTS["sarc"] * 0.9
        s.cues["sarcasm"].append("pos+espera")

    # sarcasmo contrastivo: "si es que", "claro que", "pero", "aunque"
    if re.search(r"(si es que|claro que|pero|aunque).{0,20}(llega|llego|funciona|resuelv|arregl)", text):
        s.sarcasm += WEIGHTS["contrast"]
        s.cues["sarcasm"].append("contrastive")

    # ✅ sarcasmo tipo elogio + reclamo (ajustado con impacto en complaint)
    if re.search(r"(incre[ií]ble|fant[aá]stico|perfecto|excelente|genial).{0,80}(esperando|pedido|lleg|nada|fr[ií]a|frio|tarde|demora|a[úu]n|todav[ií]a)", text):
        s.sarcasm += 1.5
        s.complaint += 0.5
        s.cues["sarcasm"].append("sarcasmo_contraste")

    # ironías de cortesía
    if re.search(r"(ah|muy|tan)\s?(buen[ií]simo|excelente|amable|eficiente|r[aá]pido).{0,40}(nada|demora|problema|error|fall[oó])", text):
        s.sarcasm += 1.0
        s.cues["sarcasm"].append("sarcasmo_ironia_cortesia")
    
    # sarcasmo cortés + frustración (ejemplo: "Perfecto, dos horas esperando y nada 😑")
    if re.search(r"(perfecto|excelente|genial|wow|incre[ií]ble|fant[aá]stico)[^\\n]{0,150}(hora|horas|esperando|todav[ií]a|nada|tarde|demora)", text, flags=re.IGNORECASE|re.UNICODE):
        s.sarcasm += 2.0
        s.complaint += 1.0
        s.cues["sarcasm"].append("sarcasmo_cortesia_frustrada")

    # emojis de frustración tras elogio
    if re.search(r"(😒|😑|🙃|😠|🤦|🤷)", text):
        s.sarcasm += 0.8
        s.cues["sarcasm"].append("emoji_frustracion")

    # fuerza un mínimo de sarcasmo si hay emoji + palabra de espera
    if re.search(r"(😒|😑|🙃|😠|🤦|🤷)", text) and re.search(r"(esperando|nada|tarde|pedido|lleg)", text):
        s.sarcasm = max(s.sarcasm, 1.0)
    
    # Corrige interferencia con cortesía: si hay sarcasmo y emoji frustración, reduce cortesía
    if s.sarcasm >= 0.8 and re.search(r"(😒|😑|🙃|😠|🤦|🤷)", text):
        s.politeness = max(0.0, s.politeness - 1.0)

    # failsafe: si hay sarcasmo leve + palabras de espera, forzar reclamo implícito
    if s.sarcasm >= 1.0 and re.search(r"(esperando|hora|horas|nada|tarde|demora|todavia|aun)", text):
        s.complaint += 1.0

    # sarcasmo indirecto o irónico sin emoji
    if re.search(r"(aunque|pero|otra vez|por lo visto|sigan así|no es su fuerte).{0,40}", text):
        s.sarcasm += 1.0
        s.cues["sarcasm"].append("sarcasmo_indirecto")

    if re.search(r"(gracias|perfecto|excelente).{0,30}(pero|aunque|nada|sin)", text):
        s.sarcasm += 1.2
        s.complaint += 0.8
        s.cues["sarcasm"].append("sarcasmo_cortesia_falsa")

    # sarcasmo resignado o ironía pasiva (dinámico con duración variable)
    if re.search(r"(alg[úu]n d[ií]a|paciencia|ya llegar[aá]|sigue igual|todo igual|sin resultado|ya van\s*[0-9]+\s*horas|[0-9]+\s*horas\s*(y\s*contando)?|hora[s]?\s*y\s*contando)", text):
        s.sarcasm += 1.0
        s.complaint += 0.5
        s.cues["sarcasm"].append("sarcasmo_resignado")

    # sarcasmo de falsa satisfacción o ironía positiva ("me encanta esperar tanto")
    if re.search(r"(me\s+(encanta|fascina|gusta|alegra|maravilla).{0,40}(esperar|nada|demora|tarde|no\s+llega|sin|eficiencia|puntualidad|velocidad|lento))", text):
        s.sarcasm += 1.5
        s.complaint += 0.7
        s.cues["sarcasm"].append("sarcasmo_falsa_satisfaccion")

    # sarcasmo implícito con tono positivo + negación ("Qué gusto da no recibir nada")
    if re.search(r"(qu[eé]\s+(gusto|placer|alegr[ií]a|maravilla).{0,30}(no|sin)\s+[a-záéíóúñ]+)", text):
        s.sarcasm += 1.3
        s.complaint += 0.6
        s.cues["sarcasm"].append("sarcasmo_implicito_positivo")

    # sarcasmo con elogio y negación o contraste implícito ("qué gusto da ver tanta eficiencia inexistente")
    if re.search(r"(qu[eé]\s+(gusto|placer|maravilla|alegr[ií]a|honor|satisfacci[oó]n).{0,40}(inexistente|lento|sin|nada|ausente))", text):
        s.sarcasm += 1.4
        s.complaint += 0.6
        s.cues["sarcasm"].append("sarcasmo_elogio_negado")

    # sarcasmo seco o ironía implícita sin elogio directo
    if re.search(r"(qué\s+(sorpresa|raro|eficiente|tranquilo|emocionante|normal)|nada\s+(nuevo|mejor|diferente)|todo\s+(igual|normal)|sin\s+(novedad|cambio))", text):
        s.sarcasm += 1.0
        s.complaint += 0.5
        s.cues["sarcasm"].append("sarcasmo_seco_implícito")

        # sarcasmo hiperbólico o humor negro (esperas imposibles o exageradas)
    if re.search(r"(a este paso|antes de navidad|voy a envejecer|para el próximo año|en otra vida)", text):
        s.sarcasm += 1.3
        s.complaint += 0.6
        s.cues["sarcasm"].append("sarcasmo_hiperbolico_tiempo")

    return s

# ---------------------------
# Decisión principal
# ---------------------------

def should_escalate(message:str)->Dict:
    if not message:
        return {"agent_response":"","should_escalate":False,"summary":{}}

    t = normalize(message)

    # Profanidad/insultos directos -> escalar siempre
    if re.search(
        r"\b("
        r"maldito|maldita|mierda|carajo|coñ[oó]|cono|hp|hpta|hijueputa|gonorrea|perra|conchudo|conchuda|"
        r"mediocre[s]?|bazofia[s]?|basura[s]?|inútil|inutil|incompetent[e]?s?|inept[oa]s?|estafador[a]?s?|"
        r"ladrón|ladron|ladrones|rata[s]?|ratero[s]?|imbécil|imbecil|idiota[s]?|tonto[s]?|torpe[s]?|asqueros[oa]s?|"
        r"patético|patetico|verg[üu]enza|pésimo|pesimo|nefast[oa]s?|desastre"
        r")\b",
        t,
    ):
        return {
            "agent_response": "Voy a escalar tu caso a un asesor humano para que te ayude con tu solicitud.",
            "should_escalate": True,
            "summary": {
                "version": "v1.4.1",
                "motivo": "profanidad",
                "mensaje": message,
            },
        }

    s = Scores()
    score_politeness(t, s)
    score_complaint(t, s)
    score_sarcasm(t, s)

    # --- DEBUG TEMPORAL (eliminar luego) ---
    print(">>> SHOULD_ESCALATE CALLED with raw message:", repr(message))
    print(">>> normalized text:", repr(t))
    print(">>> SCORES BEFORE DECISION -> sarcasm:", s.sarcasm, "complaint:", s.complaint, "politeness:", s.politeness)
    print(">>> CUES:", s.cues)
    # --- END DEBUG ---


    # 👉 NUEVO BLOQUE: sarcasmo fuerte cuenta como reclamo implícito
    if s.sarcasm >= THRESHOLDS["sarcasm"]:
        s.complaint += 0.8
    
    thr = THRESHOLDS["complaint"]

    # 🔹 Forzar escalamiento inmediato para reclamos explícitos
    if re.search(r"\b(reclamo|queja|problema|error|demora)\b", t):
        escalate = True
    else:
        thr = THRESHOLDS["soft"] if s.sarcasm >= THRESHOLDS["sarcasm"] else THRESHOLDS["complaint"]
        # Escala automáticamente si hay sarcasmo claro o emoji de frustración
        if (s.sarcasm >= 1.0 and s.sarcasm >= s.politeness) or any_emoji(t):
            escalate = True
        else:
            escalate = s.complaint >= thr

    summary = {
        "version": "v1.4.1",
        "scores": {
            "complaint": round(s.complaint, 2),
            "sarcasm": round(s.sarcasm, 2),
            "politeness": round(s.politeness, 2),
            "threshold": thr
        },
        "cues": s.cues,
        "priority_rule": "reclamo prevalece sobre cortesía"
    }

    if escalate:
        response = (
            "Entendido, escalaré tu caso para que un asesor te contacte y revise tu solicitud. "
            "Un representante validará cobros, productos faltantes o demoras."
        )
    else:
        response = (
            "Quiero ayudarte mejor. ¿Podrías indicar el número de pedido y describir brevemente el problema "
            "(cobro erróneo, producto faltante, demora, calidad)?"
        )
    
    print(">>> DEBUG SCORES:", s.sarcasm, s.complaint, s.politeness, s.cues)

    # 🧩 Failsafe: asegurar estructura de retorno completa
    if not isinstance(s.cues, dict):
        s.cues = {"complaint": [], "sarcasm": [], "politeness": []}

    if not summary or not isinstance(summary, dict):
        summary = {
            "version": "v1.4.1",
            "scores": {
                "complaint": round(s.complaint, 2),
                "sarcasm": round(s.sarcasm, 2),
                "politeness": round(s.politeness, 2),
                "threshold": THRESHOLDS.get("complaint", 1.3)
            },
            "cues": s.cues,
            "priority_rule": "reclamo prevalece sobre cortesía"
        }

    if response is None:
        response = "No se detectó una intención clara, pero puedo derivar tu caso a un asesor humano."

    return {"agent_response": response, "should_escalate": escalate, "summary": summary}


