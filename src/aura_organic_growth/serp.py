"""Búsquedas comerciales en la cola estándar de DataForSEO.

Sin DATAFORSEO_LOGIN y DATAFORSEO_PASSWORD no se llama a la API: queda
«sin dato». No se inventan consultas para llegar a 20.
"""

from __future__ import annotations

import os
from datetime import date

COLA = "https://api.dataforseo.com/v3/serp/google/organic/task_post"
COSTO_REFERENCIA_USD = 0.0006
PRIORIDAD_ESTANDAR = 1
TOPE = 30


def armar_consultas(servicios: list[str], ciudad: str) -> list[dict]:
    ciudad = str(ciudad or "").strip()
    vistos: list[dict] = []
    for servicio in servicios:
        nombre = str(servicio or "").strip()
        if not nombre or not ciudad or nombre.casefold() == "sin dato" or ciudad.casefold() == "sin dato":
            continue
        for intencion, texto in (
            ("servicio_ciudad", f"{nombre} en {ciudad}"),
            ("precio", f"precio {nombre}"),
            ("mejor", f"mejor {nombre} en {ciudad}"),
        ):
            vistos.append({"servicio": nombre, "ciudad": ciudad, "intencion": intencion, "consulta": texto})
            if len(vistos) >= TOPE:
                return vistos
    return vistos


def encolar(
    servicios: list[str],
    *,
    ciudad: str,
    pais: str,
    idioma: str = "es",
    dispositivo: str = "desktop",
    hoy: date | None = None,
    session=None,
) -> dict:
    hoy = hoy or date.today()
    consultas = armar_consultas(servicios, ciudad)
    meta = {
        "fecha": hoy.isoformat(),
        "pais": pais or "sin dato",
        "ciudad": ciudad or "sin dato",
        "idioma": idioma,
        "dispositivo": dispositivo,
        "cola": "estandar",
        "costo_referencia_usd": COSTO_REFERENCIA_USD,
    }
    login = os.getenv("DATAFORSEO_LOGIN", "").strip()
    password = os.getenv("DATAFORSEO_PASSWORD", "").strip()
    if not consultas:
        return {**meta, "status": "sin dato", "razon": "sin servicio o sin ciudad observados", "enviadas": []}
    if not login or not password:
        return {**meta, "status": "sin dato", "razon": "sin DATAFORSEO_LOGIN", "enviadas": []}
    cuerpo = [
        {
            "keyword": item["consulta"],
            "location_name": pais,
            "language_code": idioma,
            "device": dispositivo,
            "priority": PRIORIDAD_ESTANDAR,
            "tag": item["intencion"],
        }
        for item in consultas
    ]
    http = session or __import__("requests")
    resp = http.post(COLA, json=cuerpo, auth=(login, password), timeout=40)
    if resp.status_code != 200:
        return {**meta, "status": "sin dato", "razon": f"http_{resp.status_code}", "enviadas": []}
    data = resp.json() or {}
    tareas = data.get("tasks") or []
    enviadas = []
    for item, tarea in zip(consultas, tareas):
        enviadas.append({
            **item,
            "task_id": tarea.get("id"),
            "costo_usd": tarea.get("cost"),
        })
    return {**meta, "status": "en_cola", "enviadas": enviadas, "costo_usd": data.get("cost")}
