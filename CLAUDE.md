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

> Reglas duras: `aura-lead-intelligence` es de **solo lectura** (se importa,
> no se copia ni se modifica). No se inventan datos. Enviar a un prospecto
> requiere confirmación de Cristina cada vez.

## Arranque obligatorio

1. Ejecutar `./init.sh`. Si falla, parar y arreglarlo antes de seguir.
2. Leer `AGENTS.md` (mapa del repositorio y flujo de subagentes).
3. Leer el documento activo en `odd/tasks/` y trabajar una tarea a la vez.

## Dónde está cada cosa

| Archivo | Leer cuando |
|---|---|
| `AGENTS.md` | Siempre al empezar: mapa, reglas duras, subagentes, cierre |
| `docs/reglas.md` | Vas a tocar mediciones, validadores, borradores, precios, lotes o cualquier regla de negocio aprobada por Cristina |
| `docs/operacion.md` | Necesitas el doble diamante, las métricas permitidas o prohibidas, quién hace qué, la cadencia o la definición de terminado por fase |
| `docs/productos.md` | Trabajas en la oferta, los productos o las decisiones abiertas de Cristina |
| `CHECKPOINTS.md` | Vas a cerrar una tarea o sesión y necesitas verificar el estado |
