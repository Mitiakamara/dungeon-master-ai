# CLAUDE.md — Proyecto SAM

Contexto operativo para sesiones de Claude Code en `projects/SAM/`. Asume que el `CLAUDE.md` global del workspace ya fue cargado.

---

## 1. Identidad del proyecto

**SAM (Storytelling AI Master)** — Aplicación web de Dungeon Master con IA para D&D 5e. SAM es un DM virtual con personalidad sarcástica y humor oscuro, que narra historias, aplica reglas, gestiona combate/loot y soporta campañas multijugador.

**Repo y versionado:**
- Repo: `Mitiakamara/dungeon-master-ai` (cuenta personal).
- **El `.git/` vive en el workspace root**, NO en `projects/SAM/`. SAM es un subpath del repo del workspace.
- Comandos `git` (status, add, commit, push) se ejecutan desde el workspace root, no desde `projects/SAM/`.
- `projects/SAM/.gitignore` existe pero es complementario al `.gitignore` del root; no convierte a SAM en sub-repo.
- Antes de `git push`: confirmar que `gh auth status` muestra `Mitiakamara` activa (no `fcorrea-ff8`).

**Stack:**

| Capa | Tecnología | Hosting |
|------|-----------|---------|
| Frontend | Next.js 16 + TypeScript + shadcn/Radix + Tailwind v4 | Vercel |
| Backend | FastAPI (Python 3) | Render |
| Base de datos | Supabase PostgreSQL + pgvector | Supabase Cloud |
| LLM | Google Gemini Flash (via LangChain 1.x) | Google Cloud |
| Embeddings | `gemini-embedding-001` (768 dims) via `google-genai` SDK | Google Cloud |
| Auth | Supabase JWT + RLS en todas las tablas | Supabase |

**URLs activas:**
- Backend: `https://sam-backend-mg0j.onrender.com`
- Frontend: `sam-weld-tau.vercel.app`

---

## 2. Estructura del proyecto

```
projects/SAM/
├── CLAUDE.md                    # este archivo
├── SAM_progress_log.md          # memoria histórica (NO leer salvo pedido explícito)
├── SAM_tickets.md               # backlog activo (IDs SAM-XXX)
├── SAM_assessment.md            # evaluación técnica
├── SAM_Admin_Manual.md
├── SAM_Player_Manual.md
├── .gitignore                   # complementario al del workspace root
├── backend/
│   ├── server.py                # FastAPI: /api/chat, /api/roll, /api/version
│   ├── app/
│   │   ├── core/                # dice.py, security.py
│   │   ├── routers/             # campaigns, characters, messages
│   │   └── services/            # ai.py (legacy), ingestion.py, admin.py, tools/
│   ├── agents/                  # Sistema multi-agente (camino activo)
│   │   ├── dice.py, rules.py, combat_state.py
│   │   ├── mechanic.py          # MechanicEngine: D&D 5e Python puro, cero LLM
│   │   ├── interpreter.py       # IntentInterpreter: LLM → JSON intent
│   │   ├── narrator.py          # Narrator: LLM solo narra hechos pre-calculados
│   │   ├── knowledge.py         # KnowledgeService: RAG
│   │   └── orchestrator.py      # SAMOrchestrator: pipeline Interpreter→Mechanic→Narrator
│   └── schema*.sql              # Esquemas iterativos (último: phase11_schema.sql)
├── frontend/
│   ├── app/                     # page.tsx, layout.tsx, admin/, auth/callback/
│   ├── components/              # game-layout, chat-interface, dice-tray, sidebars, ui/
│   ├── lib/                     # api.ts (authenticatedFetch), supabase/
│   └── hooks/                   # use-realtime.ts
└── resources/                   # PDFs de referencia (D&D 5e SRD, manuales)
```

Archivos `*.resolved` (`implementation_plan_phase_16_math.md.resolved`, `project_proposal.md.resolved`) son artefactos de un resolver de conflictos (Dropbox o git). Decisión pendiente sobre limpieza — ver SAM_tickets.md si se materializa.

---

## 3. Coding standards (reglas que cambian implementación)

**Arquitectura multi-agente — separación obligatoria:**
- `MechanicEngine` (Python puro) decide y calcula. Cero llamadas al LLM.
- `Narrator` (LLM) solo narra hechos pre-calculados. Nunca decide si un ataque pega, ni cuánto daño hace, ni si hay level up.
- Si una nueva feature requiere "que el modelo decida X", primero verificar si X se puede modelar como regla en `mechanic.py`.

