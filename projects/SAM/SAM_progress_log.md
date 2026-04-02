# Registro de Progreso: S.A.M. (Storytelling AI Master)

Bitácora del estado actual del proyecto. Se actualiza con cada sesión de desarrollo.

---

## 1. Visión General

S.A.M. es una aplicación web que actúa como Dungeon Master virtual impulsado por IA para D&D 5e. Personalidad propia (sarcástica, humor oscuro), mecánicas reales (dados, daño, loot, inventario), y soporte para campañas con RAG sobre módulos PDF.

## 2. Arquitectura

| Capa | Tech | Hosting |
|------|------|---------|
| Frontend | Next.js 16 + TypeScript + shadcn/Radix + Tailwind v4 | Vercel |
| Backend | FastAPI (Python 3) | Render |
| Base de datos | Supabase PostgreSQL + pgvector | Supabase Cloud |
| LLM | Google Gemini Flash (via LangChain) | Google Cloud |
| Embeddings | gemini-embedding-001 (768 dims) via native `genai.embed_content()` SDK | Google Cloud |
| Auth | Supabase JWT + RLS | Supabase |

## 3. Historial de Cambios

### Sesión 04 Mar 2026

**Deploys corregidos:**
- Render: Root Directory corregido a `projects/SAM/backend`. Backend live en `https://sam-backend-mg0j.onrender.com`
- Vercel: Root Directory necesita `projects/SAM/frontend` (pendiente configuración manual)

**Bug Fixes implementados:**
1. **DiceTray identifica jugador** — `characterName` prop se pasa por la cadena `game-layout → sidebar-right → dice-tray`. Los mensajes de dados ahora dicen quién tiró. (commit `f44fbf1`)
2. **/reset borra todos los mensajes** — Estrategia 3-pass en `admin.py`: por campaign_id → huérfanos NULL → nuclear fallback. (commit `f44fbf1`)
3. **Dados via backend** — DiceTray ahora usa `authenticatedFetch("/api/roll")` con `secrets.randbelow()` (criptográficamente seguro). Fallback a `Math.random()` si el backend no responde. (commit `ee77f5b`)
4. **Parser LOOT resiliente** — `repairJson()` para JSON truncado, fallback para `</LOOT>` huérfanos, filtro de ghost items sin campo `item`. (commit `45b87c3`)
5. **Tags invisibles en chat** — `stripSystemTags()` elimina `<LOOT>`, `<UPDATE>`, `<XP_GAIN>`, `<ACTION>`, `<EVENT>`, `<IMAGE>` del texto visible. Se aplica en carga de historial y como safety net en render. `<DM_ROLL>` se preserva (tiene su propio renderer visual). (commit `45b9aa7`)
6. **System prompt reforzado** — Reglas TAG INTEGRITY para LOOT: ambos tags obligatorios, una sola línea, JSON completo, campo `item` obligatorio, formato Combined como ejemplo. (commit `45b87c3`)

**Playtest realizado:**
- Sesión completa single-player funcional: narrativa, combate, dados, loot, XP
- SAM procesa correctamente: `<UPDATE>`, `<LOOT>`, `<XP_GAIN>`, `<DM_ROLL>`
- Loot se acumula en inventario (15+ items en sesión de prueba)
- Problema detectado: Gemini ocasionalmente genera tags malformados → solucionado con parser resiliente

### Commits en main (04 Mar 2026)
```
45b9aa7 Fix: Strip machine tags from displayed messages
45b87c3 Fix: Resilient LOOT parser + stricter tag formatting
ee77f5b Feat: DiceTray rolls via backend (secrets.randbelow)
f44fbf1 Fix: DiceTray identifies character + /reset wipes all messages
a0b4ff6 Docs: Add SAM progress log and proposal
faa3ea1 Fix: Ultimate Deep Clean Reset
3599119 Docs: Add README.md
f9a4a9a Initial commit
```

### Sesión 18 Mar 2026

**Features implementados:**
1. **Upload módulos PDF de campaña** — Nuevo componente `campaign-module-upload.tsx`: dialog con drag/drop, validación tipo/tamaño, 4 estados (idle/uploading/success/error), muestra chunk count al completar. Botón "Cargar modulo PDF" en sidebar izquierdo, solo visible para el GM. (commit `513ef5c`)

**Bug Fixes implementados:**
1. **GM-only upload** — Upload restringido al GM de la campaña. Implementado via `isGM` state en `game-layout.tsx` que verifica propiedad de campaña. (commit `757450e`)
2. **GM check via backend API** — Query directa a Supabase fallaba por RLS. Cambiado a `authenticatedFetch('/api/campaigns/{id}')` que usa service role key en backend. (commit `c7f38cf`)
3. **isGM prop faltante en desktop** — El prop `isGM` solo se pasaba al sidebar mobile, no al desktop. Botón nunca aparecía en pantalla completa. Agregado `isGM={isGM}` al SidebarLeft de desktop. (commit `c3e9102`)
4. **Modelo de embeddings obsoleto** — `ingestion.py` usaba `text-embedding-004` (removido por Google). Actualizado a `gemini-embedding-001`. (commit `77311c1`)
5. **Dimensiones de embeddings** — `gemini-embedding-001` genera 3072 dims por defecto pero la BD usa `vector(768)`. Agregado `output_dimensionality=768` en `ai.py` (RAG queries) e `ingestion.py` (vectorización de PDFs). (commit `0d14f2b`)
6. **Código duplicado en characters.py** — Bloque duplicado de `load_dotenv()`, router, y Supabase client eliminado. (commit `757450e`)

