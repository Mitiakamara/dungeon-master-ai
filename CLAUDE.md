# CLAUDE.md — Workspace Global (Fran)

Archivo de contexto operativo de nivel workspace. Aplica a todas las sesiones de Claude Code que abran cualquier proyecto bajo este root. Cada proyecto tiene su propio `CLAUDE.md` con detalle específico.

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
Antigravity/                         ← workspace root
├── CLAUDE.md                        ← este archivo
├── .git/                            ← leftover histórico (ver sección 4)
└── projects/
    ├── SAM/
    │   ├── CLAUDE.md                ← contexto del proyecto SAM
    │   ├── SAM_progress_log.md
    │   └── SAM_tickets.md
    └── FF8/
        ├── CLAUDE.md                ← contexto FF8 ops
        ├── FF8_tickets.md
        ├── FF8_progress_log.md      ← si existe (a verificar)
        └── flexflow8-site/          ← sub-proyecto con repo propio
            └── CLAUDE.md            ← contexto del portal web
```

---

## 3. Proyectos activos

| Proyecto | Carpeta | Tipo | Estado |
|---------|---------|------|--------|
| SAM | `projects/SAM/` | Personal — AI DM para D&D 5e | Desarrollo activo |
| FF8 | `projects/FF8/` | Empresa — Fintech down payments | Producción |
| flexflow8-site | `projects/FF8/flexflow8-site/` | FF8 sub-proyecto — Portal web | Desarrollo activo, **repo independiente** |

---

## 4. Estado del repositorio raíz (deuda técnica conocida)

El workspace root tiene un `.git/` con historia que incluye commits de SAM. Esto es **leftover, no intencional**.

**Realidad presente:**
- El root contiene `.git/` con rama `main` y commits históricos.
- `flexflow8-site/` ya está separado como repo propio bajo `fcorrea-ff8/flexflow8-site`.
- SAM tiene su propio repo en `Mitiakamara/dungeon-master-ai`, pero los commits viejos de SAM también viven en el `.git/` del root.

**Estado deseado:**
- Workspace root NO debería ser un repo. Cada proyecto vive en su propio `.git/`.
- El `.git/` del root debería limpiarse después de verificar que todo el contenido relevante esté en los repos por proyecto.

**Mientras tanto:**
- NO commitear cambios nuevos desde la raíz del workspace.
- Para SAM, trabajar siempre desde `projects/SAM/` (que debe tener o necesita tener su propio `.git/` apuntando a `Mitiakamara/dungeon-master-ai`).
- Para FF8 portal, trabajar siempre desde `projects/FF8/flexflow8-site/` (repo independiente).

**Ticket asociado:** crear ticket `WORKSPACE-001` o equivalente para limpieza del `.git/` del root (decisión de Fran sobre cuándo).

---

## 5. Multi-cuenta GitHub (protocolo crítico)

Dos cuentas activas en `gh` CLI:

| Cuenta GitHub | Uso | SSH alias | Email para `user.email` |
|--------------|-----|-----------|--------------------------|
| `Mitiakamara` | SAM (personal) | `github-mitiakamara` | personal |
| `fcorrea-ff8` | FF8 (empresa) | `github-ff8` | corporativo |

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

**NO commitear desde la raíz del workspace.** Ver sección 4. Cada proyecto tiene (o debería tener) su propio `.git/`. Si hay duda sobre desde dónde se está commiteando, frenar y preguntar.

**NO mezclar credenciales entre cuentas GitHub.** Si el contexto del request es ambiguo, preguntar antes de ejecutar `gh auth switch` o cualquier `git push`.

---

## 7. Estrategia de memoria

**Persistir en este archivo:**
- Identidad del entorno y plataforma.
- Estructura física del workspace.
- Protocolos de auth multi-cuenta.
- Restricciones globales que aplican a todos los proyectos.
- Deuda técnica conocida del workspace (ej. `.git/` leftover en root).

**NO persistir aquí:**
- Estado transitorio de sesiones (ssh-agent, conexiones abiertas, notas tipo "estoy en casa / continuar desde la oficina"). Eso va a notas locales fuera del repo.
- Detalles operativos de un proyecto específico. Van al `CLAUDE.md` de ese proyecto.
- Changelog, historial de commits, fases de desarrollo. Van a archivos `*_changelog.md` o `*_progress_log.md` dentro de cada proyecto.

---

## 8. Expectativas de ejecución

Antes de escribir código en cualquier proyecto:
1. Leer el `CLAUDE.md` específico del proyecto en cuestión.
2. Identificar el repo activo (workspace root NO es un repo válido para nuevos commits — ver sección 4).
3. Confirmar que la cuenta `gh` activa coincide con el repo destino.
4. Para tareas que cruzan proyectos, declarar explícitamente qué proyecto se está modificando antes de cada acción.

---

*Última revisión estructural: 12 May 2026 — refactor desde un CLAUDE.md monolítico a jerarquía por proyecto. Path y estado de repo corregidos contra realidad operativa.*