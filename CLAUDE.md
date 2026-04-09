# Antigravity Workspace — CLAUDE.md

Archivo de contexto persistente para sesiones de Claude Code.
**Actualizar este archivo cada vez que se agregue o modifique un proyecto.**

> **Nota (estado local):** Estoy en casa; generé las claves SSH en `%USERPROFILE%\\.ssh` y añadí un `config` con aliases `github-mitiakamara` y `github-ff8`. El `ssh-agent` no pudo arrancar en esta sesión (permiso denegado). Continuar desde la oficina: iniciar `ssh-agent` como admin, añadir claves (`ssh-add`), y subir las claves públicas a las cuentas GitHub.


---

## Repositorio

- **Plataforma:** Windows 11, shell bash (sintaxis Unix)

### Estado local — Configuración Git/SSH

- Estoy en casa: acciones realizadas
  - Claves SSH generadas en `%USERPROFILE%\\.ssh`: `id_ed25519_mitiakamara` y `id_ed25519_ff8`.
  - Archivo `%USERPROFILE%\\.ssh\\config` creado con aliases `github-mitiakamara` y `github-ff8`.
  - `ssh-agent` no pudo arrancar en esta sesión (se requieren permisos de administrador), por eso las claves no fueron añadidas al agente.

- Siguientes pasos (continuar desde la oficina)
  1. Iniciar `ssh-agent` como administrador y añadir las claves (`ssh-add ...`).
  2. Añadir las claves públicas a las cuentas GitHub (`Mitiakamara` y `fcorrea-ff8`) en https://github.com/settings/keys.
  3. Verificar autenticación SSH: `ssh -T git@github-mitiakamara` y `ssh -T git@github-ff8`.
  4. Actualizar remotos y configurar `user.name`/`user.email` por repositorio si aplica.

- Comando rápido para copiar la clave pública al portapapeles en PowerShell:
  - `Get-Content $env:USERPROFILE\\.ssh\\id_ed25519_mitiakamara.pub -Raw | clip`
  - `Get-Content $env:USERPROFILE\\.ssh\\id_ed25519_ff8.pub -Raw | clip`


### Repos GitHub activos

| Repo | Cuenta | Proyecto | URL |
|------|--------|---------|-----|
| `dungeon-master-ai` | `Mitiakamara` (personal) | SAM | https://github.com/Mitiakamara/dungeon-master-ai |
| `flexflow8-site` | `fcorrea-ff8` (empresa FF8) | FF8 | https://github.com/fcorrea-ff8/flexflow8-site |

> ⚠️ `flexflow8-site` tiene su **propio `.git/`** dentro de `projects/FF8/flexflow8-site/` y es un repo **independiente** del repo Antigravity. No usar `git` desde la raíz del workspace para commits de FF8.

### Cuentas GitHub en `gh` CLI

Ambas cuentas están registradas en el `gh` CLI local. Para cambiar de cuenta activa:

```bash
# Cambiar a cuenta FF8
gh auth switch --user fcorrea-ff8
gh auth setup-git   # ← Obligatorio después de cambiar, para sincronizar credenciales de git HTTPS

# Cambiar a cuenta personal (SAM)
gh auth switch --user Mitiakamara
gh auth setup-git   # ← Igual, siempre ejecutar esto después de cambiar
```

> ⚠️ Sin `gh auth setup-git`, el `git push` va a fallar con "Repository not found" porque el credential helper de git sigue usando el token de la cuenta anterior.

---

## Proyectos