**Debugging realizado:**
- Console logging (`🔑 GM Check:`) agregado al `checkGM` effect para diagnosticar problemas de visibilidad del botón de upload en producción

### Commits en main (18 Mar 2026)
```
0d14f2b Fix: Set output_dimensionality=768 for gemini-embedding-001
77311c1 Fix: Update embedding model in ingestion service to gemini-embedding-001
c3e9102 Fix: Pass isGM prop to desktop sidebar (was only on mobile)
c7f38cf Fix: GM check via backend API instead of direct Supabase query
757450e Fix: PDF upload GM-only + clean duplicate code in characters.py
513ef5c Feat: Campaign module PDF upload + update project docs
```

### Sesión 18 Mar 2026 (cont.) — Refactor Embeddings + Análisis Multiplayer

**Refactorización mayor: LangChain embeddings → SDK nativo de Google**

Descubrimiento: `langchain-google-genai==2.0.10` ignora silenciosamente el parámetro `output_dimensionality`, siempre retorna 3072 dims aunque se pida 768. Esto causaba error `expected 768 dimensions, not 3072` al insertar en Supabase.

**Solución:** Reemplazar `GoogleGenerativeAIEmbeddings` con `genai.embed_content()` (SDK nativo) en todo el código runtime:

1. **`ingestion.py`** — Refactorizado de `SupabaseVectorStore.from_documents()` a `genai.embed_content()` + `supabase.table("documents").insert()` directo. Batch processing de 100 chunks.
2. **`ai.py`** — RAG query ahora usa `genai.embed_content()` con `task_type="retrieval_query"` en vez de `embeddings.embed_query()`.
3. **`compendium_tools.py`** — Reemplazado `GoogleGenerativeAIEmbeddings(model="text-embedding-004")` con `genai.embed_content(model="gemini-embedding-001")`. Las 3 funciones (search_spells/monsters/items) actualizadas.

**Dependencias:**
- `langchain-openai` eliminado (no se usaba)
- `google-generativeai>=0.8,<0.9` pinneado (compatible con `langchain-google-genai==2.0.10`)
- `langchain-google-genai` se mantiene para `ChatGoogleGenerativeAI` (LLM, no embeddings)

**Nota:** Scripts en `app/scripts/` (seeders) aún usan el modelo viejo — no son runtime, se actualizarán cuando se re-seedee el compendio.

**Análisis multiplayer completado** — Se identificaron 7 gaps críticos (ver sección 5).

### Commits en main (18 Mar 2026, cont.)
```
8654092 Refactor: Replace LangChain embeddings with native Google SDK (768d) in ingestion, AI, and compendium tools
7b57fd9 Fix: Pin LangChain + Google AI dependencies to compatible versions
a7cd70d Fix: Pin LangChain dependencies + remove unused langchain-openai
```

### Sesión 18 Mar 2026 (cont.) — Multiplayer MVP Frontend

**Implementación: Filtrado por campaña y propagación de campaignId**

1. **`game-layout.tsx`** — `campaignId` derivado de `selectedCharacter.campaign_id`. `campaignName` obtenido del API (`/api/campaigns/{id}`), reutilizando el fetch existente del GM check. Ambos propagados como props a `ChatInterface`, `CharacterCreateDialog`, y `Commlink` (via `SidebarLeft`).

2. **`chat-interface.tsx`** — Nuevos props: `campaignId`, `campaignName`.
   - `fetchHistory()` ahora filtra con `.eq('campaign_id', campaignId)`. Si no hay campaignId, muestra "Select a character to begin your adventure."
   - `useRealtime` filtrado: `filter: 'campaign_id=eq.{campaignId}'`, `enabled: !!campaignId`. Solo escucha mensajes de la campaña activa.
   - Re-fetch automático al cambiar de campaña (limpia mensajes + carga nuevos).
   - Header dinámico: muestra `Campaign: {name}` o "S.A.M." si no hay campaña.

3. **`commlink-dialog.tsx`** — Recibe `campaignId` como prop. `"FIXME_CAMPAIGN_ID"` reemplazado con el prop real.

4. **`character-create-dialog.tsx`** — Recibe `campaignId` como prop. UUID hardcodeado reemplazado (mantiene fallback al UUID de Solo Adventure si no hay campaña activa). Botón "Create Character" deshabilitado si no hay campaignId, muestra "Select a Campaign First".

5. **`sidebar-left.tsx`** — Pasa `campaignId` al componente `Commlink`.

### Commits en main (18 Mar 2026, cont.)
```
4b4c318 Feat: Multiplayer MVP — filter messages by campaign, dynamic header, fix commlink and character creation
```

### Sesión 19 Mar 2026

