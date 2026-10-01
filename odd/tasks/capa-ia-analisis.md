# Capa de IA en cada análisis

## Objective
Every lead analysis starts with the AI layer: what ChatGPT and Gemini answer when a buyer asks for the lead's service, which sources they cite, and whether AI bots can read the site. Speed and Google searches stay, after it.

## Problem
The batch measured only speed and Google searches. The AI layer (axiom: every business can grow in times of AI) was missing. Live test on 2026-09-30: ChatGPT did not mention DIVE, Clemsa or English UC when asked their buyers' questions.

## Scope (authorized by Cristina, 2026-09-30)
- New module for the live AI test (DataForSEO LLM Scraper, ChatGPT and Gemini, live, force_web_search) with balance guard.
- AI legibility check: robots.txt AI bots, llms.txt, words without JS vs rendered, JSON-LD schema types.
- AI findings rank first, written in plain business language.
- Maturity no longer marks a site with llms.txt or rich schema as low.
- Validator rejects technical jargon and tool names in drafts.
- Grok instructions and CLAUDE.md updated.

## Constraints
- aura-lead-intelligence read-only. Never invent data. Absence only after render.
- No promise of AI mention or ranking. llms.txt is measured, never sold as a citation lever. WebMCP and ai.txt are not sold.
- DataForSEO: free credit only; stop if balance < USD 0.10. No real API calls in tests.
- TDD: not configured (ordinary checks). Runner: `.venv/bin/python -m pytest -q`.

## Tasks
- [x] T1 AI live test module + tests (ia.py, observados.py; tests/test_ia.py)
- [x] T2 AI legibility module + tests (legibilidad_ia.py, render.paginas_renderizadas; tests/test_legibilidad_ia.py)
- [x] T3 Findings: AI first, plain language; maturity fix + tests (hallazgos_de_ia, hallazgos_de_legibilidad, hallazgos.ORDEN_IA, madurez.clasificar(llms_txt=))
- [x] T4 Wire into correr_lote and staging refresh (correr_lote._paso_ia, staging.hallazgos_de_ia_y_legibilidad; tests/test_correr_lote.py)
- [x] T5 Validator jargon rule + tests; Grok instructions; CLAUDE.md
- [x] T6 Run on the 6 current leads, refresh organic_borradores (scripts/ia_lote.py; AI for DIVE, Clemsa, English UC; legibility for all 6)

- [x] T5b Observed fallback for the buyer question (servicio from title/meta/h1, ciudad stored or país only, english.uc.cl override) + tests

## Route
Delegated direct (writer trigger: 2+ non-trivial files). Branch: master, as the repo and Grok Bot instructions use master.

## Progress
Created 2026-09-30.

- T1 done 2026-09-30: ia.py asks ChatGPT and Gemini via LLM Scraper with balance guard; servicio/ciudad observados moved to observados.py. Route: delegated direct (single writer).
- T2 done 2026-09-30: robots for 7 AI bots, llms.txt, words without JS vs rendered, JSON-LD types; no render => 'no determinable'.
- T3 done 2026-09-30: AI findings rank first; absence in a cited list only if the page was fetched and had content; maturity counts llms.txt or rich JSON-LD as one signal.
- T4 done 2026-09-30: IA step runs first for every lead with a web (low maturity included); refresh rebuilds IA findings from the resumen record and puts them first.
- T5 done 2026-09-30: validar() adds jerga_tecnica and mas_de_un_dato; promesa_aparicion_ia now only flags promises (naming ChatGPT/Gemini is allowed); citing a finding no longer requires a number (four consecutive words from the finding also count). T6 not run: paid calls are Cristina's decision.
- T5b done 2026-09-30: ia.servicio_de_sitio reads literal title/meta/h1 without the brand; result records servicio_origen; observados.URLS maps uc.cl to english.uc.cl.
- T6 done 2026-09-30: live run authorized by Cristina within the free credit. Balance 0.637 -> 0.581 USD (6 questions in the first run, 1 raw shape probe x2 engines, 6 in the re-run after the parser fix). AI test skipped for OutLoud, Terra, FrescoFrigo because the question built from the site was unreliable (CTA text or slogan, city outside the country); legibility ran for all 6. organic_borradores.hallazgos refreshed for the 6 rows (estado pendiente; rechazado rows untouched; borradores not rewritten).
- Live shape: both engines return `markdown`, `sources` (domain, url, title) and `items`; ChatGPT also `brand_entities`. Gemini puts citation links inside the bold names; parser now strips them. terraenergy.io/llms.txt answers 200 with an empty body (reported as absent).
