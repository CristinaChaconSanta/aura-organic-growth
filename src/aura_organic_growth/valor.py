"""Valor interno de la oferta web. El modelo propone evidencia; Python calcula.

No usa horas ahorradas: esa cuenta es de automatización. Los precios de
lanzamiento salen de los paquetes del perfil. El ticket por industria queda
en «sin dato» hasta que Cristina lo defina.
"""

from __future__ import annotations

import json
from pathlib import Path

from aura_organic_growth.lead_intel import ORGANIC_ROOT

PERFIL = ORGANIC_ROOT / "profiles" / "aura-organic.json"

TEMPERATURAS = ("in-market probable", "out-of-market", "sin evidencia")
COSTOS = ("alto", "medio", "bajo", "sin evidencia")
MADUREZ = ("baja", "media", "alta", "sin evidencia")

# Disparadores de esta oferta, últimos 6 meses. La pauta solo cuenta si
# Cristina la anotó tras mirar la biblioteca de anuncios a mano.
_SITIO = ("rediseno", "redisen", "migracion", "migro")
_SEDE = ("nueva sede", "sede nueva", "expansion", "nueva oficina")
_LANZAMIENTO = ("lanzamiento", "lanzo", "nuevo producto", "nuevo servicio", "nueva linea")
_VACANTE = ("vacante",)
_VACANTE_AREA = ("marketing", "seo", "contenido")
_PAUTA_MANUAL = ("biblioteca de anuncios", "revise a mano", "revisado a mano")

_CULPA = (
    "estan fallando", "esta fallando", "hacen mal", "hace mal", "su error",
    "no saben", "estan perdiendo", "esta perdiendo", "culp",
)
_CATASTROFE = (
    "van a quebrar", "demasiado tarde", "imposible de recuperar", "es el fin",
)


def _plano(texto: str) -> str:
    return (
        texto.lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )


def hay_trigger(evidencia: str) -> bool:
    e = _plano(evidencia)
    if any(m in e for m in _SITIO + _SEDE + _LANZAMIENTO):
        return True
    if any(m in e for m in _VACANTE) and any(m in e for m in _VACANTE_AREA):
        return True
    return "pauta" in e and any(m in e for m in _PAUTA_MANUAL)


def cargar_perfil(path: Path | None = None) -> dict:
    origen = path or PERFIL
    if not origen.is_file():
        return {"ticket_por_industria": "sin dato", "precios_lanzamiento": {}, "hipotesis_periodo": []}
    data = json.loads(origen.read_text(encoding="utf-8"))
    data.setdefault("ticket_por_industria", "sin dato")
    data.setdefault("precios_lanzamiento", {})
    data.setdefault("hipotesis_periodo", [])
    return data


def hipotesis_activa(profile: dict | None = None) -> str:
    profile = profile if profile is not None else cargar_perfil()
    activas = [h for h in profile.get("hipotesis_periodo") or [] if h.get("activa")]
    if len(activas) != 1:
        return "sin dato"
    return str(activas[0].get("enunciado") or "sin dato")


def precios_lanzamiento(profile: dict) -> dict:
    """Menú de paquetes. No elige paquete para el lead ni usa el ticket por industria."""
    lanzamiento = profile.get("precios_lanzamiento") or {}
    paquetes = lanzamiento.get("paquetes") or {}
    if not paquetes:
        paquetes = "sin dato"
    return {
        "clientes": lanzamiento.get("clientes"),
        "paquetes": paquetes,
        "ticket_por_industria": "sin dato",
    }


def temperatura(propuesta: dict) -> dict:
    valor = str(propuesta.get("temperatura_mercado") or "").strip()
    evidencia = str(propuesta.get("evidencia_temperatura") or "").strip()
    if valor not in TEMPERATURAS:
        valor = "sin evidencia"
    if not evidencia:
        return {
            "temperatura_mercado": "out-of-market" if valor == "in-market probable" else (valor or "sin evidencia"),
            "evidencia_temperatura": "sin evidencia",
        }
    if valor == "in-market probable" and not hay_trigger(evidencia):
        return {
            "temperatura_mercado": "out-of-market",
            "evidencia_temperatura": (
                "Sin trigger de los últimos 6 meses. "
                f"[Degradado — el modelo alegó: {evidencia[:180]}]"
            ),
            "_temperatura_degradada": True,
        }
    return {"temperatura_mercado": valor, "evidencia_temperatura": evidencia}


def _cerrado(propuesta: dict, campo: str, evidencia_campo: str, validos: tuple[str, ...]) -> dict:
    valor = str(propuesta.get(campo) or "").strip().lower()
    evidencia = str(propuesta.get(evidencia_campo) or "").strip()
    if valor not in validos or valor == "sin evidencia" or not evidencia:
        return {campo: "sin evidencia", evidencia_campo: evidencia or "sin evidencia"}
    return {campo: valor, evidencia_campo: evidencia}


def necesidad_industria(propuesta: dict) -> dict:
    """«Lo que hacen los mejores»: factor externo, validación previa, sin culpa."""
    texto = str(propuesta.get("lo_que_hacen_los_mejores") or "").strip()
    validacion = str(propuesta.get("validacion") or "").strip()
    factor = str(propuesta.get("factor_externo") or "").strip()
    evidencia = str(propuesta.get("evidencia_valor") or "").strip()
    bajo = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if not (texto and validacion and factor and evidencia):
        return {"lo_que_hacen_los_mejores": "sin dato", "motivo": "falta validación, factor externo o evidencia"}
    if any(m in bajo for m in _CULPA) or any(m in bajo for m in _CATASTROFE):
        return {"lo_que_hacen_los_mejores": "sin dato", "motivo": "la brecha culpa al lector o es catastrófica"}
    return {
        "lo_que_hacen_los_mejores": texto,
        "validacion": validacion,
        "factor_externo": factor,
        "evidencia": evidencia,
    }


def armar_interno(propuesta: dict, profile: dict | None = None) -> dict:
    """Cinco campos internos. Cualquier precio que haya escrito el modelo se descarta."""
    profile = profile if profile is not None else cargar_perfil()
    industria = str(propuesta.get("industria") or "").strip()
    evidencia_pago = str(propuesta.get("evidencia_capacidad_pago") or "").strip()
    necesidad = necesidad_industria(propuesta)
    return {
        "industria": industria or "sin dato",
        "hipotesis_periodo": hipotesis_activa(profile),
        "precios_lanzamiento": precios_lanzamiento(profile),
        "capacidad_pago": {
            "senales": [str(s) for s in (propuesta.get("senales_capacidad_pago") or []) if str(s).strip()],
            "evidencia": evidencia_pago or "sin evidencia",
            "precio": "sin dato",
        },
        "valor_en_juego": {**necesidad, "precio": "sin dato"},
        "madurez_digital": _cerrado(propuesta, "madurez_digital", "evidencia_madurez", MADUREZ),
        **temperatura(propuesta),
        **_cerrado(propuesta, "costo_cambio_estimado", "evidencia_costo_cambio", COSTOS),
    }


def ficha_cliente(ficha: dict) -> dict:
    """Lo que puede salir. Los campos internos no entran."""
    return {
        "lo_que_entendimos": ficha.get("lo_que_entendimos") or "",
        "resumen": ficha.get("resumen") or "",
        "senales": list(ficha.get("senales") or []),
        "brechas": list(ficha.get("brechas") or []),
        "hallazgos": list(ficha.get("hallazgos") or []),
    }