**Features implementados:**
1. **Multiplayer MVP** — Mensajes filtrados por `campaign_id` en `fetchHistory()` y Realtime. Header dinámico con nombre de campaña real. Selector de campañas en dialog de crear personaje (fetch desde `GET /api/campaigns/`). Commlink usa `campaignId` real. Character creation usa campaña activa.
2. **Atribución de mensajes multiplayer** — `sender_id` populado en backend al insertar mensajes del usuario (extraído del JWT). Mensajes propios a la derecha, otros jugadores a la izquierda con burbuja azul y nombre del personaje, SAM (`sender_id === null`) a la izquierda con estilo original.
3. **PDF upload end-to-end** — Fix schema `documents.id` de `bigint` a `uuid`. Refactor embeddings a SDK nativo de Google (`genai.embed_content()` con `output_dimensionality=768`). Pipeline completo: PDF → chunks → embeddings 768d → Supabase → RAG → SAM responde con contexto del módulo.
4. **Dependencias pineadas** — `langchain==0.3.25`, `langchain-community==0.3.21`, `langchain-google-genai==2.0.10`, `google-generativeai>=0.8,<0.9`. Eliminada `langchain-openai` (no usada).

**Bug Fixes implementados:**
1. **Schema `documents.id`** — Cambiado de `bigint` a `uuid` en Supabase (fix del error `Invalid input syntax for type bigint`).
2. **Embeddings 3072→768** — `GoogleGenerativeAIEmbeddings` de LangChain 2.0.10 ignora `output_dimensionality`. Reemplazado con SDK nativo en `ingestion.py`, `ai.py`, y `compendium_tools.py`.
3. **Perfil faltante para usuarios nuevos** — FK violation al crear personaje. Fix manual en Supabase (`INSERT profiles`). Pendiente: auto-creación de perfil.
4. **Deduplicación de mensajes** — Refactorizada para usar `id` de BD en vez de comparar contenido del último mensaje. Mensajes optimistic (sin `id`) se reemplazan cuando llega el INSERT de Realtime con el mismo `content` y `sender_id`. Mensajes de otros jugadores/SAM se verifican por `id` antes de agregar.

**Playtest multiplayer realizado:**
- 2 jugadores (Baol Gortsh + Fekas) en misma campaña "Solo Adventure"
- Mensajes se ven en ambas pantallas con atribución correcta
- SAM responde a ambos jugadores en contexto
- Dados funcionan desde ambas cuentas
- Bug pendiente: mensajes duplicados intermitentes en pantalla del sender

**Bugs conocidos (resueltos sesión 25 Mar):**
- ~~Error intermitente `thought_signature` de Gemini API~~ — ✅ Resuelto: SDK migrado a `google-genai` + `langchain-google-genai==2.1.12` + fallback sin tools
- ~~Mensajes duplicados en pantalla del sender~~ — ✅ Resuelto: eliminado optimistic update, mensajes solo via Realtime
- Auto-creación de perfil para usuarios nuevos — pendiente (trigger en Supabase o endpoint)

### Commits en main (19 Mar 2026)
```
4da41c7 Fix: Robust message deduplication using DB ids — fixes duplicate messages in multiplayer
09c7f66 Feat: Multiplayer message attribution — sender_id, character names, distinct player bubbles
4211de3 Feat: Campaign selector in character creation dialog for multiplayer join
```

### Sesión 24 Mar 2026 — Multiplayer Polish, Roster, Dedup, Admin Commands

**Features implementados:**
1. **Party roster** — Nuevo componente `party-roster.tsx` en sidebar izquierdo. Muestra otros personajes de la campaña con avatar, nombre, clase, nivel, y HP coloreado (verde/amarillo/rojo). Nuevo endpoint `GET /api/characters/campaign/{campaign_id}`. Filtra personajes propios del usuario.
2. **Multiplayer player attribution en AI** — Historial enviado a Gemini ahora incluye `sender_name` por mensaje. System prompt con `MULTIPLAYER PROTOCOL`: SAM distingue jugadores por `[CharacterName]`, narra para cada uno individualmente, nunca controla personajes ajenos. Historial expandido de 5 a 10 mensajes.
3. **Admin commands GM-only** — `/reset`, `/checkpoint`, `/load`, `/list` restringidos al GM en frontend (`isGM` prop en `ChatInterface`). Jugadores ven toast "Only the GM can use admin commands".
4. **Reset broadcast** — `/reset` ahora inserta un system message con `<ACTION>CLEAR_CHAT</ACTION>` en la BD después de borrar mensajes, sincronizando todos los clientes via Realtime INSERT (los DELETE events de Supabase no llegan sin `REPLICA IDENTITY FULL`).

**Bug Fixes:**
1. **Mensajes duplicados eliminados** — Removido optimistic update completamente. Mensajes llegan exclusivamente via Realtime. Deduplicación por `id` de BD como safety net.
2. **Roster `currentUserId` timing** — `currentUserId` se obtiene en `useEffect([], [])` al montar `game-layout.tsx` (independiente de `campaignId`). Guard `!currentUserId` en roster evita fetch sin token.
3. **Route ordering** — Endpoint `/campaign/{campaign_id}` movido antes de `/{character_id}` en `characters.py`. FastAPI matcheaba `/campaign/xxx` como `character_id="campaign"` → 500.

