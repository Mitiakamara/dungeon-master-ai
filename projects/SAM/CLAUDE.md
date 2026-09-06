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
- Turn enforcement: `combat.active && sender_name != current_turn.name` bloquea intents `attack/spell/ability/start_combat/end_turn/skill_check/self_damage/item` (todo lo que arma un pending o muta estado). `dice_roll` fuera de turno pasa solo si el roller tiene slot propio. Producir solo recordatorio in-character (<30 palabras).
- Initiative ground truth: la prosa del narrador debe citar verbatim los `result` exactos de los `<DM_ROLL>` tags. Nunca inventar valores numéricos.
- Action economy: `actions_remaining` se persiste en `combat_state.to_dict()` y se consume en handlers de `weapon_attack/weapon_damage/spell_attack/spell_damage`.

**Pending rolls — un slot por personaje (instrucción 239):**
- **Un dado se enruta por `character_id` del que lo tira, nunca por nombre.** `MechanicEngine.pending_rolls: dict[str, dict]` keyed por `character_id`. API: `set_pending(character_id, character_name, pending) -> bool` (estampa dueño; re-declarar reemplaza SOLO el slot propio; sin id → WARNING y `False`, nunca un pending sin dueño), `get_pending(character_id)`, `clear_pending(character_id)`, `all_pending()`.
- `process_player_roll` resuelve únicamente el slot del roller; sin slot propio → fact `ORPHAN ROLL` (informativo). No existe comparación por nombre (SAM-049 superseded).
- Persistencia: `campaigns.settings.combat.pending_rolls` (`{character_id: pending}`). La forma legacy `pending_player_roll` (slot único) se lee y migra en `_rehydrate_pending` (id del dict → nombre en la party → descartar con WARNING); nunca se escribe.
- Facts: `→ PROMPT PLAYER (Nombre): …` nombra a quién se le pide el dado. Los slots ajenos que quedaron de requests anteriores viajan al narrador como contexto `PENDING ROLLS: …` (regla 19: puede mencionarlos, no re-pedirlos, no inventar resultados), nunca como fact de acción.
- `/api/chat` recibe `campaign_id` explícito: acceso validado en `app/core/access.py` (personaje en la campaña, GM o admin; si no → 403) y `char_ctx` resuelto DENTRO de esa campaña. Sin `campaign_id` → inferencia legacy por primer personaje con WARNING (compatibilidad temporal, ver SAM-067).

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
- `pip install -r requirements.txt`, `uvicorn server:app --reload` en `projects/SAM/backend/` (siempre con el venv de abajo).

**Venv y tests del backend (instrucción 241 — correr antes de cada push):**
- Venv del proyecto: `projects/SAM/backend/.venv` (Python 3.14, ignorado por git y por Dropbox vía stream `com.dropbox.ignored`). No existe `python` a secas en la máquina: el intérprete base es `python3.14`. `backend/venv/` (sin punto) es el venv viejo con ruta muerta — no usar.
- Crear o reparar: desde `projects/SAM/backend/`, `python3.14 -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt pytest`. No hace falta "activar": invocar siempre `.venv/Scripts/python.exe`.
- Suite pytest: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests/ -q` (`tests/conftest.py` pone `backend/` en `sys.path`; con el venv completo usa el `langchain_core` real, sin venv lo stubbea — corre igual).
- Harnesses legacy de la raíz (scripts, no pytest): `PYTHONUTF8=1 .venv/Scripts/python.exe test_samNNN.py` — `test_sam039_042`, `test_sam045_046`, `test_sam053_054_059` corren solo con stdlib; `test_sam044` importa `server.py` y **necesita el venv completo** (`supabase`, `langchain_google_genai`, `google.genai`).
- `PYTHONUTF8=1` es obligatorio en Windows: los tests imprimen emojis y nombres con diéresis.
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
