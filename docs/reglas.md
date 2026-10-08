# Reglas que no cambian (detalle)

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
  (`corpus/adenda-brecha-segura.md`). Los precios por paquete y la tabla
  de ajuste por país viven en el perfil con estado «pendiente de Cristina»
  hasta que los apruebe. La propuesta es velocidad USD 400, SEO+GEO
  USD 500/mes y landing USD 250 + 25/mes. Mientras sigan pendientes, el
  precio del lead queda en «sin dato». `ticket_por_industria` también.
  La hipótesis activa del período es una: los mensajes con ancla=dato
  tendrán respuestas más sustantivas que ancla=oportunidad.
- **Lote:** los 10 leads con mejor score en Supabase, sin PFS. Se guarda
  el país de cada empresa tal como está en la ficha; si falta, «sin dato».
  Antes de auditar se clasifica la madurez con evidencia (CRM, etiqueta de
  pauta, analítica, blog con fecha de los últimos 6 meses). La madurez se
  anota y no descarta: todo lead con web entra al análisis, también con
  madurez baja o con la portada sin respuesta. Sin web se marca «derivar a
  landing» porque no hay sitio que medir.
- **Places:** una Text Search por lead, la ficha de Google. Sin contexto
  de lugar. Se guarda solo el `place_id`. No se precarga ni se almacena
  el resto del contenido de Places. Si una nota o las reseñas salen al
  prospecto sin mapa, llevan el logo de Google.
- **Prueba en vivo con IA:** DataForSEO LLM Scraper, ChatGPT y Gemini, una
  pregunta de comprador («¿Qué [servicio] me recomiendas en [ciudad], [país]?»)
  solo con servicio y ciudad observados (`observados.py`). USD 0,004 por
  pregunta; con saldo menor a USD 0,10 no se llama y queda «sin dato». Cada
  respuesta guarda fecha, país, idioma, si menciona al lead, a quién recomienda
  y qué fuentes cita. «El lead no está en esa lista» solo si se bajó la página
  citada y se buscó su dominio y su marca. Nunca se promete que una IA lo
  mencione.
- **Lectura del sitio para IA:** reglas de robots.txt para GPTBot,
  OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot, Google-Extended y
  CCBot; llms.txt (se informa si está o no, jamás como promesa de citas);
  palabras de la portada sin JavaScript frente a las renderizadas; tipos
  JSON-LD. Sin render, «no determinable». Un sitio con llms.txt o datos
  estructurados ricos no es de madurez baja.
- **Borradores:** el gancho es el hallazgo de IA, presentado como encontrado con
  la herramienta de análisis de crecimiento orgánico de Cristina. Lenguaje de
  negocio: sin jerga ni nombres de herramientas (solo el motor de IA
  consultado), segundos con un decimal y un solo dato medido. El validador
  rechaza lo contrario.
- **Búsquedas comerciales:** DataForSEO SERP, cola estándar (USD 0,0006
  por búsqueda de referencia). Hasta 30 consultas del tipo «[servicio] en
  [ciudad]», «precio [servicio]» y «mejor [servicio] en [ciudad]», solo
  con servicio y ciudad observados. Cada una registra fecha, país, ciudad,
  idioma y dispositivo. Sin `DATAFORSEO_LOGIN` y `DATAFORSEO_PASSWORD`,
  «sin dato».
- **Competidores:** dominios que más se repiten en esas búsquedas, separados
  en directorios, marketplaces, medios y negocios. Para un negocio local,
  una Text Search de categoría y ciudad, compartida, y solo sus place_id.
  La velocidad se compara con LCP de campo (PageSpeed o CrUX). Sin dato
  de campo: «sin datos de campo».
- **Páginas que faltan:** servicio × ciudad × intención sin una URL que
  responda. Con una sola portada el hueco queda «no determinable».
- **CrUX:** datos de usuarios reales del origen. Sin registro: «sin datos
  de campo». Nunca «está bien». El laboratorio no sustituye al campo.
- **Knowledge Graph:** si la API devuelve la marca como entidad. Sin key,
  o si el nombre no coincide, no se afirma que Google no la reconoce.
  Key: `KNOWLEDGE_GRAPH_API_KEY`.
- **Señales de compra (6 meses, verificables):** cambio de portada en
  Wayback CDX (dos HTML distintos: inferido, no se llama rediseño sin
  más), subdominio nuevo en crt.sh, vacante de marketing, SEO o contenido
  si la página la trae. Expansión, sede y lanzamiento solo con evidencia.
  La pauta activa la anota Cristina a mano.
- **Oportunidades medidas:** en una página que respondió 200, el título vacío,
  la meta description vacía y el H1 vacío son oportunidad observada. Una
  página de venta (portada, producto, colección o servicio) que responde
  4xx o 5xx también. Un 429, un 503 o una página sin respuesta siguen en
  «no determinable»: no se inventa el vacío ni se llama página rota.
  El inventario incompleto no saca al cliente; lo no rastreado no se afirma
  y lo ya medido sí. Cada medición con web corre el diagnóstico y la
  auditoría SEO juntos. Un rastreo de hoy ya completo no se repite.
- **Hallazgos:** cada uno con nivel observado, inferido o no determinable.
  Los 5 se ordenan por consecuencia: primero los de IA (prueba en vivo y
  lectura del sitio para IA), después velocidad y errores de todo el sitio
  antes que el detalle de una página. Nunca como hecho: tráfico estimado,
  backlinks totales, ventas perdidas, puntaje GEO.
- **Cifras estimadas sí entran, rotuladas.** Tráfico o volumen estimado
  (ej. DataForSEO Labs) se usa con la etiqueta «estimado», su fuente y su
  fecha, y nivel inferido. Nunca se presenta como medición ni como promesa.
- **Cada borrador guarda medición.** Hipótesis, tipo de apertura
  (`riesgo` / `oportunidad` / `esfuerzo` / `dato`), llamado a la acción,
  industria, `fecha_envio` (vacía hasta que Cristina envía desde Gmail) y
  `fecha_reunion` (vacía hasta que haya agenda). Sirve para ver después qué
  mensaje funciona y cuánto tarda cada industria en agendar. El dashboard
  no se construye todavía.
- **Landings por plantilla:** vista previa privada; nunca se publican con la
  marca ajena ni con fotos que no son nuestras.