### Commits en main (24 Mar 2026)
```
4f783c8 Fix: Route ordering — campaign endpoint before generic character_id param
f90688c Fix: Party roster currentUserId timing + auth guard for campaign characters fetch
6dd9e59 Fix: Reset broadcasts to all clients + roster filter diagnostic
466f7ef Feat: Party roster — show other players' characters in sidebar with HP status
1658188 Feat: Multiplayer player attribution — SAM now distinguishes and addresses each player individually
45067b1 Fix: Remove optimistic update to prevent duplicate messages + restrict admin commands to GM only
b1eb562 Docs: Update progress log — multiplayer MVP, PDF upload, session 19 Mar 2026
```

### Sesión 25 Mar 2026 — SDK Migration, Attribution Fix, Gemini Resilience

**Refactor mayor: google-generativeai (legacy) → google-genai (new SDK)**

El SDK legacy `google-generativeai` tenía un conflicto de dependencias con `langchain-google-genai>=2.1` (ambos pineaban `google-ai-generativelanguage` a versiones incompatibles). Migración completa a `google-genai` (el SDK nuevo de Google):

1. **`ai.py`** — `genai.configure()` → `genai.Client()`. `genai.embed_content()` → `client.models.embed_content()`. `genai.GenerativeModel().generate_content()` → `client.models.generate_content()` con `types.Part.from_bytes()` para PDF multimodal. Modelo PDF actualizado a `gemini-2.5-flash`.
2. **`ingestion.py`** — Misma migración de embeddings. Batch results: `[e.values for e in response.embeddings]`.
3. **`compendium_tools.py`** — Misma migración. `response.embeddings[0].values`.

**Dependencias actualizadas:**
- `langchain-google-genai` 2.0.10 → **2.1.12** (soporta `thought_signature`)
- `google-generativeai>=0.8,<0.9` → **`google-genai`** (nuevo SDK)
- `google-generativeai` eliminado completamente

**Bug Fixes:**
1. **Mensaje actual sin atribución** — `generate_response()` ahora recibe `sender_name` y prefixea el mensaje actual: `[CharacterName]: message`. Antes solo el historial tenía prefix.
2. **Fallback `thought_signature`** — Si Gemini falla con `thought_signature` o `functionCall` al usar tools, reintenta sin tools con historial limpio (sin `ToolMessage` ni `AIMessage` con tool calls). Cubre tanto la invocación inicial como el tool loop.
3. **Inyección de tool results en fallback** — Cuando los tools se ejecutan exitosamente (ej: `apply_damage` genera `<UPDATE>` tag) pero Gemini falla al reinvocar, los tool results capturados se inyectan en el response del fallback. Esto preserva los tags `<UPDATE>`/`<LOOT>` para que el frontend los procese.
4. **Campos de status duplicados (hp vs hp_current, wallet vs money)** — El PDF import generaba `hp` y `wallet`, pero el game loop usa `hp_current` y `money`. Fix: post-procesamiento en `parse_character_pdf()` normaliza campos. Migration script ejecutado para personajes existentes (Baol Gortsh + fekas). Frontend con fallback `hp_current ?? hp` como safety net.
5. **Ghost items en inventario** — Items sin campo `item` eliminados por migration script (1 ghost item removido de Baol).
6. **System prompt HP UPDATES** — Tools ahora "preferred" en vez de "mandatory". Ejemplo explícito de formato `<UPDATE>` tag. SAM instruido a generar tags inline cuando tools fallan.

### Commits en main (25 Mar 2026)
```
de895a9 fix: inject captured tool results into fallback response to preserve UPDATE/LOOT tags
039d20e fix: normalize status field names (hp→hp_current, wallet→money) + migration script
9895d70 fix: reinforce UPDATE tag format in system prompt with explicit example
9110278 fix: fallback tool execution via inline XML tags in system prompt
26d2e29 Fix: Clean tool-related messages from history before no-tools fallback
6b7d256 Fix: Fallback to no-tools response when Gemini thought_signature error occurs
407f1cf Refactor: Migrate from google-generativeai (legacy) to google-genai (new SDK) + upgrade langchain-google-genai to 2.1.12
48ed864 Fix: Prefix current user message with character name for multiplayer attribution
cad16de Docs: Update progress log — multiplayer polish, roster, dedup, admin commands
ddcc42c Docs: Update progress log — SDK migration, attribution fix, Gemini resilience (25 Mar 2026)
0892873 Docs: Update progress log — inline XML fallback, session 25 Mar 2026
```

### Sesión 26 Mar 2026 — Combat System, Context-Aware Prompting, LangChain 1.x Upgrade, Mobile Responsive

**Upgrade mayor: LangChain 0.3.x → 1.x**
- `langchain` 0.3.25 → **1.2.13**, `langchain-core` → **1.2.22**, `langchain-google-genai` 2.1.12 → **3.2.0**, `langchain-community` 0.3.21 → **0.4.1**
- Nuevo: `langchain-text-splitters==1.1.1`
- Modelo pineado a `gemini-2.5-flash` (reemplaza `gemini-2.0-flash` deprecated y `gemini-flash-latest` alias dinámico)
- `langchain-google-genai 3.2.0` soporta `thought_signature` nativamente para Gemini 2.5/3.x

