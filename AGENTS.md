# AGENTS.md — Mapa del repositorio

Este archivo es un mapa, no un reglamento. Dice dónde está cada cosa y cuándo
leerla. Las reglas de negocio viven en `CLAUDE.md` y `docs/`.

## 1. Antes de empezar

1. Ejecuta `./init.sh`. Si sale con código distinto de 0, para y arréglalo.
2. Lee el documento activo en `odd/tasks/` (estado real de la tarea).
3. Trabaja una tarea a la vez; no abras la siguiente sin cerrar la actual.

## 2. Mapa del repositorio

| Archivo o carpeta | Qué contiene | Cuándo leerlo |
|---|---|---|
| `CLAUDE.md` | Axioma, misión, principios y arranque (carga en cada sesión) | Siempre |
| `docs/reglas.md` | Reglas de negocio aprobadas por Cristina | Antes de tocar mediciones, validadores, borradores, precios o lotes |
| `docs/operacion.md` | Doble diamante, métricas, operación, definición de terminado | Al planear o cerrar una fase de trabajo |
| `docs/productos.md` | Productos y decisiones abiertas | Al trabajar en la oferta |
| `odd/tasks/` | Documentos de tarea (estado, checklist, evidencias); espejo en Engram | Al empezar y al cerrar cada tarea |
| `progress/` | `current.md` (sesión activa), `history.md` (bitácora) y resultados de subagentes | Al delegar o cerrar sesión |
| `instrucciones/` | Instrucciones para el Grok Bot (contactos y borradores) | Al cambiar el flujo con el bot |
| `scripts/` | Comandos de línea: auditar, correr lote, cargar y validar borradores, IA, labs | Al ejecutar o modificar un flujo de punta a punta |
| `src/aura_organic_growth/` | Paquete Python (ver módulos abajo) | Al implementar o corregir lógica |
| `tests/` | Pruebas pytest, una por módulo, sin llamadas reales a APIs | Al cambiar cualquier módulo |
| `supabase/` | Migraciones SQL | Al cambiar el esquema de datos |
| `init.sh` | Puerta de inicio y cierre (entorno, archivos, pruebas, seguridad) | Al empezar y antes de dar algo por hecho |
| `.claude/` | `settings.json` y hooks (pruebas tras editar, `init.sh` al parar) | Al ajustar el arnés |
| `.cursor/` | Regla `rules/arnes.mdc` (lee CLAUDE.md y AGENTS.md) y hook `stop` que corre `init.sh` en Cursor | Al ajustar el arnés para Cursor |
| `CHECKPOINTS.md` | Lista verificable de cierre | Antes de cerrar la sesión |

Módulos principales de `src/aura_organic_growth/`: `lote` y `cruce` (selección
y cruce de leads), `madurez`, `ia` y `legibilidad_ia` (prueba en vivo con IA y
lectura del sitio), `crux`, `serp`, `serper`, `labs`, `competidores`,
`paginas`, `entidad`, `senales`, `places_ficha`, `render` (mediciones),
`hallazgos`, `borrador`, `validar_borrador`, `oferta`, `valor`,
`observados`, `staging`, `supabase_rest`, `lead_intel` (puente de solo
lectura a `aura-lead-intelligence`) y `auditoria_seo/`.

Dos análisis distintos, no confundirlos:

- `scripts/correr_lote.py` y `scripts/ia_lote.py`: el diagnóstico del primer
  contacto (prueba con IA, lectura para IA, velocidad, madurez). Rápido.
- `scripts/auditoria_seo_lote.py`: la auditoría SEO profunda de sitio completo
  (rastreo de todo el sitemap; canonical, noindex, duplicados, enlaces rotos,
  redirecciones, huérfanas, profundidad). Es la que se pide como «análisis
  profundo» o «como el de Flamingo». Los sitios que tardarían más de 5 minutos
  van al final. Un solo sitio: `scripts/auditoria_seo.py URL`.

## 3. Reglas duras

- Ninguna tarea está terminada sin `./init.sh` en verde.
- Cero secretos en commits: `.env` y `data/` están en `.gitignore`.
- `aura-lead-intelligence` es de solo lectura: se importa, no se modifica.
- Nunca inventar datos: lo no medido se marca «sin dato».

## 4. Subagentes

- El orquestador delega; los subagentes ejecutan una unidad acotada.
- Cada subagente escribe su resultado en `progress/<tipo>_<tema>.md` y
  responde solo `done -> progress/<archivo>` o `blocked -> <motivo>`.
- El estado de las tareas vive en `odd/tasks/` (y su espejo en Engram), no
  en `progress/`. `progress/` es solo para salidas de subagentes e historial.

## 5. Cierre de sesión

1. `./init.sh` en verde.
2. Actualizar los checkboxes de `odd/tasks/` con evidencia (comando y resultado, hash de commit).
3. Añadir una línea a `progress/history.md`.
4. Commit por unidad de trabajo con Conventional Commits.
