"""Rastreo e indexación: sitemap, canonical, noindex, enlaces rotos, redirecciones,
parámetros, huérfanas, profundidad y duplicados exactos.

Solo HTML sin JavaScript: un enlace que el sitio arma con JavaScript no se ve aquí,
por eso huérfanas y profundidad quedan como «inferido».
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from urllib.parse import urlsplit, urlunsplit

from aura_organic_growth.auditoria_seo.plantillas import es_paginacion, parametros, plantilla
from aura_organic_growth.auditoria_seo.robots import permitido
from aura_organic_growth.auditoria_seo.rastreo import TEMPORALES, normalizar

GOOGLE = "Google"
INTERNO = "criterio interno de Aura"
F_SITEMAP = "https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap"
F_CANONICAL = "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
F_NOINDEX = "https://developers.google.com/search/docs/crawling-indexing/block-indexing"
F_REDIRECCION = "https://developers.google.com/search/docs/crawling-indexing/301-redirects"
F_HTTP = "https://developers.google.com/search/docs/crawling-indexing/http-network-errors"
F_FACETAS = "https://developers.google.com/crawling/docs/faceted-navigation"
F_ENLACES = "https://developers.google.com/search/docs/crawling-indexing/links-crawlable"

MAX_PROFUNDIDAD = 3
COBERTURA_MINIMA = 0.95
MIN_PALABRAS_DUPLICADO = 50
EJEMPLOS = 5
SIN_INDEXAR = {"transaccional", "busqueda"}

ORDEN = [
    "sitemap_con_error", "enlaces_rotos", "sitemap_noindex", "sitemap_bloqueada", "canonical_roto",
    "parametros_indexables", "producto_en_coleccion", "duplicados_exactos", "sitemap_no_canonica",
    "fuera_del_sitemap", "huerfanas", "profundas", "sitemap_redirige", "enlaces_a_redireccion",
    "cadenas_redireccion", "paginas_noindex", "canonical_multiple", "sin_canonical",
]


def sin_query(url: str) -> str:
    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))


def pendientes(
    paginas: list[dict],
    plataforma_sitio: str,
    *,
    tope: int = 3000,
    por_parametro: int = 20,
) -> list[str]:
    """Enlaces internos y canonicals que no se rastrearon y hay que verificar."""
    rastreadas = {p["url"] for p in paginas} | {p["pedida"] for p in paginas}
    limpias: list[str] = []
    con_query: dict[str, list[str]] = defaultdict(list)
    vistos: set[str] = set()
    for pagina in paginas:
        candidatos = [destino for destino, _ in pagina["enlaces"]] + pagina["canonical"]
        for destino in candidatos:
            if destino in rastreadas or destino in vistos:
                continue
            vistos.add(destino)
            nombres = [nombre for nombre, tipo in parametros(destino) if tipo != "pagina"]
            if not nombres:
                limpias.append(destino)
            elif len(con_query[nombres[0]]) < por_parametro:
                con_query[nombres[0]].append(destino)
    muestra = [url for urls in con_query.values() for url in urls]
    return limpias[: max(tope - len(muestra), 0)] + muestra


class _Estados:
    """Estado de una URL: rastreada, verificada o desconocida."""

    def __init__(self, paginas: list[dict], verificadas: dict[str, dict]):
        self.rastreo = {}
        for pagina in paginas:
            self.rastreo[pagina["url"]] = pagina
            self.rastreo.setdefault(pagina["pedida"], pagina)
        self.verificadas = verificadas
        self.no_determinables: set[str] = set()

    def de(self, url: str) -> dict | None:
        """None si no se sabe: sin rastrear, servidor que limita (429/503) o conexión caída."""
        pagina = self.rastreo.get(url)
        if pagina is not None and (pagina["status"] in TEMPORALES or (pagina["status"] is None and pagina["error"])):
            self.no_determinables.add(url)
            pagina = None
            if url not in self.verificadas:
                return None
        if pagina is not None:
            redirigida = pagina["pedida"] == url and pagina["url"] != url
            return {
                "status": pagina["status"],
                "final": pagina["url"],
                "cadena": pagina["redirecciones"] if redirigida else [],
                "canonical": pagina["canonical"],
                "noindex": pagina["noindex"],
                "error": pagina["error"],
                "fuente": "rastreo",
            }
        verificada = self.verificadas.get(url)
        if verificada is None:
            return None
        if verificada.get("estado") == "bloqueada por robots":
            return {"bloqueada": True, "fuente": "verificacion"}
        if verificada.get("estado") in ("limitada", "error"):
            self.no_determinables.add(url)
            return None
        return {
            "status": verificada.get("status"),
            "final": verificada.get("final", url),
            "cadena": verificada.get("cadena", []),
            "canonical": verificada.get("canonical", []),
            "noindex": verificada.get("noindex", False),
            "error": verificada.get("error", ""),
            "fuente": "verificacion",
        }


def _indexable(estado: dict | None) -> bool:
    return bool(estado) and estado.get("status") == 200 and not estado.get("noindex") and not estado.get("cadena")


def _canonical_propio(estado: dict) -> bool:
    canonical = estado.get("canonical") or []
    return not canonical or canonical == [estado.get("final")]


def _hallazgo(
    clave: str,
    titulo: str,
    filas: list[dict],
    *,
    base: int,
    plataforma_sitio: str,
    criterio: str,
    origen: str,
    fuente: str | None,
    consecuencia: str,
    nivel: str = "observado",
) -> dict | None:
    if not filas:
        return None
    plantillas = Counter(plantilla(fila["url"], plataforma_sitio) for fila in filas)
    return {
        "id": clave,
        "titulo": titulo,
        "nivel": nivel,
        "afectadas": len(filas),
        "base": base,
        "por_plantilla": dict(plantillas.most_common()),
        "alcance": "plantilla" if plantillas.most_common(1)[0][1] >= max(10, len(filas) // 2) else "sitio",
        "ejemplos": filas[:EJEMPLOS],
        "criterio": criterio,
        "origen_criterio": origen,
        "fuente": fuente,
        "consecuencia": consecuencia,
    }


def _entrantes(paginas: list[dict]) -> dict[str, list]:
    """destino -> [páginas que lo enlazan, hasta 3 ejemplos]."""
    entrantes: dict[str, list] = {}
    for pagina in paginas:
        if pagina["status"] != 200:
            continue
        for destino in {d for d, _ in pagina["enlaces"]}:
            if destino == pagina["url"]:
                continue
            fila = entrantes.setdefault(destino, [0, []])
            fila[0] += 1
            if len(fila[1]) < 3:
                fila[1].append(pagina["url"])
    return entrantes


def _profundidades(paginas: list[dict], portada: str) -> dict[str, int]:
    alias = {p["pedida"]: p["url"] for p in paginas}
    vecinos = {p["url"]: [alias.get(d, d) for d, seguir in p["enlaces"] if seguir] for p in paginas}
    inicio = alias.get(portada, portada)
    distancia = {inicio: 0}
    cola = deque([inicio])
    while cola:
        actual = cola.popleft()
        for siguiente in vecinos.get(actual, []):
            if siguiente not in distancia:
                distancia[siguiente] = distancia[actual] + 1
                cola.append(siguiente)
    return distancia


def analizar(
    paginas: list[dict],
    sitemap: list[str],
    verificadas: dict[str, dict],
    reglas: list,
    *,
    portada: str,
    plataforma_sitio: str = "otra",
) -> dict:
    estados = _Estados(paginas, verificadas)
    en_sitemap = [normalizar(url) for url in sitemap]
    conjunto_sitemap = set(en_sitemap)
    html = [p for p in paginas if p["status"] == 200 and (not p["tipo"] or "html" in p["tipo"])]
    entrantes = _entrantes(paginas)
    comun = {"plataforma_sitio": plataforma_sitio}
    hallazgos: list[dict | None] = []
    tablas: dict[str, list[dict]] = {}

    error, redirige, noindex_sm, no_canonica, bloqueada, sin_rastrear = [], [], [], [], [], []
    for url in en_sitemap:
        estado = estados.de(url)
        if estado is None:
            (bloqueada if not permitido(url, reglas) else sin_rastrear).append({"url": url})
            continue
        if estado.get("bloqueada"):
            bloqueada.append({"url": url})
        elif estado["error"] or (estado["status"] or 0) >= 400:
            error.append({"url": url, "status": estado["status"], "error": estado["error"]})
        elif estado["cadena"]:
            redirige.append({"url": url, "final": estado["final"], "saltos": len(estado["cadena"])})
        elif estado["noindex"]:
            noindex_sm.append({"url": url})
        elif not _canonical_propio(estado):
            no_canonica.append({"url": url, "canonical": " ".join(estado["canonical"])})
    total_sm = len(en_sitemap)
    hallazgos += [
        _hallazgo("sitemap_con_error", "URLs del sitemap que responden con error", error, base=total_sm,
                  criterio="El sitemap debe listar las URLs que se quieren en Google; una página con error 4xx o 5xx no se indexa.",
                  origen=GOOGLE, fuente=F_HTTP, consecuencia="Un cliente que llega a esa URL ve un error y Google gasta rastreo en ella.", **comun),
        _hallazgo("sitemap_noindex", "URLs del sitemap marcadas noindex", noindex_sm, base=total_sm,
                  criterio="Una página con noindex no aparece en Google; listarla en el sitemap manda señales contradictorias.",
                  origen=GOOGLE, fuente=F_NOINDEX, consecuencia="Páginas que el sitio ofrece a Google y a la vez le pide no mostrar.", **comun),
        _hallazgo("sitemap_bloqueada", "URLs del sitemap bloqueadas por robots.txt", bloqueada, base=total_sm,
                  criterio="Google no rastrea lo que robots.txt bloquea, aunque esté en el sitemap.",
                  origen=GOOGLE, fuente=F_SITEMAP, consecuencia="Google no puede leer esas páginas.", **comun),
        _hallazgo("sitemap_no_canonica", "URLs del sitemap cuyo canonical apunta a otra URL", no_canonica, base=total_sm,
                  criterio="El sitemap debe listar solo la versión canónica de cada página.",
                  origen=GOOGLE, fuente=F_CANONICAL, consecuencia="Google recibe dos versiones de la misma página y elige él cuál mostrar.", **comun),
        _hallazgo("sitemap_redirige", "URLs del sitemap que redirigen", redirige, base=total_sm,
                  criterio="El sitemap debe listar la URL final, no una que redirige.",
                  origen=GOOGLE, fuente=F_SITEMAP, consecuencia="Google pierde rastreo siguiendo redirecciones.", **comun),
    ]
    tablas.update({"sitemap_con_error": error, "sitemap_redirige": redirige, "sitemap_noindex": noindex_sm,
                   "sitemap_no_canonica": no_canonica, "sitemap_bloqueada": bloqueada})

    noindex = [{"url": p["url"], "robots": p["robots"]} for p in html if p["noindex"]]
    sin_canonical = [{"url": p["url"]} for p in html if not p["canonical"] and not p["noindex"]]
    multiple = [{"url": p["url"], "canonical": " ".join(p["canonical"])} for p in html if len(p["canonical"]) > 1]
    roto = []
    for pagina in html:
        if len(pagina["canonical"]) != 1 or pagina["canonical"][0] == pagina["url"]:
            continue
        objetivo = pagina["canonical"][0]
        estado = estados.de(objetivo)
        if estado is None:
            continue
        if estado.get("bloqueada"):
            motivo = "bloqueada por robots"
        elif estado["status"] != 200:
            motivo = f"responde {estado['status'] or estado['error']}"
        elif estado["cadena"]:
            motivo = "redirige"
        elif estado["noindex"]:
            motivo = "noindex"
        else:
            continue
        roto.append({"url": pagina["url"], "canonical": objetivo, "motivo": motivo})
    hallazgos += [
        _hallazgo("canonical_roto", "Canonical que apunta a una URL que no sirve", roto, base=len(html),
                  criterio="El canonical debe apuntar a una URL que responde 200 y es indexable.",
                  origen=GOOGLE, fuente=F_CANONICAL, consecuencia="Google puede ignorar la indicación y elegir otra versión, o ninguna.", **comun),
        _hallazgo("paginas_noindex", "Páginas marcadas noindex", noindex, base=len(html),
                  criterio="Una página con noindex no aparece en Google. Hay que confirmar que sea intencional.",
                  origen=GOOGLE, fuente=F_NOINDEX, consecuencia="Si alguna debía venderse en Google, hoy no aparece.", **comun),
        _hallazgo("canonical_multiple", "Páginas con más de un canonical distinto", multiple, base=len(html),
                  criterio="No se deben declarar URLs canónicas distintas para la misma página.",
                  origen=GOOGLE, fuente=F_CANONICAL, consecuencia="Google puede ignorar todas las indicaciones.", **comun),
        _hallazgo("sin_canonical", "Páginas indexables sin canonical", sin_canonical, base=len(html),
                  criterio="Google recomienda declarar el canonical; no es obligatorio.",
                  origen=GOOGLE, fuente=F_CANONICAL, consecuencia="Con versiones duplicadas, Google elige él cuál mostrar.", **comun),
    ]
    tablas.update({"paginas_noindex": noindex, "sin_canonical": sin_canonical,
                   "canonical_multiple": multiple, "canonical_roto": roto})

    rotos, a_redireccion, cadenas, fuera, sin_verificar = [], [], [], [], 0
    grupos: dict[tuple[str, str], dict] = {}
    en_coleccion = {"enlazadas": 0, "verificadas": 0, "filas": []}
    for destino, (cuantas, origenes) in entrantes.items():
        estado = estados.de(destino)
        nombres = [(n, t) for n, t in parametros(destino) if t != "pagina"]
        if nombres:
            nombre, tipo = nombres[0]
            grupo = grupos.setdefault((nombre, tipo), {
                "parametro": nombre, "tipo": tipo, "urls_enlazadas": 0, "bloqueadas_robots": 0,
                "verificadas": 0, "indexables": 0, "canonical_a_url_limpia": 0, "noindex": 0, "ejemplo": destino,
            })
            grupo["urls_enlazadas"] += 1
            if not permitido(destino, reglas):
                grupo["bloqueadas_robots"] += 1
            elif estado and not estado.get("bloqueada") and estado.get("status") == 200:
                grupo["verificadas"] += 1
                if estado["noindex"]:
                    grupo["noindex"] += 1
                elif estado["canonical"] and estado["canonical"][0] == sin_query(destino):
                    grupo["canonical_a_url_limpia"] += 1
                elif _canonical_propio(estado):
                    grupo["indexables"] += 1
        if plataforma_sitio == "shopify" and plantilla(destino, "shopify") == "producto_en_coleccion":
            en_coleccion["enlazadas"] += 1
            if estado and estado.get("status") == 200:
                en_coleccion["verificadas"] += 1
                propio = "/products/" + destino.rsplit("/products/", 1)[1].split("?")[0]
                if not any(urlsplit(c).path == propio for c in estado["canonical"]):
                    en_coleccion["filas"].append({"url": destino, "canonical": " ".join(estado["canonical"]) or "sin canonical"})
        if estado is None:
            sin_verificar += 1
            continue
        if estado.get("bloqueada"):
            continue
        if estado["error"] or (estado["status"] or 0) >= 400:
            rotos.append({"url": destino, "status": estado["status"], "error": estado["error"],
                          "paginas_que_enlazan": cuantas, "ejemplos_origen": " ".join(origenes)})
        elif estado["cadena"]:
            a_redireccion.append({"url": destino, "final": estado["final"], "paginas_que_enlazan": cuantas})
            if len(estado["cadena"]) >= 2:
                cadenas.append({"url": destino, "saltos": len(estado["cadena"]), "final": estado["final"],
                                "cadena": " > ".join(f"{u} ({c})" for u, c in estado["cadena"])})
        elif (not nombres and not es_paginacion(destino) and destino not in conjunto_sitemap
              and _indexable(estado) and _canonical_propio(estado)
              and plantilla(destino, plataforma_sitio) not in SIN_INDEXAR):
            fuera.append({"url": destino, "paginas_que_enlazan": cuantas})
    for url in en_sitemap:
        estado = estados.de(url)
        if estado and len(estado.get("cadena") or []) >= 2 and not any(c["url"] == url for c in cadenas):
            cadenas.append({"url": url, "saltos": len(estado["cadena"]), "final": estado["final"],
                            "cadena": " > ".join(f"{u} ({c})" for u, c in estado["cadena"])})
    parametros_indexables = [
        {"url": g["ejemplo"], "parametro": g["parametro"], "tipo": g["tipo"],
         "urls_enlazadas": g["urls_enlazadas"], "indexables_verificadas": g["indexables"], "verificadas": g["verificadas"]}
        for g in grupos.values() if g["tipo"] != "pagina" and g["indexables"]
    ]
    total_enlazadas = len(entrantes)
    hallazgos += [
        _hallazgo("enlaces_rotos", "Enlaces internos que llevan a un error", rotos, base=total_enlazadas,
                  criterio="Una URL que responde 4xx o 5xx no se indexa y corta el camino de quien la abre.",
                  origen=GOOGLE, fuente=F_HTTP, consecuencia="Clientes que hacen clic y llegan a un error, dentro del propio sitio.", **comun),
        _hallazgo("parametros_indexables", "Filtros, orden o búsquedas que Google puede rastrear e indexar", parametros_indexables,
                  base=len(grupos), criterio="Google recomienda bloquear en robots.txt los filtros que no se quieren en el buscador, o tratarlos con su guía de navegación facetada.",
                  origen=GOOGLE, fuente=F_FACETAS, consecuencia="Miles de variantes compiten con la página principal y gastan el rastreo de Google.",
                  nivel="inferido", **comun),
        _hallazgo("producto_en_coleccion", "Productos enlazados por una ruta de colección sin canonical al producto", en_coleccion["filas"],
                  base=en_coleccion["verificadas"], criterio="Cada producto debe consolidar sus rutas duplicadas en una sola URL canónica.",
                  origen=GOOGLE, fuente=F_CANONICAL, consecuencia="El mismo producto aparece en varias URLs que compiten entre sí.", **comun),
        _hallazgo("fuera_del_sitemap", "Páginas indexables que el sitemap no trae", fuera, base=total_enlazadas,
                  criterio="El sitemap debe incluir las URLs que se quieren en Google.",
                  origen=GOOGLE, fuente=F_SITEMAP, consecuencia="Google las descubre más tarde, o solo por enlaces.", **comun),
        _hallazgo("enlaces_a_redireccion", "Enlaces internos que pasan por una redirección", a_redireccion, base=total_enlazadas,
                  criterio="Enlazar directo a la URL final. Cada salto suma tiempo de carga.",
                  origen=INTERNO, fuente=F_REDIRECCION, consecuencia="Cada clic tarda más y Google gasta rastreo.", **comun),
        _hallazgo("cadenas_redireccion", "Redirecciones en cadena (2 saltos o más)", cadenas, base=total_enlazadas + total_sm,
                  criterio="Un solo salto. Google sigue hasta 10, pero cada salto suma latencia y riesgo de corte.",
                  origen=INTERNO, fuente=F_REDIRECCION, consecuencia="Páginas que tardan más en abrir y que Google puede dejar de seguir.", **comun),
    ]
    tablas.update({"enlaces_rotos": rotos, "enlaces_a_redireccion": a_redireccion, "cadenas_redireccion": cadenas,
                   "fuera_del_sitemap": fuera, "parametros": list(grupos.values()),
                   "producto_en_coleccion": en_coleccion["filas"]})

    distancia = _profundidades(paginas, portada)
    alias = {p["pedida"]: p["url"] for p in paginas}
    huerfanas, profundas, inalcanzables = [], [], 0
    for url in en_sitemap:
        estado = estados.de(url)
        if not _indexable(estado):
            continue
        real = alias.get(url, url)
        if real == alias.get(portada, portada):
            continue
        if url not in entrantes and real not in entrantes:
            huerfanas.append({"url": url})
        elif real not in distancia:
            inalcanzables += 1
        elif distancia[real] > MAX_PROFUNDIDAD:
            profundas.append({"url": url, "clics_desde_portada": distancia[real]})
    cobertura = 1 - len(sin_rastrear) / total_sm if total_sm else 0.0
    if cobertura < COBERTURA_MINIMA:
        huerfanas, profundas = [], []
    hallazgos += [
        _hallazgo("huerfanas", "Páginas del sitemap sin ningún enlace interno", huerfanas, base=total_sm,
                  criterio="Google descubre páginas siguiendo enlaces; una página sin enlaces internos depende solo del sitemap.",
                  origen=GOOGLE, fuente=F_ENLACES, consecuencia="Ni Google ni el cliente llegan navegando a esas páginas.",
                  nivel="inferido", **comun),
        _hallazgo("profundas", f"Páginas a más de {MAX_PROFUNDIDAD} clics de la portada", profundas, base=total_sm,
                  criterio=f"Las páginas que venden, a {MAX_PROFUNDIDAD} clics o menos. Google no fija un número.",
                  origen=INTERNO, fuente=None, consecuencia="Cuanto más hondo, menos se rastrea y menos se encuentra navegando.",
                  nivel="inferido", **comun),
    ]
    tablas.update({"huerfanas": huerfanas, "profundas": profundas})

    grupos_huella: dict[str, list[dict]] = defaultdict(list)
    for pagina in html:
        if pagina["huella"] and pagina["palabras"] >= MIN_PALABRAS_DUPLICADO and not pagina["noindex"]:
            grupos_huella[pagina["huella"]].append(pagina)
    duplicados = []
    for numero, (huella, miembros) in enumerate(grupos_huella.items(), start=1):
        destinos = {(p["canonical"][0] if p["canonical"] else p["url"]) for p in miembros}
        if len(miembros) > 1 and len(destinos) > 1:
            duplicados.extend({"url": p["url"], "grupo": numero, "copias": len(miembros)} for p in miembros)
    hallazgos.append(_hallazgo(
        "duplicados_exactos", "Páginas con el mismo texto y canonicals distintos", duplicados, base=len(html),
        criterio="Las páginas duplicadas deben consolidarse en una URL canónica.",
        origen=GOOGLE, fuente=F_CANONICAL, consecuencia="Páginas que compiten entre sí por las mismas búsquedas.", **comun,
    ))
    tablas["duplicados_exactos"] = duplicados

    encontrados = [h for h in hallazgos if h]
    encontrados.sort(key=lambda h: ORDEN.index(h["id"]))
    return {
        "resumen": {
            "urls_en_sitemap": total_sm,
            "paginas_rastreadas": len(paginas),
            "html_200": len(html),
            "estados": dict(Counter(str(p["status"]) for p in paginas).most_common()),
            "por_plantilla": dict(Counter(plantilla(p["url"], plataforma_sitio) for p in paginas).most_common()),
            "sitemap_sin_rastrear": len(sin_rastrear),
            "cobertura_sitemap": round(cobertura, 3),
            "huerfanas_y_profundidad": (
                "medidas" if cobertura >= COBERTURA_MINIMA
                else f"no determinable: el rastreo cubrió {cobertura:.0%} del sitemap"
            ),
            "enlaces_internos_distintos": total_enlazadas,
            "enlaces_sin_verificar": sin_verificar,
            "no_determinables": len(estados.no_determinables),
            "inalcanzables_desde_portada": inalcanzables,
            "nota": (
                "Solo HTML sin JavaScript. Huérfanas, profundidad y parámetros quedan como inferido. "
                "Las URLs que el servidor limitó (429/503) o que no respondieron quedan como no determinables, nunca como error."
            ),
        },
        "hallazgos": encontrados,
        "tablas": tablas,
    }