**Features implementados:**
1. **Context-aware prompting** — AI history ahora se lee de la BD (últimos 20 mensajes por campaign_id) en vez del frontend. SAM siempre ve mensajes de todos los jugadores sin importar timing de Realtime.
2. **Campaign lock** — `asyncio.Lock` por campaign_id serializa respuestas de SAM. Si dos jugadores envían mensajes simultáneamente, el segundo espera a que SAM termine de responder al primero.
3. **Combat turn tracking** — Nuevo tag `<COMBAT>` en system prompt. SAM emite initiative order, turno actual, ronda. Backend parsea el tag y actualiza `campaigns.settings.combat`. Frontend escucha via Realtime.
4. **Combat UI** — Banner de initiative order (rojo) encima del chat con turno actual resaltado. Input bloqueado cuando no es tu turno. NPCs no bloquean (SAM resuelve automáticamente).
5. **Typing indicator** — Supabase Broadcast channel `typing:{campaignId}`. Throttle 2s, stale cleanup 4s. "`Baol Gortsh is typing...`" aparece para otros jugadores.
6. **System prompt reforzado** — Combat rules: SAM tira TODOS los dados de NPCs con `<DM_ROLL>` transparente + `apply_damage` inmediato. Críticos (nat 20 = dados dobles). Advantage/disadvantage parsing de SYSTEM EVENTs. HP updates ahora MANDATORY tool use (no preferred).
7. **Character sheet responsive** — Tabs scrollables en mobile, grids adaptativos (3 cols → 6 cols), tablas con scroll horizontal, padding compacto.
8. **stripSystemTags expandido** — Limpia `Calculation:` lines, tool call text, failed search results, `<COMBAT>` tags del chat visible.

**Bug Fixes:**
1. **Duplicate message in DB history** — Fetch de BD incluía el mensaje actual del sender (ya insertado). Fix: excluir último mensaje si coincide con request.message.
2. **`/reset` no limpiaba combat** — Agregado clear de `campaigns.settings` a `{}` en el reset.
3. **`gemini-2.0-flash` deprecated** — Cambiado a `gemini-2.5-flash`.

### Commits en main (26 Mar 2026)
```
0389543 fix: make character sheet dialog responsive for mobile
1c4d96e fix: /reset now clears combat state from campaign settings
aa73ee0 feat: combat turn lock — frontend initiative banner, input blocking, realtime sync
776d7af feat: combat turn tracking — COMBAT tag parsing, campaign settings update, system prompt instructions
42ddca0 fix: add critical hit rules, advantage/disadvantage parsing, NPC damage transparency
3217903 fix: reinforce system prompt — mandatory apply_damage, DM rolls own NPC dice
8e6517e feat: add campaign lock for response consolidation + fix duplicate message in history
899dd1e feat: switch AI history from frontend to DB-sourced for context-aware prompting
e89c8d7 feat: add typing indicator via Supabase Broadcast
651dae5 fix: expand stripSystemTags to clean Calculation lines, tool call text
7c02b81 fix: switch model to gemini-2.5-flash (2.0-flash deprecated)
39697b9 chore: upgrade langchain stack to 1.x + langchain-google-genai 3.2.0
f3b730f fix: conditional tool result injection (only on fallback) + first invocation logging
692810c Docs: Update progress log — tool result injection, status normalization, Gemini resilience
```

### Sesión 31 Mar 2026 — Admin Panel, Invitations, Presence, Identity Fix

**Features implementados:**
1. **Admin panel completo** — Rediseño total de `/admin`. Campaign manager (crear/activar/desactivar/eliminar campañas con player count). Gestión de invitaciones (generar códigos, listar, desactivar). User management (tabla con role/status, toggle admin/player, activate/deactivate, activity log, role filter pills, sortable columns). Campaign controls (reset, save/load checkpoints, clear combat). SAM Neural Tuner conectado al AI (difficulty/creativity/lethality afectan system prompt dinámicamente). Módulos PDF unificados en la card de campañas.
2. **Sistema de invitaciones** — Backend: 5 endpoints (`POST /api/invitations`, `GET /api/invitations`, `DELETE /api/invitations/{id}`, `POST /api/invitations/validate`, `POST /api/invitations/register`). Códigos de 6 caracteres alfanuméricos. Validación de max_uses y expiración. Registro con código crea usuario Supabase Auth + auto-profile via trigger.
3. **Signup page** — `/signup` con validación de código de invitación en 2 pasos. Login con email/password además de Google OAuth.
4. **Player presence** — Supabase Presence API (`channel.track()`) muestra punto verde/gris al lado de cada personaje en el party roster. Auto-absent a los ~10s de cerrar tab.
5. **Tab notifications** — Título dinámico con unread count (`(3) ⚔️ S.A.M. — New activity!`). Sonido de notificación (Web Audio API, beep D5). Alerta especial de turno en combate (`🎯 YOUR TURN!`).
6. **Visibility resync** — `visibilitychange` + `online` listeners refetchean mensajes, personaje, y campaign data al volver de background. Throttle 5s anti-spam.

**Bug Fixes críticos:**
1. **🔴 Shadow variable `sender_name`** — En `ai.py`, la variable del loop de historial sobrescribía el parámetro `sender_name` de `generate_response()`. Si el último mensaje del historial era de SAM, el mensaje actual del jugador se enviaba a Gemini como `[S.A.M.]: texto` en vez de `[Baol Gortsh]: texto`. Fix: renombrado a `msg_sender` dentro del loop.
2. **Identity rule reescrita** — System prompt ahora explica que los prefixes `[CharacterName]:` son automáticos del sistema. SAM instruido a nunca pedir a jugadores que se identifiquen. 6 reglas absolutas numeradas. Stripping de `[SYSTEM EVENT]` echoes en frontend.
3. **`stripSystemTags` expandido** — Limpia `[SYSTEM EVENT]` echoes, `Calculation:` lines, tool call text, failed search results.

