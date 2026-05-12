# CLAUDE.md — Workspace Global (Fran)

Archivo de contexto operativo de nivel workspace. Aplica a todas las sesiones de Claude Code que abran cualquier carpeta bajo este root. Cada proyecto activo tiene su propio `CLAUDE.md` con detalle específico.

---

## 1. Identidad del entorno

- **Operador:** Francisco Correa (Fran), CEO/owner de Flex Flow 8 LLC.
- **Plataforma:** Windows 11, shell bash (sintaxis Unix obligatoria — no PowerShell por defecto).
- **Workspace root:** `c:\Users\FranciscoGetFinanced\Dropbox\Antigravity\`
- **Idioma de trabajo:** español (puntuación standard latinoamericana). Inglés solo para nombres técnicos, identificadores, y artefactos de código.
- **Editor primario:** VS Code + Claude Code.

> El nombre histórico de la carpeta es "Antigravity" (legado del editor previo). El setup activo de Claude Code vive acá; no confundir con `C:\CoworkFRAN\` que fue una exploración abandonada.

---

## 2. Estructura del workspace

```
Antigravity/                         ← workspace root, repo de SAM
├── CLAUDE.md                        ← este archivo
├── .gitignore                       ← incluye reglas defensivas globales (credenciales)
├── .git/                            ← repo Mitiakamara/dungeon-master-ai (SAM)
├── .agents/                         ← workflows locales de Claude Code
├── .claude/                         ← config local de Claude Code
├── .venv/                           ← virtualenv Python a nivel workspace
├── playground/                      ← vacío, scratch
├── shared/                          ← vacío, reservado para recursos cross-proyecto
└── projects/
    ├── _template/                   ← scaffold vacío para arrancar proyectos nuevos
    ├── AstroMood/                   ← pre-arranque (solo 2 .docx, sin código)
    ├── SAM/                         ← código de SAM (parte del repo del workspace root)
    │   ├── CLAUDE.md
    │   ├── SAM_progress_log.md
    │   ├── SAM_tickets.md
    │   ├── backend/
    │   └── frontend/
    └── FF8/                         ← contenido operativo de FF8 (sin repo aún)
        ├── CLAUDE.md
        ├── FF8_tickets.md
        ├── FF8_Marco_Capacidad_Cobranza.md
        ├── Automatrix (AMX)/        ← knowledge base SQL + specs (.md, .sql, .py)
        ├── COMERCIAL/               ← presentaciones, agreements, scripts de análisis
        ├── RRHH/                    ← contratos, NDAs, recruitment docs
        ├── Inversionistas/          ← promissory notes, declaration, scripts
        ├── Migration/               ← scripts ETL (extract_data.py, generate_payments.js)
        ├── automations/             ← Make.com blueprints
        ├── PIOLA/                   ← historial cliente legacy
        ├── FF8 LOGO/                ← assets de marca
        └── flexflow8-site/          ← portal web (repo independiente fcorrea-ff8/flexflow8-site)
            ├── CLAUDE.md
            └── docs/PROGRESS_LOG.md ← log del portal