| Proyecto | Carpeta | Estado | Descripción |
|---------|---------|--------|-------------|
| [SAM](#sam-storytelling-ai-master) | `projects/SAM/` | En desarrollo activo | AI Dungeon Master para D&D 5e |
| [FF8](#ff8--flex-flow-8) | `projects/FF8/` | Producción activa | Plataforma fintech de financiamiento de iniciales para dealers de autos en South Florida |

---

## SAM — Storytelling AI Master

### ¿Qué es?
Aplicación web de Dungeon Master con IA para D&D 5e. SAM es un DM virtual con personalidad sarcástica y humor oscuro que narra historias, aplica reglas, gestiona combate/loot y soporta campañas multijugador.

### Stack

| Capa | Tecnología | Hosting |
|------|-----------|---------|
| Frontend | Next.js 16 + TypeScript + shadcn/Radix + Tailwind v4 | Vercel |
| Backend | FastAPI (Python 3) | Render |
| Base de datos | Supabase PostgreSQL + pgvector | Supabase Cloud |
| LLM | Google Gemini Flash (via LangChain) | Google Cloud |
| Embeddings | `gemini-embedding-001` (768 dims) via `google-genai` SDK (`client.models.embed_content()`) | Google Cloud |
| Auth | Supabase JWT + RLS en todas las tablas | Supabase |
| Avatares | DiceBear API (pública, gratuita, seed-based) | — |

### Estructura de archivos

```
projects/SAM/
├── SAM_progress_log.md              # Log de progreso y decisiones
├── .gitignore

├── backend/
│   ├── server.py                    # FastAPI app: /api/chat, /api/roll, /api/version
│   ├── requirements.txt             # Dependencias Python
│   ├── .env                         # SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY
│   │
│   ├── app/
│   │   ├── core/
│   │   │   ├── dice.py              # DiceRoller: formato AXdY+B, secrets.randbelow()
│   │   │   └── security.py          # Verificación JWT via supabase.auth.get_user()
│   │   ├── routers/
│   │   │   ├── campaigns.py         # CRUD campañas + upload PDF módulos (GM-only)
│   │   │   ├── characters.py        # CRUD personajes + import PDF ficha via Gemini
│   │   │   └── messages.py          # Sistema de mensajería privada (commlink)
│   │   ├── services/
│   │   │   ├── ai.py                # AIHelper: SAM Brain (Gemini + LangChain tools, native SDK embeddings 768d)
│   │   │   ├── ingestion.py         # PDF/EPUB → chunks → native genai.embed_content (768d) → Supabase direct insert
│   │   │   ├── admin.py             # Comandos /checkpoint /load /reset /list
│   │   │   └── tools/
│   │   │       ├── compendium_tools.py  # search_spells, search_monsters, search_items (native SDK embeddings)
│   │   │       └── game_mechanics.py   # apply_damage, apply_healing, give_loot
│   │   └── scripts/
│   │       ├── seed_*.py            # Seeders: spells, monsters, items, compendium
│   │       ├── parse_*.py           # Parsers de JSON D&D 5e
│   │       └── *_data.json          # Datos compendio: items, monsters, spells
│   │
│   ├── agents/                      # Multi-agent system (conectado a server.py, ai.py como fallback)
│   │   ├── __init__.py
│   │   ├── dice.py              # DiceRoller: secrets.randbelow(), roll_advantage/disadvantage
│   │   ├── rules.py             # XP_THRESHOLDS, calculate_hp_change, check_hit, check_save
│   │   ├── combat_state.py      # CombatState: initiative, turns, NPC HP — máquina de estado
│   │   ├── mechanic.py          # MechanicEngine: motor D&D 5e Python puro (cero LLM)
│   │   ├── interpreter.py       # IntentInterpreter: LLM prompt corto → JSON intent estructurado
│   │   ├── narrator.py          # Narrator: LLM creativo que narra hechos pre-calculados
│   │   ├── knowledge.py         # KnowledgeService: RAG sobre módulos de campaña + compendio D&D 5e
│   │   └── orchestrator.py      # SAMOrchestrator: pipeline Interpreter→Mechanic→Narrator
│   │
│   └── schema*.sql                  # Esquemas de BD (iterativos, el más reciente es phase11_schema.sql)

└── frontend/
    ├── app/
    │   ├── page.tsx                 # Página principal del juego
    │   ├── layout.tsx               # Root layout (theme, toaster)
    │   ├── admin/page.tsx           # Panel admin del GM
    │   └── auth/callback/page.tsx   # OAuth callback de Supabase
    ├── components/
    │   ├── game-layout.tsx          # Layout 3 paneles (left | chat | right)
    │   ├── chat-interface.tsx       # Chat principal
    │   ├── dice-tray.tsx            # UI de tiradas de dados
    │   ├── character-sheet-dialog.tsx
    │   ├── character-create-dialog.tsx
    │   ├── campaign-module-upload.tsx # Dialog para subir PDF/EPUB de módulos (GM-only)
    │   ├── character-list.tsx
    │   ├── party-roster.tsx         # Roster de otros personajes en la campaña (HP status)
    │   ├── sidebar-left.tsx         # Selección de campaña/personaje + party roster
    │   ├── sidebar-right.tsx        # HP, AC, condiciones del personaje
    │   ├── profile-menu.tsx
    │   ├── admin/sam-tuner.tsx      # Ajustes de dificultad/tono del GM
    │   ├── commlink/commlink-dialog.tsx  # Mensajería privada
    │   └── ui/                      # Componentes shadcn (button, dialog, etc.)
    ├── lib/
    │   ├── api.ts                   # authenticatedFetch() con JWT + NEXT_PUBLIC_API_URL
    │   ├── utils.ts
    │   └── supabase/
    │       ├── client.ts            # Cliente Supabase browser-side
    │       ├── server.ts            # Cliente Supabase server-side
    │       └── middleware.ts
    ├── hooks/
    │   └── use-realtime.ts          # Suscripción Supabase Realtime (WebSocket)
    ├── middleware.ts                 # Auth middleware Next.js
    ├── .env.local                   # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_*
    └── package.json
```

### Base de datos — Tablas principales

| Tabla | Propósito |
|-------|----------|
| `profiles` | Usuarios (FK a `auth.users` de Supabase) |
| `campaigns` | Campañas (gm_id, status, settings JSONB) |
| `characters` | Personajes (stats, HP, inventario como JSONB) |
| `messages` | Chat con resultados de dados y visibilidad |
| `private_messages` | Mensajería privada entre jugadores |
| `documents` | RAG: chunks de PDFs con `embedding vector(768)` |
| `spells` | Compendio hechizos D&D 5e (con embeddings) |
| `monsters` | Stat blocks monstruos (con embeddings) |
| `items` | Ítems/armas/armaduras (con embeddings) |
| `checkpoints` | Saves de campaña: `chat_history jsonb`, `character_states jsonb` |

**RPCs clave de Supabase:**
- `match_documents(query_embedding, threshold, count)` — RAG retrieval de módulos de campaña
- `match_compendium(query_embedding, threshold, count, table_name)` — Búsqueda semántica en compendio

### Flujo de arquitectura

```
Frontend
  └── lib/api.ts → authenticatedFetch() con JWT
       ↓ HTTPS
Backend — server.py (FastAPI)
  ├── /api/chat
  │     ├── Verifica JWT (security.py)
  │     ├── Detecta comandos /cmd → admin.py (checkpoint/load/reset)
  │     └── AIHelper.generate_response()
  │           ├── Embed mensaje → gemini-embedding-001 (768 dims)
  │           ├── match_documents RPC (RAG)
  │           ├── Gemini Flash + LangChain tools (hasta 3 iteraciones)
  │           │     ├── compendium_tools: search_spells/monsters/items
  │           │     └── game_mechanics: apply_damage/healing/give_loot
  │           └── Parsea tags <UPDATE> <LOOT> <IMAGE>
  ├── /api/roll → dice.py (DiceRoller)
  ├── /api/characters/import → Gemini analiza PDF de ficha
  └── /api/campaigns/{id}/modules → ingestion.py (PDF→vector→Supabase)
       ↓
Supabase PostgreSQL + pgvector
```

### Tags especiales en respuestas de SAM
- `<UPDATE>` — Cambios de HP/XP/gold → actualiza BD
- `<LOOT>` — Otorga ítems al inventario del personaje
- `<IMAGE>` — Dispara generación de imagen (Gemini multimodal)
- `<XP_GAIN>` — Otorga experiencia al personaje

### Dependencias Python clave
```
fastapi, uvicorn, pydantic
supabase, pyjwt, python-dotenv
langchain==1.2.13, langchain-google-genai==3.2.0, langchain-community==0.4.1
google-genai
pypdf, unstructured, python-multipart
```

### Dependencias JS/TS clave
```
next, react, typescript
@supabase/supabase-js, @supabase/ssr
@radix-ui/*, tailwindcss, shadcn
lucide-react, sonner, next-themes
```

### Notas de despliegue
- **Vercel:** Root Directory → `projects/SAM/frontend` (pendiente config manual)
- **Render:** Root Directory → `projects/SAM/backend` ✅ (live: `https://sam-backend-mg0j.onrender.com`)
- **Render start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
- **Render build command:** `pip install -r requirements.txt`
- Los esquemas de BD son iterativos; el más reciente es `phase11_schema.sql`

### Estado actual (Abr 2026)
- Backend live en Render (`https://sam-backend-mg0j.onrender.com`), Root Directory: `projects/SAM/backend`
- Frontend en Vercel (`sam-weld-tau.vercel.app`) — config Root Directory: `projects/SAM/frontend`
- 70+ commits en main (último: `d567718`, 1 Abr 2026)
- **Single-player funcional y testeado:** login → personaje → chat → dados → loot → XP → checkpoints
- **Upload PDF de módulos:** Integrado en admin campaign manager, vectoriza con gemini-embedding-001 (768d)
- **LangChain 1.x stack:** `langchain==1.2.13`, `langchain-core==1.2.22`, `langchain-google-genai==3.2.0` (thought_signature support), `langchain-community==0.4.1`. Modelo: `gemini-2.5-flash` (pineado).
- **SDK migrado a `google-genai`:** Todo el código runtime usa el nuevo SDK (`from google import genai`). Legacy `google-generativeai` eliminado.
- **Gemini resilience (3 capas):** (1) `langchain-google-genai==3.2.0` soporta `thought_signature`. (2) Fallback sin tools con historial limpio + inline tags. (3) Tool results capturados se inyectan en fallback response.
- **Context-aware prompting:** AI history se lee de BD (últimos 20 msgs por campaign_id) en vez de frontend. Campaign lock (`asyncio.Lock`) serializa respuestas de SAM por campaña.
- **Combat turn tracking:** Tag `<COMBAT>` en system prompt → backend parsea y actualiza `campaigns.settings.combat` → frontend muestra initiative banner con turno actual resaltado, input bloqueado cuando no es tu turno (NPCs no bloquean).
- **Multiplayer completo (sesiones 18 Mar – 1 Abr):**
  - Mensajes filtrados por campaign_id, Realtime scoped, header dinámico
  - sender_id + burbujas diferenciadas (propios/otros/SAM), `[CharacterName]` prefix en AI prompt
  - **Shadow variable fix:** `msg_sender` en loop de historial, `sender_name` (parámetro) intacto para mensaje actual
  - **Identity rule robusta:** 6 reglas absolutas, prefixes son automáticos del sistema, SAM nunca pide identificación
  - Selector de campaña, party roster con HP + **presencia online/offline** (Supabase Presence API)
  - Sin optimistic update, dedup por id de BD
  - Admin commands GM-only, `/reset` broadcast + clear combat state
  - Typing indicator via Supabase Broadcast
  - **Tab notifications:** unread count dinámico, sonido (Web Audio API), alerta de turno
  - **Visibility resync:** re-fetch al volver de background (visibilitychange + online)
- **Admin panel completo:** Campaign manager (crear/activar/desactivar/eliminar + módulos PDF unificados), invitaciones (códigos 6 chars, max_uses, expiración), user management (role/status toggle, delete con confirmación), campaign controls (reset/checkpoint/combat clear), SAM Neural Tuner conectado al AI
- **Sistema de invitaciones:** 5 endpoints backend + signup page con validación de código en 2 pasos + auto-profile trigger
- **SAM Neural Tuner → AI:** Difficulty/creativity/lethality en `campaigns.settings` afectan system prompt dinámicamente
- **Status fields normalizados:** `hp→hp_current`, `wallet→money`. Migration script ejecutado.
- **Character sheet responsive:** Tabs scrollables, grids adaptativos, padding compacto mobile.
- **stripSystemTags expandido:** Limpia `[SYSTEM EVENT]` echoes, Calculation lines, tool call text, `<COMBAT>` tags, failed search results. Role-aware: solo limpia artifacts de Gemini en mensajes de SAM, no en tiradas de dados de jugadores.
- **Multiplayer pendiente:** Realtime para nuevos commlink messages, marcado de leído al abrir
- **Multi-agent architecture (integrado 2 Abr 2026):** `backend/agents/` con separación de responsabilidades. `DiceRoller` (secrets.randbelow), `Rules` (tablas D&D 5e), `CombatState` (máquina de estado), `MechanicEngine` (Python puro, cero LLM), `IntentInterpreter` (LLM prompt corto → JSON), `Narrator` (LLM creativo solo narra, regla no-level-up), `SAMOrchestrator` (coordinador del pipeline), `KnowledgeService` (RAG). Conectado a `server.py` con fallback a `ai.py` legacy.
- **Self-damage flow:** Intent type `self_damage` permite que jugadores se autolesionen, caigan en trampas, etc. MechanicEngine aplica el daño, state_updates lo persiste.
- **Healing items:** Pociones de curación reconocidas (Healing/Greater/Superior/Supreme) con `is_healing: true` + `healing_dice`. Pending roll → MechanicEngine aplica curación al target (self o party member).
- **CR balancing:** Tablas `CR_XP_VALUES` y `ENCOUNTER_THRESHOLDS` en `rules.py`. `get_recommended_cr_range()` calcula single/pair/group/boss CR según nivel del party. Inyectado en `campaign_context` del narrador.
- **Character delegation:** Comandos `/delegate <name>` y `/undelegate <name>` permiten al GM ceder control de un personaje a SAM (útil para jugadores ausentes). Nueva columna `characters.controlled_by`. En combate, el orquestador trata a delegados como NPCs en `_resolve_npc_turns`.
- **Campaign memories:** Tabla `campaign_memories` con tipos (fact/npc/location/plot/item/decision) + importance 1-10 + embedding vector(768). `MemoryService` extrae hechos narrativos automáticamente después de cada respuesta de SAM (gemini-2.5-flash, max 3 facts <100 chars). Fire-and-forget background task — no bloquea al jugador. Memorias inyectadas en `campaign_context` del narrador para continuidad entre sesiones. Recuperación de JSON truncado via regex como fallback.
- **`/memory` command:** GM puede gestionar memorias desde el chat: `/memory list` (top 20), `/memory add <type> <text>` (manual, importance=7), `/memory delete <#N|UUID>` (por número de listado o UUID directo).
- **Commlink recipients:** `GET /api/messages/recipients?campaign_id=X` lista party members + entrada `S.A.M. (DM)` con `user_id=null`. Frontend ahora usa dropdown real en lugar de input de texto libre. Sender names en inbox se resuelven a nombres reales (`S.A.M.`, propio personaje, o nombre del otro player). `PrivateMessageCreate.receiver_id` ahora es `Optional[str]` para soportar mensajes a SAM.
- **PDF character import endurecido:** `parse_character_pdf()` con `max_output_tokens=65536` + `thinking_budget=0` (gemini-2.5-flash quemaba todo el budget en thinking interno). `response_mime_type="application/json"` fuerza JSON estructurado. Cleanup defensivo de trailing commas + 2do intento agresivo si falla. Prompt reforzado para extraer ALL spells/inventory de TODAS las páginas (4-6 pages). Actions/bonus_actions/reactions skip standard 5e actions. Nuevo campo `status.spell_slots` con `{N: {total, used}}` por nivel.
- **Spell slots tracking:** Panel interactivo en character sheet dialog (tab Spells, encima de la tabla). Sort numérico de niveles, click en chip = gastar slot, botón `−` = recuperar. Visual exhausted con `opacity-50 + border red`. **Bug crítico resuelto:** el `useEffect` reconstruía `formData.status` field-by-field y descartaba `spell_slots` (mismo issue que `saving_throws`). Spells deduplicados por `name-level`.
- **Resource consumption automático:** `interpreter` extrae `spell_level` del intent (0=cantrip, 1+=leveled, soporta upcast). `orchestrator` valida slots disponibles después de `process_spell()` (warning "spell fizzles" si no hay) y emite `state_update spell_slot_consume`. Para items: `state_update inventory_remove` con qty=1. `server.py` tiene handlers nuevos para ambos tipos, defensive (log warning sin crashear si el slot/item no existe).
- **`/gold` admin command:** GM puede ajustar dinero con `/gold <character> <±amount> <coin>`. Soporta nombres con espacios, valida `cp/sp/ep/gp/pp`, clamp a 0.
- **Auto-refresh character post-SAM:** El listener Realtime de `messages` en `chat-interface.tsx` (que ya escuchaba INSERTs para el chat) detecta `role === 'assistant'` y dispara el callback `onSamMessageReceived` que viene de `game-layout.tsx`. El callback hace `setTimeout(fetchCharacterData, 1500)` con `selectedCharacter.id` capturado en closure fresco via `useCallback`. Anteriormente había un segundo `useRealtime` duplicado que no funcionaba — Supabase no garantiza routing limpio cuando un mismo cliente se subscribe dos veces a la misma table con filtros distintos.
- **Character sheet responsive completo:** Combat vitals `grid-cols-2` mobile (2×2) / `sm:flex` desktop. HP row normalizado (mismo h/text/px para Max/Current/Temp). Spells responsive cols `grid-cols-6 sm:grid-cols-12` (mobile: Lvl/Name/Time, desktop: todas). Spell sorting clickeable (level/name con `▲`). Attacks inline con `break-all` y `overflow-x-hidden`. Bio & Gear siempre stacked (`grid-cols-1`). Sidebar header `pr-10 md:pr-4` para evitar X overlap.
- **Mini sheet redesign:** Spell Slots dots (`1: ●●●○` purple/gray) + Gold compact (`15 GP · 5 SP` amber) reemplazan Ready Attacks y Spells Prepared en el sidebar character card.
- **`pending_player_roll` persistence:** Sobrevive entre requests via `combat_state` en `campaigns.settings`. Permite flujos como "tira de daño" → siguiente mensaje del jugador con su tirada.
- **Mobile UX:** `h-[100dvh]` (dynamic viewport), `pb-safe` (iOS notch), header compacto en mobile (h-9), dice tray con botones pequeños + auto-close al rolear, input area con `mb-2` extra.
- **Completitud: ~95%** (app funcional) con arquitectura multi-agente integrada
- Ver `SAM_progress_log.md` para detalle completo

---

## FF8 — Flex Flow 8

### ¿Qué es?
Plataforma fintech de **financiamiento de down payments (iniciales)** para dealers de autos en South Florida. Modelo de negocio full-recourse (dealer garantiza el préstamo). Los deals van de $1,500–$3,000 principal, a 10–14 pagos quincenales. El dealer respalda cualquier saldo impago.

### Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| Base de datos core | SQL Server | Toda la contabilidad de deals, pagos, repos |
| CRM operativo | Airtable (Base ID: `appWaO56w2bSrBccg`) | Aplicaciones, dealers, cobranza, inversores |
| Automatización | Make.com | Webhooks Airtable → OneDrive → PandaDocs |
| Formularios de campo | Fillout.com | GPS capture, video upload |
| Evidencia de campo | Timestamp Camera Enterprise | Video geolocalizado con Network Time anti-fraude |
| Almacenamiento videos | Microsoft OneDrive | `/FF8/Dealers/[DealerName]/Evidence/` |
| Firma electrónica | PandaDocs | Via Make.com al crear aplicación |
| SMS/Voz | Twilio | Credenciales en `Twilio Credentials.txt` |
| Website (nuevo) | Next.js 16 + Netlify | `projects/FF8/flexflow8-site/` — en construcción activa |
| Website (legacy) | Wix | flexflow8.com activo mientras migra |
| Scripts de análisis | Python (pandas, numpy) | Modelos financieros, ETL, proyecciones |
| Automatización Airtable | JavaScript (Airtable Scripting) | Generación de pagos mensuales |

### Estructura de archivos

```
projects/FF8/
├── Automatrix (AMX)/                   # Capa de conocimiento para agentes IA
│   ├── # 🤖 Automatrix (AMX) – FF8.md  # CRÍTICO: Reglas de negocio, esquema DB, cálculos
│   ├── AMX_Tables_Summary_2025-08-26.md # Relaciones de tablas y columnas
│   ├── Production_Query_Analysis.md    # Updates al schema por hallazgos en producción
│   ├── Resumen de tablas y relaciones.txt
│   ├── FF8_Bracket_Movement_Reports.md # 3 SQL adaptados de Get Financed: Weekly Collections, Bracket Snapshot, Bracket Movement
│   ├── FF8_Collections_Master_Report_Spec_v3.md # Spec v3.1: 36 columnas, reporte maestro para agente AI de cobranzas
│   ├── FF8_Collections_Master_Report.sql # SQL v3.1: genera el reporte maestro (AMX → .xlsx → Make → Claude AI)
│   ├── Out_For_Repo_Report.sql         # Cuentas Out for Repo con DIN, descuentos, interest due
│   └── HASHEDSSNREPAYFEED_Query.sql    # Últimas 30 cuentas con hashed SSN
│
├── COMERCIAL/                          # Business Intelligence y marketing
│   ├── FF8_Website_SEO_Guide.md
│   ├── FF8_Content_For_Word.txt / _EN.txt
│   ├── project_2026.py                 # Simulador de flujos de caja por cohorte
│   └── analyze_*.py                    # 12+ scripts de análisis financiero
│
├── RRHH/                               # Recursos humanos y operaciones de campo
│   ├── FF8_Field_Sales_Policies.md     # Territorios, ética, actividad CRM
│   ├── FF8_CRM_Recommendation.md       # Estrategia Fillout + Airtable
│   ├── FF8_Field_Tool_Setup_Guide.md   # Setup Fillout + Timestamp Camera
│   ├── FF8_Make_Scenario_Blueprint.md  # Blueprint: Fillout → OneDrive → Airtable
│   ├── FF8_Independent_Contractor_Agreement.md
│   ├── FF8_NDA.md
│   ├── FF8_Timestamp_Camera_*.md       # Guías admin/config ES/EN
│   └── [Recruitment docs, interview guides, candidate reviews]
│
├── Inversionistas/                     # Relaciones con inversores
│   └── scripts/                        # Análisis Excel inversores
│
├── Migration/
│   ├── generate_payments.js            # Script Airtable: genera pagos mensuales de interés
│   └── extract_data.py                 # ETL: Excel inversores → CSV → Airtable
│
├── automations/make/
│   └── New Application - Create & Send PandaDocs.blueprint.json
│
└── flexflow8-site/                     # Sitio público + portales (Next.js, repo independiente)
    ├── DESIGN_SYSTEM.md                # Paleta completa, tipografía, componentes
    ├── netlify.toml                    # @netlify/plugin-nextjs, build: npm run build, publish: .next
    ├── src/
    │   ├── app/
    │   │   ├── globals.css             # Tailwind v4 @theme: tokens teal/pink/navy + mesh blob keyframes
    │   │   ├── layout.tsx              # Root layout: DM Sans + JetBrains Mono + JSON-LD schema + metadataBase
    │   │   ├── sitemap.ts              # Sitemap dinámico (7 URLs, /sitemap.xml)
    │   │   ├── robots.ts              # robots.txt (allow /, disallow /portal/ + /api/)
    │   │   ├── icon.png                # Favicon (auto-detectado por Next.js App Router)
    │   │   ├── api/
    │   │   │   ├── auth/check-email/route.ts  # Email validation API (service role, pre-OTP gate)
    │   │   │   ├── auth/me/route.ts          # GET: returns authenticated user's role (service role, bypasses RLS)
    │   │   │   ├── auth/track-login/route.ts  # POST: update last_login via service role (called from client callback)
    │   │   │   ├── dealer/                    # Phase 3 — Dealer API routes
    │   │   │   │   ├── portfolio/route.ts     # Supabase portfolio_data by portfolio_id + Airtable frequency enrichment
    │   │   │   │   ├── applicants/route.ts    # Airtable applicants (filter by PortfolioID)
    │   │   │   │   ├── din/route.ts           # Airtable DINs (Default Process filter)
    │   │   │   │   └── profile/route.ts       # Airtable dealer profile by email
    │   │   │   ├── admin/                     # Admin Settings API routes
    │   │   │   │   └── users/
    │   │   │   │       ├── route.ts          # GET all users + POST new user (admin only, service role)
    │   │   │   │       └── [id]/route.ts     # PUT update user + DELETE soft-delete (admin only)
    │   │   │   ├── broker/                    # Phase 4 — Broker API routes
    │   │   │   │   ├── profile/route.ts       # Airtable Brokers table (by email match)
    │   │   │   │   ├── accounts/route.ts      # Airtable Applicants filtered by {Broker}
    │   │   │   │   ├── commissions/route.ts   # Same data + fee summary + monthly breakdown
    │   │   │   │   ├── dealers/route.ts       # Linked dealers + CRM enrichment
    │   │   │   │   ├── crm/route.ts           # CRM Interactions (name-based broker post-filter + optional dealerId filter)
    │   │   │   │   └── buybacks/route.ts      # DINs: Pipeline Status='Default Process' filtered by {Broker}
    │   │   │   ├── collections/                # Collections module API routes
    │   │   │   │   ├── ingest/route.ts        # POST: JSON ingestion (API key auth, batch upsert)
    │   │   │   │   ├── upload/route.ts        # POST: xlsx upload (local dev fallback, production uses Netlify Function)
    │   │   │   │   ├── summary/route.ts       # GET: role-filtered KPI summary from ai_analysis
    │   │   │   │   └── accounts/route.ts      # GET: role-filtered account list with sorting/pagination
    │   │   │   └── investor/                  # Phase 5 — Investor API routes
    │   │   │       ├── profile/route.ts       # Airtable Investors table (by email or investorId)
    │   │   │       ├── loans/route.ts         # Airtable Loans table (by Investor Email)
    │   │   │       └── payments/route.ts      # Airtable Interest Payments table (by Investor Email)
    │   │   ├── auth/callback/page.tsx    # Client-side auth callback: PKCE exchange + role redirect (replaced server route.ts)
    │   │   ├── (public)/               # Grupo de rutas: Navbar + Footer
    │   │   │   ├── layout.tsx
    │   │   │   ├── page.tsx            # Home
    │   │   │   ├── dealers/page.tsx    # For Dealers
    │   │   │   ├── customers/page.tsx  # For Customers (payments: PayNearMe + phone)
    │   │   │   ├── about/page.tsx      # About
    │   │   │   ├── contact/page.tsx    # Contact (form funcional, Resend API + honeypot + rate limit)
    │   │   │   ├── terms/page.tsx      # Terms & Conditions
    │   │   │   ├── privacy/page.tsx    # Privacy Policy
    │   │   │   └── login/              # Magic link login (layout.tsx metadata + page.tsx client form)
    │   │   └── portal/                 # Auth-protected portal routes
    │   │       ├── layout.tsx          # Server: auth check + fetch role → PortalSidebar
    │   │       ├── page.tsx            # Server: redirect to /portal/[role]
    │   │       ├── dealer/
    │   │       │   ├── page.tsx                     # Dealer portal server page → MobileWrapper
    │   │       │   └── DealerPortalMobileWrapper.tsx # Client: useIsMobile → DealerPortalMobile | DealerTabs
    │   │       ├── broker/
    │   │       │   ├── page.tsx                     # Broker portal server page → MobileWrapper
    │   │       │   └── BrokerPortalMobileWrapper.tsx # Client: useIsMobile → BrokerPortalMobile | BrokerTabs
    │   │       ├── investor/
    │   │       │   ├── page.tsx                     # Investor portal server page → MobileWrapper
    │   │       │   └── InvestorPortalMobileWrapper.tsx # Client: useIsMobile → InvestorPortalMobile | InvestorTabs
    │   │       ├── admin/
    │   │       │   ├── page.tsx                     # Admin portal (desktop only)
    │   │       │   ├── AdminMobileMessage.tsx       # Shows "Desktop Required" on mobile
    │   │       │   └── investors/page.tsx           # Admin Investor View (InvestorTabs isAdmin)
    │   │       ├── collections/
    │   │       │   └── page.tsx                     # Collections dashboard: routes by collections_role (admin/supervisor/collector)
    │   │       └── unauthorized/page.tsx
    │   ├── lib/supabase/
    │   │   ├── client.ts              # Browser client (createBrowserClient)
    │   │   ├── server.ts              # Server client (createServerClient + cookies)
    │   │   └── middleware.ts           # Middleware client (session refresh + /portal protection)
    │   ├── types/
    │   │   ├── auth.ts                # UserRole + UserStatus types + UserProfile interface (status, display_name, last_login)
    │   │   ├── dealer.ts             # PortfolioRecord, ApplicantRecord, DINRecord (+ collectionsCommsDate), DealerProfile types
    │   │   ├── broker.ts             # BrokerProfile, BrokerAccount (+ veriffIdVerified), BrokerDealer, CRMInteraction, BrokerCommissionSummary, BrokerTab types
    │   │   ├── investor.ts          # InvestorProfile, InvestorLoan, InterestPayment, InvestorTab types
    │   │   ├── collections.ts        # Collections module types (SnapshotRow, AIAnalysis, role-filtered responses)
    │   │   └── leaflet-heat.d.ts     # TypeScript declarations for leaflet.heat
    │   ├── migrations/
    │   │   ├── 001_users_table.sql    # Supabase: users table + RLS + auth trigger
    │   │   ├── 002_create_portfolio_data.sql  # Supabase: portfolio_data table + indexes
    │   │   ├── 003_add_last_login.sql # Add last_login + display_name columns to users table
    │   │   └── 004_collections_tables.sql # Collections: daily_snapshots, ofr_snapshots, ai_analysis, chat_history + RLS
    │   ├── hooks/
    │   │   └── useIsMobile.ts          # Mobile detection hook (768px breakpoint)
    │   ├── lib/
    │   │   ├── dates.ts                # parseAirtableDate() — timezone-safe date parsing for Airtable date-only strings
    │   │   └── mobileTheme.ts          # Dark mode color palette for mobile portals
    │   ├── middleware.ts               # Next.js middleware: session refresh + protect /portal/*
    │   └── components/
    │       ├── layout/
    │       │   ├── Navbar.tsx          # Sticky, glassmorphism on scroll, mobile hamburger
    │       │   ├── Footer.tsx          # navy bg, 4 cols: Services/Company/Legal/Brand
    │       │   └── PortalSidebar.tsx   # Auto-hide sidebar: hover-to-expand + pin/unpin, favicon when collapsed, role-based nav, logout wired
    │       ├── portal/mobile/          # Shared mobile portal components (dark mode)
    │       │   ├── MobileShell.tsx     # Full-screen layout: fixed header + scrollable content + bottom tab bar (safe-area)
    │       │   ├── MobileStatCard.tsx  # Compact metric card (label/value/sub)
    │       │   ├── MobileBadge.tsx     # Inline colored badge
    │       │   ├── MobileDPDBadge.tsx  # DPD badge: 0→Current, 1-29→amber, 30+→red
    │       │   └── MobileTimeSlicer.tsx # Time period selector (This Month | Last 3 mo. | Custom) + date pickers
    │       ├── portal/dealer/          # Phase 3 — Dealer portal components
    │       │   ├── DealerTabs.tsx      # Main tabbed container (4 tabs + DIN badge)
    │       │   ├── DealerPortalMobile.tsx # Mobile dark mode: 4 tabs (Dashboard w/ CSS bars chart, Portfolio, Resources, Buybacks)
    │       │   ├── DashboardTab.tsx    # Applicants overview: donut chart + status table + 3-level drill-down (sortable columns, UPPERCASE names) + time filter + VERIFF filter + conditional columns (ID Verification for Pending Client Signatures, Expected Funding Date for Pending Funding) + Dealer column (admin)
    │       │   ├── PortfolioTab.tsx    # Portfolio data table: sortable, searchable, color-coded days late, Frequency column (from Airtable), compact promise columns
    │       │   ├── ApplicationTab.tsx  # Dealer application link card + profile info
    │       │   ├── BuybacksTab.tsx     # Pending buybacks (DIN) table: expandable rows with BuybackTimeline + footer totals + summary cards
    │       │   └── AdminPortalClient.tsx # Admin wrapper: Dealer View | Broker View | Settings selector + dealer filter dropdown
    │       ├── portal/shared/          # Shared portal components
    │       │   └── BuybackTimeline.tsx  # Timeline (4 milestones + Today marker) + Financial Breakdown panel
    │       ├── portal/admin/           # Admin Settings components
    │       │   └── UserManagement.tsx  # Full user CRUD: table, add/edit modals, activate/deactivate, activity log, role filter pills, sortable columns
    │       ├── portal/investor/         # Phase 5 — Investor portal components
    │       │   ├── InvestorTabs.tsx    # Main tabbed container (3 tabs + admin investor dropdown)
    │       │   ├── InvestorPortalMobile.tsx # Mobile dark mode: 3 tabs (My Investment, Active Loans, Payment History + CSV)
    │       │   ├── MyInvestmentTab.tsx # Profile card, summary cards, beneficiaries. Admin: aggregated AUM + investor table
    │       │   ├── LoansTab.tsx        # Sortable loans table with expandable rows showing interest payments
    │       │   └── PaymentHistoryTab.tsx # Payment history with filters (Year/Loan/Status), Export CSV, footer totals
    │       ├── portal/broker/          # Phase 4 — Broker portal components
    │       │   ├── BrokerTabs.tsx      # Main tabbed container (5 tabs: Accounts, Commissions, Dealers, CRM + "New CRM Entry" Fillout link, Buybacks + badge; Activity Map admin-only)
    │       │   ├── BrokerPortalMobile.tsx # Mobile dark mode: 5 tabs (Accounts w/ TimeSlicer, Commissions, Dealers, CRM, Buybacks)
    │       │   ├── AccountsTab.tsx     # Dashboard: BarCharts (by-dealer + stacked portfolio quality) + pivot table + drill-down (w/ VERIFF badges) + Portfolio Health card. Recharts v3. UPPERCASE.
    │       │   ├── CommissionsTab.tsx  # Per-deal fee table + monthly breakdown (last 3 months) + time filter + Export CSV. UPPERCASE.
    │       │   ├── DealersTab.tsx      # Expandable rows with inline CRM, activity indicator. UPPERCASE.
    │       │   ├── CRMTab.tsx          # Expandable rows, GPS "Map" links (Google Maps), photo thumbnails, type filter. UPPERCASE.
    │       │   ├── BrokerBuybacksTab.tsx # Pending buybacks (DIN): expandable rows with BuybackTimeline, summary cards. UPPERCASE.
    │       │   ├── ActivityMap.tsx      # Admin-only: wrapper with data fetch, visits-only filter, date range, view mode toggle
    │       │   └── ActivityMapInner.tsx # Leaflet map: Markers (colored DivIcons) + Heatmap (leaflet.heat) modes. South Florida center.
    │       ├── collections/            # Collections module components
    │       │   ├── AdminDashboard.tsx  # Full admin view: KPIs, brackets, tabs (Queues/Dealers/Programs/Alerts/OFR), narrative, queue filter
    │       │   ├── SupervisorDashboard.tsx # All queues, no financials, attention list
    │       │   ├── CollectorDashboard.tsx  # Own queue only, priority contacts
    │       │   ├── ChatPanel.tsx       # AI chat assistant (slide-over desktop, full-screen mobile)
    │       │   ├── KPICard.tsx         # Metric card (light + dark variants)
    │       │   ├── BracketBar.tsx      # Horizontal bracket distribution bar (clickable segments)
    │       │   ├── AlertCard.tsx       # Severity-coded alert display
    │       │   ├── TimeSlicer.tsx      # Date picker (Today/Yesterday/Pick)
    │       │   └── AccountsTable.tsx   # Role-filtered accounts table with sortable columns
    │       └── ui/
    │           ├── MeshGradient.tsx    # 3 blobs CSS animados (blobDrift, 60-80s alternate)
    │           ├── FloatingShapes.tsx  # Paralelogramos FF8, variantes: light/dark/contact
    │           ├── HeroBackground.tsx  # Combina mesh + shapes + parallax (useScroll)
    │           ├── FadeInOnScroll.tsx  # whileInView fade+slide, prop delay para stagger
    │           └── LottieAnimation.tsx # Wrapper lottie-react (client component)
    ├── public/
    │   ├── icon.png                     # FF8 favicon (used by sidebar when collapsed)
    │   ├── logo-white.svg              # Logotipo texto blanco (para fondos oscuros)
    │   ├── logo-dark.svg               # Logotipo texto negro (para fondos claros)
    │   ├── og-image.png                # OG image 1200x630 (navy + logo, para social sharing)
    │   └── animations/                 # Lottie JSON animations (recolorizados a paleta FF8)
    │       ├── Home_Fintech_Services.json
    │       ├── Dealers_Handshaking___Collaboration.json
    │       ├── About_Business_Partners.json
    │       └── Contact_us_Lottie_animation.json
    ├── scripts/
    │   ├── recolor-lottie.js           # Recoloriza Lotties a paleta FF8
    │   ├── generate-og-image.js        # Genera OG image con sharp
    │   └── seed-portfolio.ts           # Import AMX XLSX → Supabase portfolio_data (npx tsx scripts/seed-portfolio.ts <file>)
    ├── netlify/
    │   └── functions/
    │       ├── portfolio-upload.js     # Netlify Function: recibe XLSX binary de Make.com → delete stale accounts per portfolio + upsert Supabase portfolio_data
    │       ├── collections-upload.js   # Netlify Function: recibe XLSX binary → parse → segment Active/OFR → upsert daily_snapshots + ofr_snapshots
    │       ├── collections-analyze.js  # Netlify Function: pre-compute KPIs server-side → save ai_analysis → Claude generates narrative bullets
    │       └── collections-chat.js     # Netlify Function: AI chat assistant — role-based context, conversation history, bilingual
    └── package.json                    # + recharts, xlsx, tsx (Phase 3) + react-leaflet, leaflet, leaflet.heat (Activity Map)
```

### Base de datos SQL Server — Tablas clave

| Tabla | PK | Propósito |
|-------|-----|----------|
| `DealsTable` | `AccountNumber` | Master record del deal. FK: BuyerCode, PortfolioId, StockNumber |
| `CustomerTable` | `CustomerCode` | Info del comprador (nombre, teléfono, email) |
| `PortfolioTable` | `PortfolioId` | Info del dealer |
| `InventoryTable` | `StockNumber` | Vehículo (Year, Make, Model, VIN) |
| `PaymentScheduleTable` | `PaymentScheduleId` | Calendario de pagos (DateDue, Amount, Status) |
| `DealPaymentTable` | `DealPaymentId` | Pagos recibidos (CollectedPrincipal, CollectedInterest) |
| `PaymentTransactionTable` | `PaymentTransactionId` | Journal de transacciones (join ambas tablas de pagos) |
| `Repossession` | `RepossessionId` | Eventos de repossession |
| `GetAccountBalances` | (VIEW) | `Principal` = UPB real. Siempre usar para saldo |

**Reglas críticas de negocio (Automatrix):**
- `AccountNumber` es el ÚNICO identificador de deal
- `FinanceAmount` = Balance inicial (no cambiar)
- UPB **siempre** viene de `GetAccountBalances.Principal`
- `DISCOUNT` es monto, no porcentaje
- `IsReversed = 0` es obligatorio en queries de `DealPaymentTable`
- Days Late = TODAY - DateDue **solo si** Status = 'Pending'
- Default operacional comienza a los **5 días** vencido

**Joins permitidos:**
```sql
DealsTable.AccountNumber = PaymentScheduleTable.AccountNumber
DealsTable.AccountNumber = DealPaymentTable.AccountNumber
DealsTable.AccountNumber = GetAccountBalances.AccountNumber
DealsTable.BuyerCode = CustomerTable.CustomerCode
DealsTable.PortfolioId = PortfolioTable.PortfolioId
DealsTable.StockNumber = InventoryTable.StockNumber
PaymentScheduleTable.PaymentScheduleId = PaymentTransactionTable.PaymentScheduleId
DealPaymentTable.DealPaymentId = PaymentTransactionTable.DealPaymentId
Repossession.AccountNumber = DealsTable.AccountNumber
```

### Flujo de operaciones

```
NUEVA APLICACIÓN:
Dealer aplica → Airtable (Applicants) → Make.com webhook
  → Get applicant details → PandaDocs (e-signature)
  → Fillout form (URL personalizada con dealer_name + application_id)
    → Vendor graba video con Timestamp Camera (GPS + Network Time)
    → Fillout submission → Make.com webhook
      → Download video → OneDrive /FF8/Dealers/[Name]/Evidence/
      → Airtable update: video link + "Pending Review"

COBRO MENSUAL:
generate_payments.js (Airtable Script, scheduled)
  → Fetch active loans → Check duplicates (Year-Month-LoanID)
  → Create interest payment records

ANÁLISIS FINANCIERO:
analyze_*.py / project_2026.py → pandas/numpy
  → Proyecciones por tier ($1500-$3000), escenarios 50-120 cuentas/mes
  → Capital needs, bad debt, ROI por cohorte (~25-31% por deal)
```

### Métricas de negocio actuales
- Portfolio: ~$1,178,729 balance
- Deals: $1,500–$3,000 principal, 12 pagos quincenales (estándar)
- Inversores APR: 12% anual (1% mensual)
- Costos fijos: ~$21,000/mes
- ROI estimado por deal: 25–31%

### Portal de Dealers (estado actual — Wix/Velo)

El portal actual vive en www.flexflow8.com. Dealers se logean con Wix Site Members, el backend Velo consulta Airtable y devuelve datos al frontend via custom elements (web components).

**4 tabs del portal:**
1. **Dealer Portfolio** — loans del dealer (Wix CMS `DealersData`, populado por Make.com desde CSVs de AMX)
2. **Pending Buybacks (DIN)** — deals en Default Process (Airtable `tblvCbb7qXARXhp0g`)
3. **Applicants Dashboard** — pipeline completo de aplicantes
4. **Account Settings** — perfil Wix Members

**Admin role:** PortfolioID=8 → ve todos los dealers sin filtro de portfolio

**⚠️ Seguridad crítica:** API key de Airtable está hardcodeada en `airtableUtilts.web.js` (Velo). **Rotar antes de cualquier migración.** CMS `DealersData` tiene permisos `ANYONE` para todo CRUD — corregir en migración.

**Arquitectura Velo (3 backend functions):**
- `getRecordsByDealerEmail(email)` → lookup dealer en Airtable Dealers table (`tbl4J5TTewQJT4TEW`)
- `getDINforDealersDisplay(portfolioId)` → DINs en Default Process, paginado (pageSize=100)
- `applicantsDashboard(portfolioId)` → pipeline completo, todos los campos

### flexflow8-site — Sitio Público (Next.js, en construcción)

**Path:** `projects/FF8/flexflow8-site/` — repo independiente (`fcorrea-ff8/flexflow8-site`)

**Stack:**

| Capa | Tecnología |
|------|-----------|
| Framework | Next.js 16 + TypeScript + App Router |
| Auth | Supabase Auth (magic link OTP, `@supabase/ssr` cookie-based, 5 roles) |
| Estilos | Tailwind CSS v4 (config via `@theme` en globals.css) |
| Animaciones | Framer Motion (parallax, scroll animations, floating shapes) + Lottie (lottie-react) |
| Fuentes | DM Sans + JetBrains Mono (next/font/google, self-hosted, display: swap) |
| Iconos | Lucide React |
| SEO | Metadata por página + Open Graph + Twitter cards + JSON-LD FinancialService + sitemap.xml + robots.txt + noindex login + absolute canonical |
| Deploy | Netlify (`@netlify/plugin-nextjs`) + 301 redirects Wix legacy URLs + www canonical |

**Páginas completadas:**
- `/` — Home: hero (Lottie fintech) + value props (3 cards) + how it works + CTA banner
- `/dealers` — For Dealers: hero (Lottie handshake) + deal terms bar + 6 benefits + 4 steps + full-recourse + FAQ + CTA
- `/customers` — For Customers: hero + 2 payment cards (Pay Online via PayNearMe + By Phone) + questions + CTA
- `/about` — About: hero (Lottie partners) + 3 valores + company info card
- `/contact` — Contact: hero (Lottie geométrico) + form funcional (Resend API → ff8@flexflow8.com + confirmation email al sender, honeypot anti-spam, rate limit 3/hr/IP) + contact info 2 columnas
- `/terms` — Terms & Conditions (9 secciones, texto legal)
- `/privacy` — Privacy Policy (10 secciones, texto legal)
- `/login` — Magic link login (email OTP, 3 states: form/loading/success)
- `/portal` — Auth-protected, redirects to `/portal/[role]`
- `/portal/dealer` — Dealer portal: 4 tabs (Dashboard, My Portfolio, Application Link, Pending Buybacks)
- `/portal/broker` — Broker portal: 5 tabs (Accounts, Commissions, Dealers, CRM, Buybacks) + Activity Map (admin)
- `/portal/investor` — Investor portal: 3 tabs (My Investment, Active Loans, Payment History)
- `/portal/admin` — Admin portal: Dealer View | Broker View | Investor View | Settings sub-nav, all data (no filters)

**Navbar:** Home, For Dealers, For Customers, About, Contact + Portal Login button (→ /login)

**Efectos visuales implementados:**
- `HeroBackground`: mesh gradient CSS + paralelogramos flotantes + parallax
- `FadeInOnScroll`: whileInView fade+slide con stagger
- `FloatingShapes` variantes: `light` (hero sections), `dark` (CTA banners navy), `contact` (periférico, opacidad 0.04)
- `LottieAnimation`: wrapper lottie-react (speed 0.5x via setSpeed, loop=false + 3s pause via onComplete/goToAndPlay), 4 animaciones recolorizadas a paleta FF8
- Navbar glassmorphism: `bg-white/80 backdrop-blur-md` on scroll
- Cards: `group-hover:scale-110` icon + `hover:-translate-y-1.5 hover:shadow-lg`
- Botones CTA: `hover:scale-[1.03] active:scale-[0.97]`

**Mobile Responsive Dark Mode (implementado):**
- All 3 portal roles (dealer/broker/investor) have dedicated mobile dark mode views
- **Hook:** `useIsMobile(768)` — detects viewport width, returns boolean
- **Theme:** `mobileTheme.ts` — dark color palette (bg: #0f1f30, card: #1e3450, teal/pink/navy accents)
- **MobileShell:** Fixed header (F8 logo + user info + logout) + scrollable content + bottom tab bar with badges and safe-area
- **MobileWrapper pattern:** Server page passes data → client MobileWrapper uses `useIsMobile()` → renders mobile or desktop component
- **Shared components:** MobileStatCard, MobileBadge, MobileDPDBadge, MobileTimeSlicer
- **Dealer mobile:** 4 tabs — Dashboard (CSS bars chart + drill-down + VERIFF filter + TimeSlicer), Portfolio (search + cards), Resources (link cards), Buybacks
- **Broker mobile:** 5 tabs — Accounts (TimeSlicer + stats), Commissions, Dealers (activity indicator), CRM (timeline), Buybacks
- **Investor mobile:** 3 tabs — My Investment (hero + beneficiaries), Active Loans, Payment History (year filter + CSV)
- **Admin mobile:** Shows "Desktop Required" message (AdminMobileMessage component)
- Portal layout: sidebar `hidden md:block`, main padding `p-0 md:p-8`
- All mobile styles are inline (not Tailwind), `position: fixed; inset: 0` for full-screen layout
- Dashboard uses **CSS horizontal bars** (not Recharts) for compact mobile rendering

**Auth (Phase 2 — implementado):**
- Supabase Auth via magic link (OTP, sin password)
- `@supabase/ssr` cookie-based: browser client, server client, middleware client
- Middleware (`src/middleware.ts`): session refresh en cada request, protege `/portal/*`
- Auth callback: `/auth/callback` → **client-side page** (not server route) — `createBrowserClient` handles PKCE exchange + hash fragments → fetch role via `/api/auth/me` → redirect `/portal/[role]`. Converted from `route.ts` to `page.tsx` for Netlify production compatibility
- Role endpoint: `/api/auth/me` (GET) — returns authenticated user's role using service role client (bypasses RLS). Used by login page + auth callback for client-side role fetching
- Track login: `/api/auth/track-login` (POST) — updates `last_login` via service role client, called fire-and-forget from callback page
- Email gate: `/api/auth/check-email` → service role query a `public.users`, bloquea OTP si email no registrado o `status !== 'active'`
- Login page: `/login` (client component, 3 estados: form/loading/success, valida email antes de enviar magic link, role fetch via `/api/auth/me`)
- Portal layout: server component, verifica auth, fetch role de `users` table via `createServiceClient()`, pasa props a PortalSidebar
- **Service role client:** Shared `createServiceClient()` in `lib/supabase/server.ts` — bypasses RLS. ALL API routes and portal pages use this for `public.users` reads (role, portfolio_id, status queries)
- **Airtable table IDs:** All moved to env vars (no hardcoded `tbl...` IDs in code). Env vars: `AIRTABLE_DEALERS_TABLE`, `AIRTABLE_APPLICANTS_TABLE`, `AIRTABLE_BROKERS_TABLE`, `AIRTABLE_INVESTORS_TABLE`, `AIRTABLE_LOANS_TABLE`, `AIRTABLE_PAYMENTS_TABLE`, `AIRTABLE_CRM_INTERACTIONS_TABLE`, `AIRTABLE_CRM_DEALERS_TABLE`
- PortalSidebar: auto-hide sidebar (collapses by default, hover-to-expand, Pin/Unpin toggle), shows favicon (`icon.png`) when collapsed, full logo when expanded. Nav items por rol, logout wired
- 5 roles: dealer, broker, investor, customer, admin
- SQL migration: `001_users_table.sql` (users table + RLS + auto-trigger en auth.users)
- Supabase `users` table: `id uuid → auth.users.id`, email, role (enum), status (enum: active/inactive/suspended), display_name, last_login, airtable_record_id, portfolio_id, base_id

**Dealer Portal (Phase 3 — implementado):**
- 4 tabs dentro de `/portal/dealer`: Dashboard | My Portfolio | Resources | Pending Buybacks
- Dashboard (Tab 1): Applicants overview con donut chart (recharts, % labels on slices), status table, 3-level drill-down (overview → filtered list → account detail), time filter (All Time / This Month / Last Month / Custom Range con date picker). Summary cards: Total Accounts, Active Loans (5 statuses: Pending Client Signatures, Pending Funding, Pending DMS Account Creation, Pending Loan Repayment, Default Process), Total Cash Advance, Avg Cash Advance. VIN in uppercase, **Customer names in UPPERCASE**. Level 2 drill-down has **sortable columns** (all headers clickable asc/desc/clear), Cash Adv Balance footer total, **conditional columns**: **ID Verification** (only for "Pending Client Signatures", color badges: Approved/Pending/Declined), **Expected Funding Date** (only for "Pending Funding"), **Dealer** column (admin-only). **Timezone-safe dates** via `parseAirtableDate()` helper (`src/lib/dates.ts`)
- My Portfolio (Tab 2): Supabase `portfolio_data` table enriched with **Frequency** from Airtable (`fetchFrequencyMap()`), sortable columns, search by account/name, color-coded Days Late (green/yellow/orange/red), summary cards (Total Accounts, Total UPB, Total Past Due). Compact text-xs layout for dense data display. Mobile: frequency in card subtitle
- Resources (Tab 3): Application Form link (from Airtable Dealers table), ACH Authorization Form, Card Authorization Form + dealer profile card
- Pending Buybacks (Tab 4): DIN records from Airtable (Pipeline Status = 'Default Process'). Columns: Account#, Customer, Dealer, DIN Notice#, DIN Amount, DIN Fee, DIN Total, Paid, Balance, Pay By Date, Days Past Due, Status. Footer totals for Paid and Balance. Summary cards (Total DINs, Total Balance, Overdue). DIN badge count in tab
- Admin portal (`/portal/admin`): sub-navegación Dealer View | Broker View | Investor View | Settings. Cada vista muestra los tabs del portal respectivo sin filtros de usuario. Dealer View incluye dropdown de filtro por dealer (service role client). Settings muestra User Management
- All summary cards have `hover:border-teal-300 hover:shadow-md` indicator. Tab buttons have `hover:bg-white hover:shadow-sm`
- 4 API routes: `/api/dealer/portfolio` (Supabase), `/api/dealer/applicants` (Airtable), `/api/dealer/din` (Airtable), `/api/dealer/profile` (Airtable)
- Airtable field name gotchas: lookup fields return arrays (use `firstStr()`/`firstNum()` helpers), field names are case-sensitive (e.g., `DIN past due days` lowercase, `DIN Payby Date` specific casing, `Dealer Name (from Dealer Name)` for resolved names vs record IDs)
- Admin detection: `role === 'admin' || portfolio_id === 8` → no portfolio filter en API queries
- Supabase `portfolio_data` table: importada via seed script (`npx tsx scripts/seed-portfolio.ts <xlsx>`)
- SQL migration: `002_create_portfolio_data.sql`

**Broker Portal (Phase 4 — implementado):**
- 5 tabs dentro de `/portal/broker`: Accounts Produced | Commissions | My Dealers | CRM | Pending Buybacks (+ Activity Map admin-only)
- Accounts Produced (Tab 1): All accounts originated through the broker. Dashboard (BarCharts + pivot table) with drill-down to detail table (Account#, Customer, Issue Date, Closing Type, Status, VERIFF badges). VERIFF column: Approved=green #00C4B4, Pending=yellow #F59E0B, Declined=red #EF4444. Summary cards: Total Accounts, Total Dealers, Funded This Month, Portfolio Health
- Commissions (Tab 2): Per-deal fee table with Fee Calc, Fee Paid Date, Fee Adjusted columns + footer totals. Monthly breakdown by Deal Month/Year. Paid/Pending filter buttons. Summary cards: Total Earned, Paid count, Pending count
- My Dealers (Tab 3): Dealers assigned to broker via linked records. Expandable rows showing inline CRM interactions. Activity indicator (green <30d, yellow 30-60d, red 60+d). Summary cards: Total Dealers, Active (30d), Inactive (60+d)
- CRM (Tab 4): Full list of CRM interactions. "New CRM Entry" button (top-right, teal filled, → Fillout form in new tab). Expandable rows with full notes, GPS "Map" link (Google Maps), photo thumbnails. Type filter (Visit/Call). Search by dealer/notes/outcome. Summary cards: Total Interactions, Visits, Calls
- Pending Buybacks (Tab 5): DINs filtered by broker name. Summary cards (Total DINs, Balance, Overdue). Expandable rows with BuybackTimeline (shared component). Dealer filter dropdown. Badge with count on tab. UPPERCASE
- Activity Map (Tab 6, admin only): Interactive Leaflet map centered on South Florida (26.0, -80.2). Toggle Markers/Heatmap. Type filter + date range. Uses react-leaflet + leaflet.heat. Dynamic import (SSR disabled)
- Broker identification: email matched against `Broker Email 1` OR `Broker Email 2` in Airtable Brokers table. Broker `Name` used to filter Applicants. CRM filtering: name-based post-filter (Broker → Dealers → resolve names → match interactions)
- CRM Airtable architecture: Interactions → CRM Dealers → Brokers (two-hop relationship, NO direct `{Brokers}` field on Interactions or CRM Dealers)
- 6 API routes: `/api/broker/profile`, `/api/broker/accounts`, `/api/broker/commissions`, `/api/broker/dealers`, `/api/broker/crm`, `/api/broker/buybacks`
- Airtable tables: Brokers, Applicants & Clients, CRM Dealers, CRM Interactions (all table IDs in env vars, no hardcoded IDs)
- Admin: sees all broker data without broker filter. Activity Map tab only visible in admin view
- Test user: `info@fjmsolutions.net` (role=broker) — FJM Solutions, 71 dealers
- **Shared component:** `BuybackTimeline.tsx` (in `portal/shared/`) — used by BOTH Dealer and Broker Buybacks tabs. Timeline with 4 milestones (Deal Issued → Collections → DIN Issued → Deadline) + Today marker + Financial Breakdown (Capital, DIN Fee, DIN Total, Paid, TOTAL DUE). Requires `collectionsCommsDate` field in DINRecord.

**Admin Settings — User Management (implementado):**
- Settings view dentro del admin portal (cuarto tab en sub-navegación: Dealer View | Broker View | Investor View | Settings)
- User table: Email, Display Name, Role (color badges), Portfolio ID, Status (color badges), Created, Last Login, Actions
- **Role filter pills:** All Roles | Dealer | Broker | Investor | Customer | Admin (with counts per role)
- **Sortable columns** on all table headers with ArrowUp/ArrowDown indicators (default sort: Created DESC)
- Add User modal: email (required, validated), role dropdown, portfolio_id (optional), display_name (optional)
- Edit User modal: role, portfolio_id, display_name, status. Email shown read-only
- Activate/Deactivate toggle inline per user row
- Activity Log section: last 20 logins sorted by `last_login DESC`
- 2 admin API routes: `/api/admin/users` (GET list + POST create), `/api/admin/users/[id]` (PUT update + DELETE soft-deactivate)
- Admin-only access: verified via Supabase auth + `role = 'admin'` check in `public.users`
- Service role client for all DB writes (bypasses RLS)
- Auth callback updated: tracks `last_login` on every login via service role client
- check-email API updated: enforces `status === 'active'`, blocks deactivated users from receiving magic link
- SQL migration: `003_add_last_login.sql` (adds `last_login timestamptz` + `display_name text` + index)

**Investor Portal (Phase 5 — implementado):**
- 3 tabs dentro de `/portal/investor`: My Investment | Active Loans | Payment History
- **Read-only** portal — investors can view but not modify data
- **Airtable base:** FF8 Investors (`appL8VY2KVjxRmBmE`) — separate from main FF8 base
- **Airtable tables:** Investors (`tblq1yhKrwMhzb8Er`), Loans (`tbl0Dku5zogcskPFM`), Interest Payments (`tblGugUZDvggtDYmx`)
- **ENV var:** `AIRTABLE_INVESTORS_BASE_ID=appL8VY2KVjxRmBmE`
- My Investment (Tab 1): Profile card (name, legal name, email, phone, address, type, representative, status). Summary cards (Total Invested, Active Loans, Annual Rate 12%, Monthly Interest Est.). Collapsible beneficiary section (up to 2 beneficiaries). Sensitive fields (Tax ID, bank info) excluded. Admin: aggregated view (Total AUM, Total Active Loans, Active Investors count, investor table)
- Active Loans (Tab 2): Sortable table (Loan#, Principal, Annual Rate, Daily Interest, Start/End Date, Term, Status). Expandable rows showing interest payments for each loan. Summary cards (Total Loans, Total Principal Invested, Avg Daily Interest). Status badges (green=Active, gray=other)
- Payment History (Tab 3): Chronological table of interest payments (Payment Date, Loan#, Principal, Days, Interest Amount, Period, Status). Summary cards (Total Interest Earned, YTD Interest, Last Payment Date, Next Expected). Filters: Year dropdown, Loan dropdown, Status buttons. Footer totals. Export CSV button (filename: `FF8_Interest_Payments_[YYYY-MM-DD].csv`)
- **Investor identification:** email matched case-insensitive (`LOWER({Email})`) against Investors table
- 3 API routes: `/api/investor/profile` (Airtable Investors table), `/api/investor/loans` (Airtable Loans table), `/api/investor/payments` (Airtable Interest Payments table)
- Admin: Investor View at `/portal/admin/investors` — dropdown filter by investor, sees all data without email filter. API routes accept `investorId` param and resolve to email via Investors table lookup
- Admin portal sidebar: Dealer View | Broker View | Investor View | Settings
- Contact note: "To update your information, contact FlexFlow8 at (954) 947-4781."
- **Airtable Investors field gotchas:**
  - `Active Loans` in Investors table is a **linked record field** returning array of record IDs (e.g. `["recXXX", "recYYY"]`), NOT a number — use `.length` for count
  - Interest Payments table has **NO** `Loan # (from Loan)` lookup field — extract loan number from `ID` field (format `"VK-111725 - Feb 2026"`) using regex `/^([A-Z]+-\d+)/i`
  - `Principal (from Loan)` and `Daily Interest` in payments table return **arrays** (e.g. `[20000]`, `[6.67]`) — `safeNum()` handles via `v[0]` extraction
  - `Investor Email` in Loans table is an **array lookup** (e.g. `["email@example.com"]`) — `safeStr()` handles via `v[0]` extraction
  - Sensitive fields present but excluded: Bank Name, Routing Number, Account Number, Account Type

**Pendiente (próximas fases):**
- DNS switch: flexflow8.com → Netlify
- Cancelar Wix después del go live

### Plan de migración: Wix → Netlify (v3, Feb 2026)

**Doc de referencia:** `FF8_Migration_Plan_v3_Full_Portals.docx` + `FF8_Dealer_Portal_Architecture.docx`

**Stack destino:**

| Capa | Tecnología |
|------|-----------|
| Hosting | Netlify |
| Auth | Supabase Auth (magic link, sin password) |
| Backend | Netlify Functions |
| Frontend | React / Next.js |
| Datos | Airtable (mismo) + Supabase `users` table (solo para roles) |

**5 roles / 5 portales:**
- **Dealer** (4 tabs) — migración del actual
- **Broker** (4 tabs) — nuevo: cuentas producidas, comisiones, mis dealers, CRM
- **Investor** (3 tabs) — nuevo: mi inversión, loans, historial de pagos (read-only)
- **Customer** — placeholder → redirect a PayNearMe
- **Admin** — PortfolioID=8, ve todo

**Supabase `users` table (única tabla nueva):**
```sql
id, email, role (dealer|broker|investor|customer|admin),
airtable_record_id, portfolio_id, base_id
```

**Airtable bases usadas:**
- `appWaO56w2bSrBccg` — FlexFlow8 (dealers, brokers, applicants, CRM)
- `appL8VY2KVjxRmBmE` — FF8 Investors (investors, loans, interest_payments)

**6 fases (12-16 semanas):**
1. Sitio público en Netlify (sem 1-3)
2. Auth + roles con Supabase (sem 3-5)
3. Portal Dealer (sem 5-8)
4. Portal Broker (sem 8-11)
5. Portal Investor (sem 11-13)
6. Go Live + DNS switch + cancelar Wix (sem 13-16)

**Ahorro:** ~$180-200/año vs Wix, más control de código y sin vendor lock-in

### Backup Strategy (Make.com + Google Drive)

**Doc de referencia:** `FF8_Airtable_Backup_Strategy.docx`

Airtable no tiene backups automáticos. Estrategia: 3 escenarios Make.com exportan tablas a JSON en Google Drive.

- **FlexFlow8 Daily** (3:00 AM EST): 11 tablas → `FF8_Backups/FlexFlow8_Daily/YYYY-MM-DD/`
- **Investors Weekly** (domingo): Investors, Loans, Interest_Payments
- **Field CRM Weekly** (domingo): Dealers, Brokers, Interactions
- Retención: 30 días rolling (~150-450 MB, dentro del free tier de Google Drive)
- Cada carpeta incluye `_manifest.json` con record counts por tabla
- Alertas por email: éxito/falla por ejecución + health check lunes 9 AM
- Script Python de restore listo (batch de 10 registros via Airtable API)

### Estado actual (Mar 2026)
- **En producción activa** — funding deals, cobranza, equipo de ventas en campo
- Portal legacy en Wix (flexflow8.com) operativo durante la migración
- **Git workflow:** `dev` branch para desarrollo, merge a `main` para producción
- **flexflow8-site:** Fase 1-5 completas + Admin Settings + Mobile Responsive + **Auth production fix** + **Portfolio Upload Automation** (con cleanup de cuentas cerradas) + **Security hardening** + **SEO audit** — sitio público (7 páginas + SEO con noindex login + absolute canonical + JSON-LD email fix + Lottie + OG image) + Supabase Auth (magic link + roles + portal routing, **client-side callback for Netlify**, `/api/auth/me` para role fetching) + Dealer Portal (4 tabs, Dashboard con **sortable drill-down columns** + **conditional columns** (ID Verification solo Pending Client Signatures, Expected Funding Date solo Pending Funding) + **Dealer column admin-only** + **UPPERCASE customer names** + **timezone-safe dates**, Portfolio con **Frequency column** desde Airtable, Buybacks con expandable BuybackTimeline, VERIFF filter, compact promise columns) + Broker Portal (5 tabs: Accounts dashboard con **VERIFF badges en drill-down** / Commissions + CSV export / Dealers / CRM con GPS Map links + "New CRM Entry" Fillout button / Pending Buybacks con expandable BuybackTimeline + badge; Activity Map admin-only visits-only con Leaflet heatmap+markers — todo UPPERCASE) + Investor Portal (3 tabs: My Investment / Active Loans con expandable payments / Payment History con filters + CSV export — read-only, Airtable FF8 Investors base, **case-insensitive email matching**) + Admin Portal (Dealer View con portfolio fix + **Dealer name en drill-down** | Broker View | Investor View | Settings con User Management CRUD + Activity Log + **role filter pills + sortable columns**) + **Mobile dark mode portals** (dealer 4 tabs con frequency en cards / broker 5 tabs / investor 3 tabs, CSS bars chart, MobileShell con favicon logo + LogOut icon, TimeSlicer, admin "Desktop Required") en Netlify
- **Producción Netlify:** Login funcional con magic link en `incandescent-figolla-de25fc.netlify.app`. Requiere env vars configuradas en Netlify Dashboard (AIRTABLE_PAT, AIRTABLE_BASE_ID, AIRTABLE_DEALERS_TABLE, AIRTABLE_APPLICANTS_TABLE, AIRTABLE_BROKERS_TABLE, AIRTABLE_INVESTORS_BASE_ID, AIRTABLE_INVESTORS_TABLE, AIRTABLE_LOANS_TABLE, AIRTABLE_PAYMENTS_TABLE, AIRTABLE_CRM_INTERACTIONS_TABLE, AIRTABLE_CRM_DEALERS_TABLE, SUPABASE_SERVICE_ROLE_KEY, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, PORTFOLIO_UPLOAD_KEY, COLLECTIONS_INGEST_KEY, ANTHROPIC_API_KEY)
- **Service role client:** Shared `createServiceClient()` en `lib/supabase/server.ts` — todas las lecturas de `public.users` usan service role (bypassa RLS). Todos los Airtable table IDs en env vars (sin hardcoded `tbl...`)
- **Portfolio Upload Automation (Make.com → Netlify Function):** Escenario Make.com "Portfolio Report → Supabase (New Portal)" recibe email con XLSX adjunto → sube a Google Drive → descarga bytes → POST a Netlify Function `/api/portfolio/upload` con binary body. Function (`netlify/functions/portfolio-upload.js`) parsea XLSX (row 3 = headers, row 4+ = data), mapea columnas → **delete stale accounts per portfolio** (solo los portfolios del reporte, no toca los demás) → upsert Supabase `portfolio_data`. Auth: `x-api-key` header validado contra `PORTFOLIO_UPLOAD_KEY` env var. Redirect en `netlify.toml`: `/api/portfolio/upload` → `/.netlify/functions/portfolio-upload`
- Timestamp Camera Enterprise + Fillout funcionando para verificación de campo
- Make.com automatizaciones operativas (incluye Portfolio Upload automation)
- **Automatrix (AMX) — SQL Collection KPIs (Mar 2026):**
  - 15 SQL reportes de FF8 en producción (eficiencia diaria/mensual, payments detail/summary, portfolio snapshot, cohort performance, collections worklist, out for repo, etc.)
  - 5 SQL reportes de Get Financed analizados para adaptación (monthly collections, collections by queue, bracket movement semanal, behavioral efficiency, repo sold & buybacks)
  - **3 nuevos SQL adaptados de Get Financed para FF8** (documentados en `FF8_Bracket_Movement_Reports.md`):
    1. **Weekly Collections by Queue** — cobros semanales por queue (A-F / G-L+N / M-Z-N)
    2. **Bracket Snapshot** — distribución de morosidad por pagos atrasados (normalizado por frecuencia: Weekly=7d, Bi-Weekly=14d) en 4 cortes semanales
    3. **Bracket Movement** — migración entre brackets semana a semana (Improved/Same/Worsened), NET = leading indicator de efectividad de cobranza
  - Adaptaciones clave vs Get Financed: brackets por **número de pagos** (no días fijos), threshold proporcional al ciclo, queues FF8, solo BHPH (sin LHPH), excluye COMPANY LOANS
  - **Collections Master Report SQL v3.1** (`FF8_Collections_Master_Report.sql` + `FF8_Collections_Master_Report_Spec_v3.md`):
    - Reporte maestro unificado: 1 fila por cuenta por fecha de corte, **36 columnas** en 5 bloques (A-E)
    - Pipeline: AMX genera XLSX → email → Make mailhook → Claude AI analiza → API → Dashboard
    - Columnas clave: identification (7), loan characteristics (9), account status (10, incluye `recency` y balance split principal/interest), bracket & queue (4, con `bracket_previous` y `bracket_movement`), period collections (6, desglosadas principal/interest/fees + YTD)
    - **Fixes v3.1:** (1) `program_code` redondea FinanceAmount al tier real (PFA-1500/2000/2500/3000, BHPH-7000/10000), (2) filtro COMPANY LOANS con wildcard para doble espacio + `original_dealer_name` para CLOSED BUYBACKS, (3) balance separado en `current_principal_balance` + `current_interest_balance` (de GetAccountBalances), (4) APR hardcoded 30% (eliminado cálculo dinámico), (5) `dealer_code` = PortfolioId (único por dealer)
    - **CLOSED BUYBACKS resuelto:** `DealsTable.ServicingBranchId` → `BookLoadCatalogTable.BookLoadCatalogId` (WHERE `Category='servicingbranch'`) → `Description` = dealer original. Ej: cuenta 8001301 → ServicingBranchId=13 → "Doral Motors Inc DBA Carman"
    - **`GetAccountBalances` columnas reales:** AccountNumber, Principal, **Interest** (no InterestDue), AccruedInterest, SalesTax, LHPHSalesTax, CPI, CPIPayoff, SideNote, DeferredDown, NSF, MiscFee, LateFee, LastPaymentDate
    - **`recency`** (col 26): días desde último pago recibido. Diferente a DPD (deuda vencida vs actividad). Umbrales: <14d/28d=activo, 35+=alerta, 60-70+=zona DIN
    - Queue asignada por **apellido** (no nombre), brackets con **grace period de 4 días**
  - **Pendiente adaptación:** Behavioral Efficiency (tendencia de pago individual) y Repo Sold & Buybacks (charge-off analysis)
- **Collections Module (Phase 1-4 implementado, Mar 2026):**
  - **Supabase tables:** `daily_snapshots` (Active, ~243 rows/day), `ofr_snapshots` (OFR, weekly), `ai_analysis` (pre-computed KPIs + Claude narrative), `chat_history` (admin chat)
  - **Users table:** Added `collections_role` (admin/supervisor/collector) + `collections_queue` (A-F / G-L(+N) / M-Z(-N))
  - **RLS:** Admin=all, supervisor=daily_snapshots+ai_analysis, collector=own queue only
  - **Netlify Functions:** `collections-upload.js` (xlsx binary → parse → segment → upsert), `collections-analyze.js` (pre-compute KPIs in JS → save → Claude narrative), `collections-chat.js` (role-based AI assistant)
  - **Dashboard:** 3 role-based views — Admin (full KPIs, tabs, queue filter, drill-down, OFR, AI narrative), Supervisor (no financials), Collector (own queue only). Chat FAB on all views
  - **Architecture:** KPIs pre-computed server-side in JavaScript (no Claude dependency for dashboard). Claude only generates 4-6 bullet narrative lines (~500 char input, 512 max_tokens). Dashboard works even if Claude fails
  - **6 Charts (Chart.js):** % Current Trend (line), Collections Trend (bars), Bracket + Payment Cycle Donut (side by side), Recency Heatmap (horizontal bars), Queue Comparison (vertical bars, identity colors), Dealer Scatter (bubbles). History API: `/api/collections/history`
  - **Mobile dark theme:** `position: fixed` dark container (#0B1929 bg, #12233A cards), 12px content padding, Home nav button, all components receive `dark` prop
  - **Dealer Mobile Light:** 4-tab dark theme (Dashboard with admin dealer selector, Portfolio with sort controls, Buybacks with totals card, Resources). Admin sees dealer dropdown filter
  - **Admin mobile home:** Nav cards (Collections, Dealer Portal, Settings with user CRUD, Logout) replacing "Desktop Required" dead-end
  - **ff8_team role:** New user role for FF8 team members. Redirects to `/portal/collections`. Sidebar shows Collections link. Auth callback + login page handle redirect correctly
  - **Chat limits:** Daily message limits by role (admin=50, supervisor=30, collector=20). Topic restriction (collections-only questions)
  - **Alert drill-down:** Clickable recency/new-behind alerts expand to filtered account lists. API supports `recency_gte` and `new_behind` filters
  - **Collector priority system:** Priority scoring (recency zones + bracket deterioration + payment amount), "START HERE" top 10 with reason tags, collapsible Strategy Guide, performance card (recovery rate, improved/worsened counts)
  - **Supervisor view toggle:** "SUPERVISOR VIEW" | "MY QUEUE: A-F" pill toggle. Switches between overview and CollectorDashboard with supervisor's assigned queue
  - **TimeSlicer on all views:** Admin, Supervisor, and Collector dashboards all have Today/Yesterday/Pick/Range date selection
  - **AI Insights popup:** Narrative moved from bottom to on-demand modal (Sparkles button + "AI INSIGHTS" label, red dot for HIGH alerts)
  - **Collections KPI card redesign:** "YESTERDAY'S COLLECTIONS (MAR 31)" label, progress bar vs daily_target (computed from current accounts × scheduled_payment / cycle_days), 7-day average, OFR subtotal (admin only)
  - **Bracket cycle filter:** ALL | BW | W | M pills above bracket bar. `brackets_by_cycle` pre-computed in analyze endpoint
  - **OFR period NET:** `ofr_period_net` added to portfolio_summary. Admin KPI shows Active + OFR = TOTAL
  - **Favicon:** `icons: { icon: "/icon.png" }` in root layout metadata — works for all roles
  - **Env vars:** `COLLECTIONS_INGEST_KEY`, `ANTHROPIC_API_KEY`
  - **Redirects:** `/api/collections/upload` → `collections-upload`, `/api/collections/analyze` → `collections-analyze`, `/api/collections/chat` → `collections-chat`
- **Urgente:** Rotar API key de Airtable hardcodeada en Wix antes de migración
- **Pendiente:** Implementar backup strategy (Make.com + Google Drive)
- **Pendiente:** Automatización OCR de videos (necesaria cuando >10 reps activos)
- **Pendiente:** Escalamiento a 120+ cuentas/mes requiere más capital

---

## Archivos sin trackear en git (intencionales)

| Archivo | Descripción |
|---------|-------------|
| `.agents/` | Archivos internos de Claude Code |
| `docx_content.txt` | Contenido extraído de un .docx |
| `read_docx.py` | Script para leer archivos .docx |
| `reporte_usuario.md` | Reporte de usuario |
| `tasks.md` | Lista de tareas |
| `projects/FF8/` | Proyecto FF8 (sin commitear aún) |

---

*Última actualización: 9 Abr 2026 — SAM: Mini sheet redesign (spell slots dots + gold display), character sheet mobile polish (combat 2×2 vitals, HP alignment, spells responsive columns + sorting, bio/gear stacked, sidebar X overlap fix). FF8: Collections Module complete.*