**Infraestructura:**
1. **Schema migration 006** — `profiles` con campos `status` (pending/approved/rejected) y `role` (admin/player). Tabla `invitations` (code, max_uses, expires_at, is_active). Trigger `handle_new_user` auto-crea perfil al registrarse. RLS para admin.
2. **Admin verification** — `verify_admin()` helper reutilizable. Endpoints admin verifican `role = 'admin'` en profiles.
3. **Delete campaigns/users** — Confirmación por nombre (type-to-confirm). Cascade: documents → messages → characters → campaign.

### Commits en main (27 Mar – 1 Abr 2026)
```
d567718 fix: critical shadow variable bug — player messages sent to Gemini as [S.A.M.]
a7832a9 fix: rewrite identity rules + add Gemini prompt debug logs + strip SYSTEM EVENT echoes
222cc72 fix: rewrite identity rule — clarify prefix is automatic
bc5657a debug: add presence tracking console logs for diagnosis
95b77dc fix: prevent SAM from prefixing responses with player name brackets
4db77ec feat: tab notifications — dynamic title, notification sound, turn alert
264477b feat: player presence tracking — online/offline indicator via Supabase Presence API
bc2ff64 fix: add critical identity rule to system prompt
efa24c0 debug: log history sent to SAM for player attribution diagnosis
aced2a2 feat: admin delete campaigns and users with confirmation dialogs
532b265 feat: merge campaign modules into campaign manager
a9f7fc4 feat: admin campaign manager — create, activate/deactivate, delete campaigns with player count
d884ced feat: connect SAM Neural Tuner to AI — campaign settings affect system prompt dynamically
ca710b7 feat: admin panel — player role/status management, campaign controls, layout reorganization
```

### Sesión 1 Abr 2026 — Multi-Agent Architecture Foundation

**Refactorización arquitectónica mayor: monolito → sistema multi-agente**

Análisis del pipeline existente en `ai.py` reveló que Gemini estaba haciendo aritmética de HP, generando JSON de loot, y emitiendo XML — tareas determinísticas que no necesitan LLM. Los dados de NPCs eran números inventados por Gemini, no `secrets.randbelow()`.

**Nuevo paquete `backend/agents/` — 8 módulos:**

1. **`dice.py`** — `DiceRoller` con `secrets.randbelow()`. Métodos: `roll(sides)`, `roll_multiple(count, sides)`, `roll_with_modifier(count, sides, modifier)`, `roll_advantage()`, `roll_disadvantage()`.

2. **`rules.py`** — Tablas y cálculos D&D 5e puro Python: `XP_THRESHOLDS` (niveles 1-20), `get_level_for_xp()`, `xp_to_next_level()`, `calculate_hp_change()`, `check_hit()`, `check_save()`.

3. **`combat_state.py`** — `CombatState`: máquina de estado de combate. `start_combat()` (rolls initiative de NPCs con dados reales), `advance_turn()`, `remove_combatant()`, `update_npc_hp()`, `end_combat()`. Serializable para `campaigns.settings.combat`.

4. **`mechanic.py`** — `MechanicEngine`: motor de juego Python puro. Cero LLM.
   - `process_spell()`: save de NPC (dados reales) o pending roll para spell attack
   - `process_attack()`: pending roll para el jugador
   - `process_player_roll()`: router para pending actions (weapon_attack/damage, spell_damage, spell_attack, skill_check)
   - `resolve_npc_turn()`: turno NPC completo con acumulación de daño multi-ataque → `calculate_hp_change()` una sola vez
   - `award_xp()`: split entre party, level-up check
   - `get_results_summary()`: texto plano de hechos para el narrador
   - `state_updates[]`: lista de mutaciones de BD listas para Supabase

5. **`interpreter.py`** — `IntentInterpreter`: LLM con prompt de 40 líneas.
   - SYSTEM EVENTs → regex puro (0 tokens): `{"type": "dice_roll", "result": 18, "rolls": [18]}`
   - Texto libre → JSON estructurado: `{"type": "spell", "spell_name": "Sacred Flame", "target": "Guard 1"}`
   - 8 tipos de acción: spell, attack, skill_check, movement, roleplay, item, ability, free_action
   - Fallback a `{type: roleplay}` en error de JSON

6. **`narrator.py`** — `Narrator`: LLM creativo con prompt de 60 líneas. 13 reglas duras: sin XML, sin math, sin dados inventados.
   - `narrate_mechanics(facts)`: narra hechos pre-calculados del MechanicEngine
   - `narrate_roleplay()`: exploración y diálogo sin mecánicas
   - `narrate_scene()`: descripciones de ubicación

7. **`orchestrator.py`** — `SAMOrchestrator`: coordinador del pipeline completo.
   - `process_message()`: Interpreter → Mechanic → (RAG) → Narrator
   - Resolución automática de turnos NPC consecutivos (safety valve: 20 iteraciones)
   - Retorna `{narrative, state_updates, combat_state, prompt_player_roll}`