```

Archivos sueltos en el root (`main.py`, `read_docx.py`, `docx_content.txt`, `tasks.md`, `reporte_usuario.md`, `check-cowork.ps1`) son utilitarios legacy o exploración abandonada. No se documentan acá hasta que se decida si se conservan o limpian.

---

## 3. Proyectos activos

| Proyecto | Carpeta | Tipo | Repo | Estado |
|---------|---------|------|------|--------|
| SAM | `projects/SAM/` | Personal — AI DM para D&D 5e | `Mitiakamara/dungeon-master-ai` (en root del workspace) | Desarrollo activo |
| FF8 (ops) | `projects/FF8/` | Empresa — Contenido operativo: SQL AMX, RRHH, automatizaciones, docs | Pendiente: `fcorrea-ff8/ff8-operations` | Producción (sin versionado) |
| flexflow8-site | `projects/FF8/flexflow8-site/` | Empresa — Portal web | `fcorrea-ff8/flexflow8-site` (repo propio) | Desarrollo activo |

**Proyectos inactivos / scaffolds:**
- `projects/AstroMood/` — pre-arranque, solo specs en .docx. Sin CLAUDE.md.
- `projects/_template/` — scaffold vacío para futuros proyectos.

---

## 4. Estructura git del workspace

**Realidad operativa actual:**

| Path | Repo | Origin |
|------|------|--------|
| Workspace root (`Antigravity/`) | Repo principal | `Mitiakamara/dungeon-master-ai` |
| `projects/FF8/flexflow8-site/` | Repo independiente | `fcorrea-ff8/flexflow8-site` |
| `projects/FF8/` (todo lo demás) | **Sin repo** | — |

**Implicaciones:**

- SAM se commitea desde el workspace root. El working tree del repo del root contiene todo el workspace, pero `.gitignore` excluye lo que no es de SAM. Esa estructura es intencional, no leftover.
- El portal web vive en su propio repo. Se commitea desde `projects/FF8/flexflow8-site/`.
- El resto de FF8 (Automatrix, COMERCIAL, RRHH, Inversionistas, Migration, automations, PIOLA) **no está versionado**. Si Claude Code rompe algo en estos directorios, no hay rollback git. Dropbox provee history limitado por archivo pero no commits atómicos.

**Plan de versionado de FF8 (WORKSPACE-002, pendiente):**

Inicializar repo privado `fcorrea-ff8/ff8-operations` en `projects/FF8/` con primer commit completo del estado actual (excepto credenciales, env y binarios temporales). Esto preserva la posibilidad de retroceder a "el estado de hoy" si algo se rompe a futuro. La inicialización se hace después del refactor de CLAUDE.md.

**Hasta que `ff8-operations` exista:**
- Asumir que cambios en `projects/FF8/` no tienen rollback automático.
- Para cambios destructivos en `projects/FF8/`, confirmar dos veces.
- Dropbox sigue sincronizando — última defensa.

---

## 5. Multi-cuenta GitHub (protocolo crítico)

Dos cuentas activas en `gh` CLI:

| Cuenta GitHub | Uso | SSH alias | Repos |
|--------------|-----|-----------|-------|
| `Mitiakamara` | Personal | `github-mitiakamara` | `dungeon-master-ai` (SAM) |
| `fcorrea-ff8` | Empresa FF8 | `github-ff8` | `flexflow8-site`, futuro `ff8-operations` |

**Protocolo obligatorio al cambiar de cuenta:**

```bash
gh auth switch --user <cuenta>
gh auth setup-git     # SIEMPRE. Sin esto, git push falla con "Repository not found"
```

El segundo comando es no-opcional. El credential helper de git sigue usando el token de la cuenta anterior si se omite.

**Verificación de auth SSH:**

```bash
ssh -T git@github-mitiakamara
ssh -T git@github-ff8
```

---

## 6. Restricciones globales (Forbidden)

Aplican a todas las sesiones independientemente del proyecto.

**NO ejecutar sin confirmación explícita en chat:**
- Comandos destructivos: `rm -rf`, `git reset --hard origin/<branch>`, `git push --force`, `git clean -fdx`.
- `terraform apply`, `kubectl delete`, ningún comando contra infra de producción.
- Modificar env vars de producción (Netlify, Vercel, Render) desde sesión local.
- Cualquier UPDATE/DELETE directo contra bases de datos de producción (Supabase, AMX SQL Server, Airtable bases de FF8).

**NO mezclar credenciales entre cuentas GitHub.** Si el contexto del request es ambiguo, preguntar antes de ejecutar `gh auth switch` o cualquier `git push`.

**NO commitear credenciales bajo ningún concepto.** Las reglas defensivas en el `.gitignore` del workspace root cubren globs comunes (`*Credentials*.txt`, `*Credentials*.md`, `*ApiKey*.txt`, `*ApiKey*.md`, `*.env`, `*.env.local`, `*.env.*.local`, `PostmarkAPI.txt`). Si encontrás un archivo nuevo con credenciales que no encaja en esos globs, agregálo al `.gitignore` antes que nada.

**NO escribir credenciales en `CLAUDE.md`, `*_tickets.md`, `*_progress_log.md` ni ningún documento de memoria.** Esos archivos sí se versionan. Si necesitás referenciar un secreto, usá un placeholder (`<TOKEN>`, `<API_KEY>`).

---

## 7. Estrategia de memoria

**Persistir en este archivo:**
- Identidad del entorno y plataforma.
- Estructura física del workspace y mapa de repos.
- Protocolos de auth multi-cuenta.
- Restricciones globales que aplican a todos los proyectos.

**NO persistir aquí:**
- Estado transitorio de sesiones (ssh-agent, conexiones abiertas, notas tipo "estoy en casa / continuar desde la oficina"). Eso va a notas locales fuera del repo.
- Detalles operativos de un proyecto específico. Van al `CLAUDE.md` de ese proyecto.
- Changelog, historial de commits, fases de desarrollo. Van a archivos `*_changelog.md` o `*_progress_log.md` dentro de cada proyecto.
- Tareas pendientes globales del workspace. Van a un `WORKSPACE_tickets.md` si se materializa.

**Tickets de scope workspace conocidos:**
- `WORKSPACE-001` — Decisión sobre archivos sueltos del root (`main.py`, `read_docx.py`, `docx_content.txt`, `tasks.md`, `reporte_usuario.md`, `check-cowork.ps1`): ¿conservar, mover o borrar?
- `WORKSPACE-002` — Inicializar repo `fcorrea-ff8/ff8-operations` en `projects/FF8/` (privado, gitignore selectivo, primer commit completo).

---

## 8. Expectativas de ejecución

Antes de escribir código en cualquier proyecto:
1. Leer el `CLAUDE.md` específico del proyecto en cuestión.
2. Identificar el repo activo según la sección 4. Si el proyecto no tiene repo (caso actual de FF8 ops), tratar cambios con cautela extra.
3. Confirmar que la cuenta `gh` activa coincide con el repo destino.
4. Para tareas que cruzan proyectos, declarar explícitamente qué proyecto se está modificando antes de cada acción.
5. Para operaciones destructivas en `projects/FF8/` (no-portal), confirmar dos veces hasta que `ff8-operations` esté inicializado.

---

*Última revisión: 12 May 2026 — v3 reconciliada contra inventario completo del workspace. Plan de versionado de FF8 declarado (WORKSPACE-002).*
