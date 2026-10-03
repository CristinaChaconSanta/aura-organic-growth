# Operación, doble diamante y métricas

## Doble diamante (cómo se trabaja cada cliente)

| Fase | Qué se hace | Entregable | Métrica |
|---|---|---|---|
| 1. Descubrir | Primero la prueba en vivo con IA (ChatGPT y Gemini) y la lectura del sitio para IA; después velocidad, búsquedas, auditoría GEO/SEO, reseñas, formulario/CRM | Diagnóstico con datos reales | Solo datos medidos |
| 2. Definir | Elegir los 5 problemas que más cuestan | Ficha con hallazgos y consecuencia comercial | Línea base: LCP, leads/mes, mención en IA |
| 3. Desarrollar | Proponer y probar en staging | Propuesta + cambios en staging + capturas | Mejora medida en staging |
| 4. Entregar | Publicar lo aprobado y medir | Cambio en producción + informe | LCP ≤ 2,5 s; leads vs. línea base |

Fases 1-2 son el gancho gratuito (primer contacto). Fases 3-4 son el
servicio pagado.

## Métricas

- **Permitidas (con consecuencia de negocio):** LCP e INP frente a los
  umbrales de Google; formularios, llamadas y leads frente a la línea base;
  veredicto de la prueba con IA (invisible / mencionado / citado) y quién
  aparece en su lugar; reseñas y su respuesta.
- **Prohibidas como resultado (cifras de vanidad):** impresiones, puntajes
  de herramientas (ej. "GEO score 72"), tráfico sin conversión, número de
  palabras clave, "visibilidad" sin definición.
- **Métricas propias de Aura:** tasa de respuesta, reuniones y cierres por
  lote de 20 leads, medidas con `hipotesis-outbound`.

## Operación

| Quién | Qué hace |
|---|---|
| Python | Mide (PageSpeed, geo-optimizer-skill, una ficha de Google, tecnologías, formulario). Costo: 0 tokens |
| Grok Bot (cuota de Cursor) | Redacta hallazgos en lenguaje de negocio y borradores, vía tabla de staging en Supabase |
| Validadores en Python | Verifican que nada se invente, que cada afirmación cite y que no se prometan rankings |
| Claude | Construye y corrige el sistema |
| Cristina | Aprueba, firma, envía y decide precios |

**Cadencia:** lotes de 20 leads por producto; medir respuestas cada semana;
decidir con datos qué producto sigue.

**Orden de Descubrir:** 1) prueba en vivo con IA y 2) lectura del sitio para IA
(`src/aura_organic_growth/ia.py` y `legibilidad_ia.py`), después 3) velocidad y
4) búsquedas. Corre para todo lead con web, también con madurez baja.

**Definición de terminado por fase:** Descubrir = todas las mediciones con
fecha o marcadas "sin dato". Definir = 5 hallazgos con consecuencia y línea
base registrada. Desarrollar = staging aprobado con capturas. Entregar =
producción medida contra la línea base e informe enviado.
