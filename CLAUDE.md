# Aura Organic Growth — Sistema de diagnóstico y crecimiento orgánico

Proyecto de Aura Studio para vender optimización web (velocidad), SEO,
GEO/AEO y landings por plantilla a pymes de LATAM. Se construye sobre
`aura-lead-intelligence`, que se usa en **solo lectura** y no se modifica.

> Estado: axioma y misión aprobados por Cristina (2026-09-28). Principios en
> borrador.

## Axioma

**Todo negocio puede crecer en tiempos de IA.**

Es la única verdad del producto y no se discute. Hereda el axioma de Aura:
*todos y todas podemos hacer ventas exitosas, analizando, escuchando y
comprendiendo.*

## Misión

**Ayudamos a crecer negocios en tiempos de IA.**

Antes de construir o vender algo, preguntar: ¿esto ayuda a que este negocio
crezca en tiempos de IA, y lo podemos demostrar con sus datos? Si no, no se
hace.

## Principios

1. **Medir antes de opinar.** Nada se afirma sin una medición o una cita
   del sitio, con fecha. Show, don't tell: el primer email muestra SUS datos.
2. **El problema correcto antes que la solución.** Doble diamante: primero
   descubrir y definir; después desarrollar y entregar. Nunca se vende una
   solución sin diagnóstico.
3. **Consecuencia comercial o no se dice.** Cada hallazgo técnico se
   traduce a lo que le cuesta al negocio: clientes que se van, leads
   perdidos, no aparecer cuando alguien pregunta a una IA.
4. **Prometer entregables, medir resultados.** Se garantiza la métrica
   técnica (LCP ≤ 2,5 s o se sigue sin costo). El resultado de negocio se
   mide contra una línea base, nunca se promete.
5. **Honestidad radical.** Sin casos propios, se dice. Casos de terceros,
   siempre con enlace. Nada de sellos, reseñas ni cifras falsas.
6. **People trust people.** El sistema diagnostica y redacta; una persona
   aprueba, firma y envía.
7. **Primero no dañar.** Ningún cambio llega al sitio real sin respaldo,
   staging, capturas de antes y después, y aprobación del cliente.

## Doble diamante (cómo se trabaja cada cliente)

| Fase | Qué se hace | Entregable | Métrica |
|---|---|---|---|
| 1. Descubrir | Velocidad, auditoría GEO/SEO, prueba con IA, reseñas, formulario/CRM | Diagnóstico con datos reales | Solo datos medidos |
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

## Reglas que no cambian

- **No inventar datos.** Un dato falso invalida el diagnóstico completo.
  Si algo no se pudo medir, se marca como tal.
- **«Falta X» entra solo desde la página renderizada.** Title, H1, meta
  description, dirección y precio se comprueban con Playwright antes de
  entrar a la ficha. El HTML crudo no alcanza. Si el dato aparece al
  renderizar, no entra como ausencia: se anota «aparece solo con JavaScript»
  y la consecuencia es para los bots de IA que no ejecutan JavaScript. La
  indexación en Google queda en «sin dato» si no hay Search Console.
- **No prometer rankings ni aparición en IA.** Google lo dice: "No one can
  guarantee a #1 ranking on Google".
- **No vender lo que no es estándar:** `/.well-known/ai.txt`, `/ai/*.json`,
  WebMCP ni cifras sin fuente como "+40% de visibilidad". La FAQ se vende
  como contenido útil, no como resultado enriquecido (Google los eliminó el
  2026-05-07).
- **Accesos mínimos y revocables:** usuario propio o contraseña de
  aplicación, nunca la contraseña del dueño. Se revocan al terminar.
- **Respaldo, staging, un cambio a la vez, capturas y aprobación** antes de
  producción. Si algo se rompe, se vuelve atrás.
- **Bibliotecas de anuncios solo a mano.** Meta y Google prohíben la
  recolección automatizada; Cristina navega y pega URLs en un CSV.
- **Enviar requiere confirmación de Cristina** cada vez. Emails inferidos no
  verificados nunca se usan.
- **Datos personales** de decisores bajo la ley de protección de datos
  (Ley 1581 en Colombia). Datos de empresas, sí.
- **`aura-lead-intelligence` es de solo lectura.** Se importa, no se copia
  ni se modifica. El corpus (`corpus/`) y las skills
  `redaccion-primer-contacto-aura` e `hipotesis-outbound` se leen de ahí.
  No se copian ni se les mezcla material externo.
- **Ficha interna, nunca al cliente:** capacidad de pago, valor en juego
  por industria, madurez digital, temperatura, costo de cambio y precio.
  La necesidad se redacta como «lo que hacen los mejores de su industria»
  (`corpus/adenda-brecha-segura.md`). Los precios de lanzamiento (primeros
  3 clientes) viven en el perfil: velocidad USD 400, SEO+GEO USD 500/mes,
  landing USD 250 + 25/mes. `ticket_por_industria` queda en «sin dato»
  hasta que Cristina lo defina. La hipótesis activa del período es una:
  «pega H1».
- **Lote:** los 10 leads con mejor score en Supabase, sin PFS. Se guarda
  el país de cada empresa tal como está en la ficha; si falta, «sin dato».
- **Places:** una Text Search por lead, la ficha de Google. Sin contexto
  de lugar.
- **Cada borrador guarda medición.** Hipótesis, tipo de apertura
  (`riesgo` / `oportunidad` / `esfuerzo` / `dato`), llamado a la acción,
  industria, `fecha_envio` (vacía hasta que Cristina envía desde Gmail) y
  `fecha_reunion` (vacía hasta que haya agenda). Sirve para ver después qué
  mensaje funciona y cuánto tarda cada industria en agendar. El dashboard
  no se construye todavía.
- **Landings por plantilla:** vista previa privada; nunca se publican con la
  marca ajena ni con fotos que no son nuestras.

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

**Definición de terminado por fase:** Descubrir = todas las mediciones con
fecha o marcadas "sin dato". Definir = 5 hallazgos con consecuencia y línea
base registrada. Desarrollar = staging aprobado con capturas. Entregar =
producción medida contra la línea base e informe enviado.

## Productos

1. Optimización de velocidad (con garantía técnica).
2. SEO completo: técnico, on-page, contenido y local. La auditoría rastrea
   todo el sitio (advertools, MIT): titles, meta descriptions, H1-H6, slugs,
   canonical, hreflang, estado HTTP, redirecciones, enlaces rotos e
   internos, sitemap vs. páginas rastreadas, duplicados, contenido delgado,
   blog y frescura, imágenes (peso, formato, alt) y palabras clave que el
   sitio ataca. Volumen de búsqueda y posiciones reales solo con Search
   Console del cliente o API paga; sin eso, se dice "sin dato".
3. GEO/AEO (prueba en vivo con IA como gancho; reputación y menciones de
   autoridad, según Cherep et al., arXiv 2509.25609).
4. Landings por plantilla por industria para negocios sin web. Leads desde
   Google Maps; Cristina elige en el front qué tipo de empresa buscar (el
   sistema no filtra por su cuenta). Contacto por WhatsApp, manual.
   Pendiente, no es el foco actual.
5. (Luego) Fichas de inteligencia de compra por industria.

## Decisiones abiertas (Cristina)

- Aprobar o reescribir el axioma y los principios.
- Tarifa y precio de los paquetes.
- Qué producto va primero en el lote de 20.
- Si hay casos propios de SEO de trabajos anteriores.
