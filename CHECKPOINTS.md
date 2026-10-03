# CHECKPOINTS — Verificación de cierre

Marca cada casilla solo con evidencia observada (comando y resultado).

## C1 Arnés completo
- [ ] `CLAUDE.md` tiene menos de 200 líneas
- [ ] Existen `AGENTS.md`, `init.sh`, `CHECKPOINTS.md` y `.claude/settings.json`
- [ ] `./init.sh` sale con código 0

## C2 Estado coherente
- [ ] Los checkboxes de `odd/tasks/` están marcados solo con evidencia
- [ ] `progress/current.md` está vacío o describe la sesión activa

## C3 Arquitectura
- [ ] `aura-lead-intelligence` no se tocó
- [ ] Ningún secreto ni `.xlsx` en git (`git ls-files | grep -i xlsx` sin resultados nuevos)
- [ ] Los módulos nuevos están en `src/aura_organic_growth/` con sus pruebas

## C4 Verificación real
- [ ] Cada módulo nuevo tiene pruebas en `tests/`
- [ ] `.venv/bin/python -m pytest -q` corre más de 0 pruebas y todas pasan
- [ ] Ninguna prueba llama a APIs reales

## C5 Cierre
- [ ] `progress/history.md` tiene una entrada de la última sesión
- [ ] Sin `print` de depuración ni archivos temporales sueltos
