# Grok Bot — revisión de contactos del lote orgánico

Antes de redactar, confirmas que cada contacto sigue en su empresa. Lees `organic_borradores` en Supabase. No envías nada y no escribes a nadie.

## Regla de Cristina

- Ya no trabaja en la empresa: se descarta.
- Sigue en la empresa, en el mismo cargo o en la misma área: se mantiene. Su email de Apollo se usa tal cual.
- No se puede confirmar con evidencia pública: queda «sin confirmar» y Cristina lo revisa a mano.

## Cómo se revisa, sin iniciar sesión en LinkedIn

No inicies sesión en LinkedIn ni en ninguna cuenta de Cristina. LinkedIn prohíbe el acceso automatizado y la cuenta es personal.

1. Busca en Google el nombre, el apellido y la empresa, por ejemplo `"Nombre Apellido" Empresa linkedin`. Lee el título y el resumen que muestra Google, sin abrir el perfil con sesión.
2. Revisa la página de equipo o «nosotros» del sitio de la empresa.
3. Anota la fuente (URL) y la fecha de cada evidencia. Si dos fuentes se contradicen, gana la más reciente, y si no hay fecha, queda «sin confirmar».

Nunca infieras. Que no aparezca en el sitio no prueba que se fue.

## Cómo se guarda

`PATCH` de la fila, solo la columna `contacto`. Agrega estas claves sin borrar las que ya están:

- `vigente`: `si`, `no` o `sin confirmar`
- `cargo_actual`: el cargo que muestra la evidencia, o `sin dato`
- `evidencia_url`: la URL de la fuente
- `evidencia_fecha`: la fecha en que la revisaste

Si `vigente` es `no`, además pon `estado` en `rechazado` y `motivo_rechazo` en `contacto ya no está en la empresa`. No redactes esa fila.

Al terminar, muéstrale a Cristina una tabla con empresa, contacto, vigente, cargo actual y fuente.
