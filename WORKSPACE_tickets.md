# Workspace — Tickets

Backlog de tareas de scope workspace (no específicas de SAM ni FF8). Cosas que afectan la estructura global, archivos en la raíz del workspace, o deuda técnica transversal.

Estados: `Open` · `In Progress` · `Blocked` · `Done`.
Tickets cerrados se mueven al final bajo "Archive".

Convenciones (mismas que FF8_tickets.md):
- IDs: `WS-XXX` secuencial, no se reusan.
- Formato de sección: `## WS-XXX · Título`.
- Cada ticket tiene Origen, Estado, Descripción, Investigación necesaria (opcional), Criterio de done.

---

## WS-001 · Decidir destino de archivos sueltos del workspace root
**Origen:** Inventario completo del workspace (12 May 2026) detectó archivos sueltos en la raíz cuyo rol no está claro
**Estado:** Open

**Descripción:**
La raíz del workspace (`Antigravity/`) contiene archivos cuya función actual es ambigua. Hay que decidir caso por caso si se conservan, mueven, archivan o borran.

Archivos a evaluar:
- `main.py` (7 líneas) — esqueleto Python casi vacío, sin uso operativo aparente.
- `read_docx.py` (36 líneas) — script utilitario para extraer texto de .docx. Posiblemente uso ad-hoc.
- `docx_content.txt` (42 líneas) — output viejo de read_docx.py sobre `GET FINANCED, LLC / PROMISSORY NOTE`.
- `check-cowork.ps1` (172 líneas) — script "Claude Cowork Readiness Check". Cowork fue exploración abandonada según memoria.
- `tasks.md` (14 líneas) — "Antigravity Project Tasks", tareas genéricas con callout `[!NOTE]`.
- `reporte_usuario.md` (30 líneas) — "Perfil de Usuario y Contexto", reporte autogenerado.
- `.venv/` — virtualenv Python a nivel workspace, posiblemente solo para read_docx.py.

**Criterio de done:**
Cada archivo de la lista quedó (a) documentado en el CLAUDE.md global con propósito claro, (b) movido a una subcarpeta apropiada (ej. `scripts/`, `archive/`), o (c) borrado. No quedan archivos en la raíz cuyo rol sea "no estoy seguro qué hace".

---

## WS-002 · Reorganizar markdowns operativos sueltos en flexflow8-site/ root
**Origen:** Inventario del 12 May 2026 detectó 20+ archivos .md operativos al root del repo del portal
**Estado:** Open

**Descripción:**
El repo `fcorrea-ff8/flexflow8-site` tiene en su raíz ~20+ markdowns que deberían vivir en `docs/`. El propio `flexflow8-site/CLAUDE.md` (sección 4) ya documenta esta deuda y la sección 6 "Tool permissions" bloquea agregar más .md al root para futuro. Falta procesar los existentes.

Archivos identificados al momento del inventario (lista parcial):
- `01_FF8_Collections_Master_Report_Spec_v3.1.md`, `02_FF8_KPI_Definitions_v1.md`, `03_FF8_Agent_Architecture.md`, `04_FF8_AI_Agent_System_Prompt_Directives.md`
- `FF8_Collections_Phase1_ClaudeCode_Instructions.md`, `FF8_Collections_Phase3_Dashboard.md`, `FF8_Collections_Phase4_Chat.md`
- `FF8_Collections_Upload_Endpoint.md`, `FF8_Collections_Analyze_Endpoint.md`
- `FF8_Consolidated_Fixes.md`, `FF8_Fixes_Round2.md` ... `FF8_Fixes_Round5.md`, `FF8_Fixes_Round4_1.md`
- `FF8_Mobile_Access_and_Improvements.md`
- `FF8_GoLive_StepByStep.md`
- `FF8_Autopay_Discovery_Synthesis.md`
- `FF8_Design_Checklist_1.html` (no es .md pero está en el mismo lote)

**Investigación necesaria:**
Antes de mover, clasificar cada archivo:
1. **Spec viva** (referenciada activamente en código actual) → `docs/specs/`
2. **Decisión arquitectónica histórica** (sigue siendo verdad pero no cambia) → `docs/architecture/`
3. **Instrucción de una fase ya consumada** (Phase 1 ya en main) → `docs/history/` o borrar si ya está absorbida en `PROGRESS_LOG.md`
4. **Audit / discovery** (one-shot research) → `docs/audits/` o `docs/`
5. **Round de fixes ya mergeados** → candidatos a borrar (la historia está en git)

Decisión por archivo requiere mirada humana — no automatizable.

**Criterio de done:**
- El root del repo flexflow8-site contiene solo: CLAUDE.md, README.md, DESIGN_SYSTEM.md, archivos de config (netlify.toml, package.json, tsconfig.json, etc.), assets binarios (logos, og-image).
- Los markdowns operativos viven en `docs/` con subcarpetas apropiadas.
- `flexflow8_changelog.md` o equivalente absorbe los hitos importantes que estaban dispersos.
- Commit hace `feat → dev → main` según workflow.

---

## Archive

*(cerrados se mueven acá — se mantiene contenido original + fecha de cierre + resolución)*