8. **`__init__.py`** — documentación del sistema

**Commits (1 Abr 2026):**
```
75693e1 feat: SAMOrchestrator — full pipeline coordinator connecting Interpreter → Mechanic → Narrator
fedfb7a feat: Narrator agent — LLM storyteller that narrates mechanical facts without touching game logic
619de53 feat: IntentInterpreter — LLM-powered action parser with structured JSON output
5231b73 feat: MechanicEngine — complete D&D 5e game engine for spells, attacks, NPC turns, XP, and skill checks
68d2226 feat: multi-agent foundation — DiceRoller, Rules engine, CombatState manager
```

**Estado:** Los 8 módulos están implementados y conectados a `server.py` con fallback a `ai.py`.

### Sesión 2 Abr 2026 — Orchestrator Integration + stripSystemTags Fix

**Integración del orquestador multi-agente en server.py:**
1. **`agents/knowledge.py`** — KnowledgeService que encapsula RAG existente. Usa `genai.Client.models.embed_content()` (768d) + RPCs `match_documents` y `match_compendium` de Supabase. Métodos: `search_campaign_context()`, `search_spell/monster/item()`, `search()`.
2. **Orchestrator conectado a `/api/chat`** — Pipeline: Interpreter (temp=0.1) → MechanicEngine → Knowledge → Narrator (temp=0.9). State updates (HP, XP) se aplican directamente a la BD sin depender de tags XML. Combat state se actualiza directamente.
3. **Legacy fallback** — Si el orquestador falla por cualquier razón, cae automáticamente a `SAMBrain.generate_response()` con todo el pipeline original (tools, COMBAT tags, etc.). `ai.py` no se borró ni modificó.
4. **Character context de BD** — `server.py` ahora fetcha el personaje real de la BD (`characters` table) en vez de parsear el string formateado del frontend. Resuelve `KeyError: 'name'` que causaba el crash del orquestador.

**Bug Fixes:**
1. **`character["name"]` → `character.get("name", "Unknown")`** — 7 instancias en `mechanic.py` convertidas a acceso defensivo.
2. **`stripSystemTags` solo para SAM** — La función ahora recibe `role` como parámetro. Gemini artifacts (`[SYSTEM EVENT]`, `Calculation:`, tool calls) solo se limpian de mensajes con `role === 'assistant'`. Los mensajes de jugadores (tiradas de dados) mantienen su contenido intacto.
3. **`renderMessageContent` con role** — La función de render pasaba todo por `stripSystemTags` sin role (default `'assistant'`), eliminando `[SYSTEM EVENT]` de las tiradas de dados de jugadores. Fix: se pasa `msg.role` al renderizar.

### Commits en main (2 Abr 2026)
```
87381e9 fix: pass role to renderMessageContent to prevent stripping SYSTEM EVENT from player dice rolls
8608fa2 fix: only strip SYSTEM EVENT text from SAM responses, not from player dice roll messages
0dce0e0 fix: defensive character_context access in mechanic + orchestrator — handle missing 'name' key
2ae8662 feat: integrate SAMOrchestrator into server.py — multi-agent pipeline replaces monolithic SAMBrain with legacy fallback
1bba20d docs: update CLAUDE.md and SAM_progress_log with multi-agent architecture session
75693e1 feat: SAMOrchestrator — full pipeline coordinator connecting Interpreter → Mechanic → Narrator
fedfb7a feat: Narrator agent — LLM storyteller that narrates mechanical facts without touching game logic
619de53 feat: IntentInterpreter — LLM-powered action parser with structured JSON output
5231b73 feat: MechanicEngine — complete D&D 5e game engine for spells, attacks, NPC turns, XP, and skill checks
68d2226 feat: multi-agent foundation — DiceRoller, Rules engine, CombatState manager
```

---

## 4. Estado Actual — Abril 2026

