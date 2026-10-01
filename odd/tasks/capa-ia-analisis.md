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
- [ ] T3 Findings: AI first, plain language; maturity fix + tests
- [ ] T4 Wire into correr_lote and staging refresh
- [ ] T5 Validator jargon rule + tests; Grok instructions; CLAUDE.md
- [ ] T6 Run on the 6 current leads, refresh organic_borradores

## Route
Delegated direct (writer trigger: 2+ non-trivial files). Branch: master, as the repo and Grok Bot instructions use master.

## Progress
Created 2026-09-30.

- T1 done 2026-09-30: ia.py asks ChatGPT and Gemini via LLM Scraper with balance guard; servicio/ciudad observados moved to observados.py. Route: delegated direct (single writer).
- T2 done 2026-09-30: robots for 7 AI bots, llms.txt, words without JS vs rendered, JSON-LD types; no render => 'no determinable'.
