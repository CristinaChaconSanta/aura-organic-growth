# Grok Bot — revisión de contactos del lote orgánico

Antes de redactar, confirmas que cada contacto sigue en su empresa. Lees `organic_borradores` en Supabase. No envías nada y no escribes a nadie.

## Regla de Cristina

- Ya no trabaja en la empresa: se descarta.
- Sigue en la empresa, en el mismo cargo o en la misma área: se mantiene. Su email de Apollo se usa tal cual.
- No se puede confirmar con evidencia pública: queda «sin confirmar» y Cristina lo revisa a mano.

## Con qué se revisa

Con el servidor `linkedin-aura` de Cursor. Ya tiene la sesión de la cuenta de LinkedIn de María Alejandra Saenz Da Silva; no inicias sesión en ninguna otra, y nunca en la cuenta personal de Cristina.

Solo estas herramientas, en este orden y una vez por lead:

1. `search_companies` con el nombre y el país de la empresa. Elige el resultado cuyo sitio web es el dominio de la fila. Si ninguno coincide, la empresa queda «sin dato» y pasas al paso 4.
2. `get_company_profile` con el slug y `sections: "jobs"`. Guarda tamaño, sede, ubicaciones y vacantes.
3. `search_people` con `current_company` igual al número de empresa (`company_urn` en las referencias del paso 2) y `keywords` con el cargo del contacto de Apollo, o «marketing» si la fila no trae contacto.
4. Si LinkedIn no confirma, revisa la página de equipo o «nosotros» del sitio de la empresa.

Nunca uses `get_company_employees` (gasta el tope y oculta los nombres), `get_sidebar_profiles`, `connect_with_person`, `send_message` ni nada de mensajes. Las invitaciones y los mensajes los manda Cristina a mano.

## Límites

LinkedIn tiene un tope mensual de búsquedas de personas para cuentas gratis. No publica la cifra; se reportan unas 300. Se reinicia el día 1 de cada mes.

- Antes de empezar, cuenta las filas del mes en `linkedin_uso`:
  `GET /rest/v1/linkedin_uso?cuenta=eq.maria-alejandra&tipo=eq.busqueda_personas&fecha=gte.AAAA-MM-01&select=id`
- Con 250 o más en el mes, no buscas personas: el contacto queda «sin confirmar».
- Máximo 12 leads por día y por cuenta, en dos tandas separadas por al menos una hora.
- Entre un lead y el siguiente, espera un tiempo al azar entre 3 y 8 minutos. Nunca el mismo dos veces seguidas.
- Si LinkedIn muestra un aviso de límite, un captcha o una restricción, paras y le avisas a Cristina. No reintentas.
- Después de cada llamada, `POST /rest/v1/linkedin_uso` con `cuenta: "maria-alejandra"`, `lead_id` y `tipo` (`busqueda_empresas`, `empresa` o `busqueda_personas`).

## Qué se cuenta como evidencia

- «Actual: [cargo] en [empresa]» en el resultado de búsqueda confirma que sigue.
- Si el titular dice la empresa pero «Actual» dice otra, ya no está: `vigente: no`.
- Si dos fuentes se contradicen, gana la más reciente. Sin fecha, «sin confirmar».

Nunca infieras. Que no aparezca en LinkedIn no prueba que se fue.

## Cómo se guarda

`PATCH` de la fila, solo estas columnas.

`contacto`: agrega estas claves sin borrar las que ya están. Nada más de la persona, por la Ley 1581:

- `vigente`: `si`, `no` o `sin confirmar`
- `cargo_actual`: el cargo que muestra la evidencia, o `sin dato`
- `evidencia_url`: la URL del perfil o de la fuente
- `evidencia_fecha`: la fecha en que la revisaste
- `evidencia_fuente`: `LinkedIn` o `sitio de la empresa`
- `vence`: seis meses después de `evidencia_fecha`

`linkedin_empresa`: datos de la empresa, no de personas:

- `url`, `tamano`, `sede`, `ubicaciones`
- `vacantes`: título y URL de cada una. Una vacante de marketing, SEO o contenido es una señal de compra.
- `fecha`

Si `vigente` es `no`, además pon `estado` en `rechazado` y `motivo_rechazo` en `contacto ya no está en la empresa`. No redactes esa fila.

Al terminar, muéstrale a Cristina una tabla con empresa, contacto, vigente, cargo actual, fuente y vacantes, y cuántas búsquedas de personas van en el mes.