### Lo que funciona
- Login/auth via Supabase JWT + email/password + Google OAuth
- Crear/importar personajes (PDF via Gemini)
- Chat con SAM (narrativa + mecánicas)
- Dados (backend con `secrets.randbelow`, fallback client-side)
- Daño/curación via tools (`apply_damage`, `apply_healing`)
- Loot procesado y persistido en inventario (money + items)
- XP tracking y notificaciones
- DM rolls visualizados (chips morados)
- Compendio D&D 5e con búsqueda semántica (spells, monsters, items)
- RAG sobre módulos PDF de campaña
- Upload PDF de módulos de campaña (integrado en admin campaign manager)
- Checkpoints (save/load/reset/list)
- Mensajería privada (commlink) — usa campaignId real (UI prototipo, falta selector de destinatarios)
- Realtime sync via Supabase WebSocket (filtrado por campaña)
- **Multiplayer completo:** mensajes filtrados por campaign_id, header dinámico, atribución por `[CharacterName]` prefix
- **Shadow variable fix:** `sender_name` del loop de historial ya no sobrescribe el parámetro de `generate_response()`
- **Identity rule robusta:** System prompt con 6 reglas absolutas, SAM nunca confunde jugadores con DM
- **Selector de campaña:** dropdown en dialog de crear personaje
- **Deduplicación robusta:** sin optimistic update, mensajes solo via Realtime, dedup por id de BD
- **Party roster:** sidebar muestra otros personajes con HP status + indicador de presencia online/offline
- **Player presence:** Supabase Presence API con punto verde/gris en roster
- **Admin commands GM-only:** `/reset`, `/checkpoint`, `/load`, `/list` solo para GM
- **Admin panel completo:** Campaign manager, invitaciones, user management, SAM tuner, campaign controls
- **Sistema de invitaciones:** Registro por código de 6 chars. Signup page + backend endpoints
- **SAM Neural Tuner → AI:** Difficulty/creativity/lethality afectan system prompt dinámicamente
- **SDK migrado:** `google-genai` (nuevo SDK), `langchain-google-genai==3.2.0`, `langchain==1.2.13`
- **Gemini resilience (3 capas):** thought_signature support + fallback sin tools + tool results injection
- **Context-aware prompting:** AI history de BD (20 msgs). Campaign lock (`asyncio.Lock`) serializa respuestas.
- **Combat turn tracking:** `<COMBAT>` tag → initiative banner + input blocking por turno
- **Typing indicator:** Supabase Broadcast, throttle 2s
- **Tab notifications:** Unread count, sonido, alerta de turno
- **Visibility resync:** Re-fetch de mensajes/personaje/campaña al volver de background
- **Character sheet responsive:** Tabs scrollables, grids adaptativos, padding compacto mobile
- **stripSystemTags:** Limpia SYSTEM EVENT echoes, Calculation lines, tool calls, COMBAT tags — solo en mensajes de SAM (role-aware)
- **Multi-agent architecture:** `backend/agents/` con DiceRoller, Rules, CombatState, MechanicEngine, IntentInterpreter, Narrator, SAMOrchestrator + KnowledgeService. Conectado a `server.py` con fallback a `ai.py` legacy.

### Completitud: ~95% (app funcional) + arquitectura multi-agente integrada

### Pendiente para "done"
- Commlink: selector de destinatarios (usar party roster como lista)
- Generated scene placeholder (tag `<IMAGE>` sin servicio de imágenes conectado)
- Playtest completo con grupo de amigos
- Vercel Root Directory config
- Quitar console.logs de debug (presence tracking)

## 5. Análisis Multiplayer

### Infraestructura existente
- `messages` table tiene `campaign_id` FK (NOT NULL)
- Backend auto-detecta campaña via personaje del usuario o propiedad GM
- Supabase Realtime filtrado por `campaign_id` (cada jugador solo ve su campaña)
- RLS policies en todas las tablas
- `campaignId` propagado a todos los componentes que lo necesitan

### Gaps resueltos (sesión 18 Mar 2026)
| Gap | Fix | Commit |
|-----|-----|--------|
| Sin filtro de campaña en chat | `.eq('campaign_id', campaignId)` en fetchHistory + filter en useRealtime | `4b4c318` |
| Commlink hardcodeado | Recibe `campaignId` como prop | `4b4c318` |
| Character creation hardcodea UUID | Recibe `campaignId` como prop (fallback a Solo Adventure) | `4b4c318` |
| Header hardcodeado | Dinámico: `Campaign: {name}` desde API | `4b4c318` |
| Sin re-fetch al cambiar campaña | `useEffect` con `campaignId` dependency limpia + recarga | `4b4c318` |

### Gaps pendientes para multiplayer completo
| Gap | Detalle | Archivo |
|-----|---------|---------|
| ~~**Sin selector de campaña**~~ | ✅ Resuelto: dropdown en `character-create-dialog.tsx` | `4211de3` |
| ~~**Sin roster de jugadores**~~ | ✅ Resuelto: `party-roster.tsx` con endpoint `/campaign/{id}` | `466f7ef` |
| **Sin membership table** | No hay concepto formal de "jugadores en campaña" | schema |
| ~~**Sin presence indicators**~~ | ✅ Resuelto: Supabase Presence API + punto verde/gris en roster | `264477b` |
| **Commlink sin recipients** | No hay lista de jugadores para enviar mensajes | `commlink-dialog.tsx` |
| ~~**Campaign join/invite**~~ | ✅ Resuelto: sistema de invitaciones por código | `aced2a2` |

## 6. Próximos Pasos Prioritarios

1. ~~**Probar upload PDF end-to-end**~~ — ✅ Completado
2. ~~**Auto-creación de perfil**~~ — ✅ Trigger `handle_new_user` en Supabase (migration 006)
3. ~~**Presence indicators**~~ — ✅ Supabase Presence API en party roster
4. ~~**Campaign join/invite**~~ — ✅ Sistema de invitaciones por código
5. **Commlink recipients** — Agregar selector de destinatarios usando party roster
6. **Image generation** — Conectar servicio de imágenes (Imagen 3 o similar) al tag `<IMAGE>`
7. **Tests** — al menos smoke tests para el gameplay loop
8. **Vercel config** — Root Directory → `projects/SAM/frontend`
7. **Vercel config** — configurar Root Directory → `projects/SAM/frontend`

---
*Última actualización: 2 Abr 2026 — Multi-agent architecture integrated into server.py with legacy fallback. KnowledgeService RAG. stripSystemTags role-aware. Character context from DB.*