**Combat loop — invariantes:**
- Turn enforcement: `combat.active && sender_name != current_turn.name` bloquea intents `attack/spell/ability/start_combat`. Producir solo recordatorio in-character (<30 palabras).
- Initiative ground truth: la prosa del narrador debe citar verbatim los `result` exactos de los `<DM_ROLL>` tags. Nunca inventar valores numéricos.
- Action economy: `actions_remaining` se persiste en `combat_state.to_dict()` y se consume en handlers de `weapon_attack/weapon_damage/spell_attack/spell_damage`.

**Resource consumption automático:**
- Spell slots: el interpreter extrae `spell_level`. El orchestrator emite `state_update spell_slot_consume` después de procesar el hechizo.
- Items consumibles: `state_update inventory_remove` con qty=1. Defensive: log warning sin crashear si el item no existe.

**Embeddings:** usar siempre el SDK `google-genai` (`client.models.embed_content()`). Dimensión fija 768. Legacy `google-generativeai` está eliminado.

**Tags especiales en respuestas de SAM** (no inventar nuevos sin actualizar el parser en `server.py`): `<UPDATE>`, `<LOOT>`, `<IMAGE>`, `<XP_GAIN>`, `<COMBAT>`, `<DM_ROLL>`.

**Stripping de artifacts:** `stripSystemTags` en frontend es role-aware. Solo limpia mensajes con `role: assistant`. Las tiradas de dados de jugadores no se tocan.

**RPCs de Supabase permitidos:**
- `match_documents(query_embedding, threshold, count)` — RAG módulos de campaña.
- `match_compendium(query_embedding, threshold, count, table_name)` — compendio D&D 5e.

---

## 4. Tool permissions

**Permitidos:**
- `npm install`, `npm run dev`, `npm run build`, `npm run lint` en `projects/SAM/frontend/`.
- `pip install -r requirements.txt`, `uvicorn server:app --reload` en `projects/SAM/backend/`.
- Lectura de cualquier archivo del proyecto.
- Ejecutar scripts de seed en `backend/app/scripts/` contra la BD de **desarrollo**.
- Crear feature branches desde el workspace root (`git checkout -b feat/...`).
- Commits y push desde el workspace root (cuenta `gh` debe ser `Mitiakamara`).

**Forbidden (incluso con permiso explícito):**
- Modificar `phase*_schema.sql` previos (los esquemas son iterativos; agregar uno nuevo, nunca editar uno publicado).
- Ejecutar seeders contra Supabase de producción.
- Tocar `auth.users` directamente (usar Supabase Auth API).
- Modificar el system prompt del narrator sin actualizar `SAM_progress_log.md` con la razón del cambio (cambia tono/comportamiento del DM).
- Push a `main` sin haber pasado por una rama feature primero (workflow: `feat/* → main` para SAM; SAM no tiene rama `dev` separada).

---

## 5. Memoria

**Persistir en este `CLAUDE.md`:**
- Stack y URLs activas.
- Invariantes arquitectónicos (separación mechanic/narrator, multi-agent pipeline).
- Tags especiales y RPCs nombrados.
- Aclaración del modelo de repo (SAM como subpath del repo del workspace root).

**NO persistir aquí — externalizar:**
- Historial de bugs resueltos → `SAM_progress_log.md`.
- Backlog activo y tickets → `SAM_tickets.md` (formato `SAM-XXX | tipo | prio | estado`).
- Detalles de fixes específicos por commit → log de progreso, no CLAUDE.md.

**Si una sesión necesita contexto histórico:** instruir explícitamente "lee `SAM_progress_log.md`" antes del pedido, en lugar de cargarlo siempre.

---

## 6. Expectativas de ejecución

Antes de modificar código:
1. Identificar si la lógica vive en `agents/` (camino activo) o `app/services/ai.py` (legacy fallback). Preferir `agents/`.
2. Para features de combate, revisar `combat_state.py` y `orchestrator._handle_*` antes de inventar un nuevo intent type.
3. Para nuevos intent types, agregarlos al `interpreter.py` Y al handler en `orchestrator.process_message()`. Ambos lados son obligatorios.
4. Para cambios que afectan el frontend, verificar si el `useRealtime` subscription en `chat-interface.tsx` necesita actualizarse — la subscription es sensible a duplicación.
5. Abrir ticket `SAM-XXX` en `SAM_tickets.md` antes de la instrucción, referenciarlo en el commit message.
6. Operaciones git desde el workspace root, NO desde `projects/SAM/`.

---

*Mantener este archivo por debajo de 220 líneas. Si crece, externalizar a `SAM_progress_log.md`.*
