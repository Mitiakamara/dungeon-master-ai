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

### Sesión 3 Abr 2026 — Multi-Agent Polish, Self-Damage, Mobile UX, Pending Roll Persistence

**Features implementados:**
1. **Self-damage intent** — Nuevo tipo `self_damage` en `IntentInterpreter` con `damage_dice`. `MechanicEngine.process_player_roll()` resuelve self-damage aplicando `calculate_hp_change()` al personaje + `state_updates`. `SAMOrchestrator` enruta el intent y emite `pending_player_roll` para esperar la tirada de daño. Cubre auto-lesiones, caídas, trampas.
2. **Pending player roll persistence** — `pending_player_roll` ahora se persiste en `combat_state["pending_player_roll"]` al final de `process_message()` y se restaura al inicio. Sobrevive entre requests, permitiendo flujos como "tira de daño" → siguiente mensaje del jugador con su tirada.
3. **Warning log para daño no rastreado** — Si un `dice_roll` se procesa sin generar `state_updates`, se loguea un warning. Útil para detectar daño narrativo que el motor no captura.

**Bug Fixes:**
1. **Narrator nunca cambia stats por pedido** — Regla 14 agregada al `Narrator` SYSTEM_PROMPT: "NEVER agree to change a character's level, class, stats, HP max, or abilities because a player asks. Levels are earned through XP only."
2. **Debug logs removidos** — `🔍 char_ctx` print removido de `server.py`. Presence `🟢` console.logs removidos de `use-presence.ts`.

**Frontend mobile UX:**
1. **`h-screen` → `h-[100dvh]`** — Layout principal usa `100dvh` (dynamic viewport height) para que el input no quede oculto bajo la barra del browser en mobile.
2. **`pb-safe` class** — Nueva clase utility en `globals.css` con `padding-bottom: env(safe-area-inset-bottom)` aplicada al input area del chat para iOS notch / Android nav bar.
3. **Dice tray compacto** — Botones `h-14` en mobile (vs `h-20` desktop), `text-lg` (vs `text-2xl`), grid `3 cols` (vs `2 cols`), gap `1` (vs `2`). Auto-cierre del Sheet 500ms después del roll.
4. **Header chat compacto en mobile** — `h-9 sm:h-14`, `text-xs sm:text-lg`, padding `px-3 sm:px-6`. Status text reducido a "OK"/"..." en mobile. Título con `truncate`.
5. **Input area más compacto** — `p-2 sm:p-4`, `mb-2 sm:mb-0` para más espacio vertical para escribir en mobile.

### Commits en main (3 Abr 2026)
```
f7cfcc1 fix: persist pending_player_roll between requests + compact mobile header for more input space
3f32334 fix: consolidated fixes — self-damage tracking, mobile input/dice tray, no level-up by request, cleanup debug logs
```

### Sesión 8 Abr 2026 — Healing Items, CR Balancing, Character Delegation

**Features implementados:**
1. **Healing items handler** — Type `item` en `IntentInterpreter` ahora reconoce pociones de curación (`is_healing: true`, `healing_dice: "2d4+2"`) con tabla de potions D&D 5e estándar (Healing/Greater/Superior/Supreme + Elixir of Health). El orquestador rutea a `pending_player_roll` esperando la tirada de daño/curación. `MechanicEngine.process_player_roll` resuelve el tipo `healing`: parsea el modificador del dice notation, aplica `calculate_hp_change(is_damage=False)` al target (self o party member), emite `state_update` con `damage` negativo. Frontend ya soporta esto sin cambios.
2. **CR Balancing** — Nuevas tablas en `rules.py`: `CR_XP_VALUES` (CR 0–30), `ENCOUNTER_THRESHOLDS` (Easy/Medium/Hard/Deadly por nivel 1–20). Funciones: `calculate_encounter_difficulty(monster_crs, party_levels)` (con multiplicadores DMG por número de monstruos) y `get_recommended_cr_range(party_levels)` (single/pair/group/boss). El orquestador inyecta `encounter_info` en el `campaign_context` antes de narrar: "Party: N players, avg level X. Recommended single monster CR: Y. Boss CR: Z. DO NOT use monsters above CR Z unless the story absolutely demands it." SAM ahora respeta los límites de CR según el nivel del party.
3. **Character delegation (`/delegate`, `/undelegate`)** — Nueva columna `characters.controlled_by uuid REFERENCES profiles(id)` (migration `schema_character_delegation.sql`). El GM puede delegar control de un personaje a SAM con `/delegate <name>` y devolverlo con `/undelegate <name>`. En combate, cuando es turno de un personaje delegado, el orquestador lo trata como NPC: construye un `npc_data` con stats del personaje real y lo resuelve con `engine.resolve_npc_turn`. Header marcado como "(SAM-controlled)". Útil para jugadores ausentes en combate.

**Helpers nuevos:**
- `orchestrator._find_party_member(name, party)` — búsqueda case-insensitive partial match
- `admin._find_character_in_active_campaign(name, gm_user_id)` — resolución de personaje en la campaña activa del GM

**Pendiente:** Ejecutar `schema_character_delegation.sql` en Supabase manualmente.

### Commits en main (8 Abr 2026)
```
5a7792e feat: healing items handler + CR balancing + character delegation (/delegate, /undelegate)
```

### Sesión 8 Abr 2026 (cont.) — Campaign Memories, Commlink Recipients, Mobile Polish

**Features implementados:**

1. **Campaign Memories — memoria narrativa persistente** — Nueva tabla `campaign_memories` con embedding vector(768), tipos (`fact`/`npc`/`location`/`plot`/`item`/`decision`), importance 1-10, source (manual/auto/session_summary). RLS para players (read) y GM (manage). `MemoryService` extrae hechos narrativos después de cada respuesta de SAM via Gemini 2.5-flash con prompt corto: máximo 3 facts, <100 chars cada uno. Las memorias se inyectan automáticamente en el `campaign_context` del narrador en cada nueva interacción. SAM ahora "recuerda" lo que pasó incluso cuando el historial de chat scrolla más allá. Migración SQL en `migrations/schema_campaign_memories.sql` (pendiente ejecución manual en Supabase).

2. **`/memory` command para GM** — Tres subcomandos:
   - `/memory list` — top 20 memorias ordenadas por importance, formato `#N [TYPE] (imp:N) content`
   - `/memory add <type> <text>` — agrega memoria manual con `importance=7`, `source='manual'`
   - `/memory delete <#N|UUID>` — borra por número (resuelve el UUID re-fetcheando) o por UUID directo
   - Validación de tipos contra `VALID_MEMORY_TYPES`, doble check `campaign_id` anti-cross-contamination

3. **Commlink recipients dropdown** — Nuevo endpoint `GET /api/messages/recipients?campaign_id=X` que retorna party members + entrada especial `S.A.M. (DM)` con `user_id=null`. Frontend ahora tiene un `<select>` real en lugar del input de texto libre. Sender names en inbox se resuelven correctamente: "S.A.M." para `sender_id=null`, propio nombre del personaje para mensajes propios, nombre real del personaje para otros players.

**Bug fixes:**

1. **MemoryService modelo + retries** — `gemini-2.0-flash` (deprecated) → `gemini-2.5-flash` (mismo que narrator/interpreter). `max_retries=1` para evitar bloqueos exponenciales en errores transitorios.

2. **Memory extraction fire-and-forget** — La extracción estaba in-lock bloqueando al jugador ~90s. Movida a `asyncio.create_task()` background después del `return` — el cliente recibe la respuesta inmediatamente, la extracción corre en paralelo. Variables capturadas en closure local (`_cid`, `_msg`, `_resp`, `_existing`) para evitar race conditions.

3. **Memory JSON recovery** — Si Gemini trunca el JSON output (max_tokens hit), regex `\{[^{}]+\}` recupera objetos completos individuales. `max_tokens` también subió de 500 → 1024.

4. **Commlink `receiver_id` Optional** — `PrivateMessageCreate.receiver_id` era `str` (required), ahora `Optional[str] = None` para permitir mensajes a SAM (`receiver_id=null`).

5. **Mobile chat input padding** — Input estaba pegado a los bordes laterales y a la barra del browser. Cambiado a `py-4 px-4 sm:px-6` con `mb-4 sm:mb-2`. Matchea el padding del messages area (`p-4`).

### Commits en main (8 Abr 2026, cont.)
```
f7e7001 fix: PrivateMessageCreate.receiver_id is Optional — allows sending to S.A.M.
f05ca98 feat: commlink — recipient dropdown + resolved sender names in inbox
a998bc9 feat: GET /api/messages/recipients — list party members + S.A.M.
6fea080 fix: cap memory extraction to 3 facts/100 chars + recover from truncated JSON
5ddd0cb fix: increase vertical padding/margin on chat input
1c695da fix: memory extraction fire-and-forget (asyncio.create_task) + bump max_tokens to 1024
122796a fix: add horizontal padding to chat input area for consistency with messages
52aacd2 fix: MemoryService — switch to gemini-2.5-flash + max_retries=1
8a62632 feat: /memory command for GM — list, add, and delete campaign memories from chat
a46abad feat: campaign memories — persistent narrative facts auto-extracted and injected into context
```

### Sesión 8 Abr 2026 (final) — PDF Character Import Improvements + Spell Slots Tracking

**Backend — `parse_character_pdf()` reforzado:**
1. **`max_output_tokens=8192`** agregado al `generate_content` call via `types.GenerateContentConfig`. Antes el default truncaba el JSON en personajes con muchos hechizos/items.
2. **Reglas del prompt reforzadas:**
   - **Inventory (regla 6):** "Extract ALL items... armor, weapons, potions, tools, adventuring gear. Do NOT skip items even if the list is long."
   - **Spells (regla 8):** "Extract ALL spells from ALL pages and ALL spell levels. Do NOT truncate."
   - **Nueva regla 11 (Spell Slots):** Formato `{'1': {'total': 4, 'used': 0}, '2': {'total': 3, 'used': 0}, ...}`
3. **JSON schema template:** Nuevo campo `status.spell_slots` agregado después de `spells`.
4. **Multipage hint:** "This PDF may have 4-6 pages. Extract data from ALL pages. Do not stop early."

**Frontend — Character sheet dialog:**
1. **Spell Slots panel** en la tab Spells (encima de la tabla de hechizos):
   - Lee `formData.status.spell_slots`, solo se renderiza si existe y tiene keys
   - Sort numérico de niveles (1, 2, 3...)
   - Cada nivel es un chip `Lvl N: used/total` con fondo `bg-muted`
   - **Click en el chip** → incrementa `used` (gasta un slot)
   - **Botón `−` a la izquierda** → decrementa `used` (recupera un slot)
   - Clamp automático entre `0` y `total`
   - Visual exhausted: `opacity-50 border border-red-500/40`
   - Persistencia automática vía `formData.status` al guardar

### Commits en main (8 Abr 2026, final)
```
b607a8f feat: spell slots panel in character sheet — click to use, − to recover
f0f43f2 feat: PDF character import — bump max_output_tokens to 8192, extract all spells/inventory/spell_slots, multipage hint
```

### Sesión 8 Abr 2026 (extra) — PDF Parse Hardening, Resource Consumption, /gold, Desktop Polish

**PDF Character Import — fixes en cadena:**
1. **Cleanup defensivo del JSON** — Strip de markdown fences + regex `,\s*([}\]])` para eliminar trailing commas. Si el primer parse falla, segundo intento con cleanup más agresivo (remover ASCII control chars, NO tocar comillas).
2. **`response_mime_type="application/json"`** en `GenerateContentConfig` — fuerza a Gemini a devolver JSON estructuralmente válido.
3. **`max_output_tokens=65536`** (era 8192) — el cap anterior se quemaba en thinking tokens internos de gemini-2.5-flash, dejando solo ~1238 chars de output visible (`finish_reason=MAX_TOKENS`).
4. **`thinking_config=types.ThinkingConfig(thinking_budget=0)`** — desactiva el thinking mode para esta llamada. PDF parse es extracción estructurada, no necesita reasoning. Todo el budget va al output visible.
5. **Logging de diagnóstico** — `finish_reason`, longitud del JSON, chars 600-900 alrededor del error de parse.
6. **Plan B en el prompt** — actions/bonus_actions/reactions ahora se documentan como `[]` por defecto. Regla 9 actualizada: "Only include SPECIAL or UNIQUE actions. Do NOT list standard actions like Attack, Dash, Dodge, Help, Hide, Ready, Search, Use Object."

**Frontend — Spell slots y dedup:**
1. **Bug crítico — `spell_slots` se descartaba** — El `useEffect` de `character-sheet-dialog.tsx` reconstruía `formData.status` campo por campo y no copiaba `spell_slots` (ni `saving_throws` antes del fix anterior). Resuelto: línea explícita `spell_slots: character.status?.spell_slots || {}`.
2. **Spell deduplication** — PDF parser a veces emite el mismo hechizo dos veces (lista multi-página). Dedup por `name-level` lowercased en dos lugares: el import handler (`character-create-dialog.tsx`) y el load handler (`character-sheet-dialog.tsx`).

**Resource consumption — spell slots e inventory:**
1. **Interpreter** — `spell` intent ahora incluye `spell_level` (0=cantrip, 1+=leveled, soporta upcast). 3 ejemplos en el prompt + 4 reglas de inferencia.
2. **Orchestrator** — Después de `engine.process_spell()`, valida `character_context.status.spell_slots[level]`. Si no hay slots: agrega `WARNING: ... The spell fizzles.` a los facts. Si hay slots: emite `state_update` tipo `spell_slot_consume`. Para items: emite `state_update` tipo `inventory_remove` con `qty: 1` cuando se identifica el item.
3. **server.py** — Dos handlers nuevos:
   - `spell_slot_consume`: lee `status.spell_slots[level]`, incrementa `used` con cap a `total`, UPDATE. Defensive: si no existe spell_slots o el level, log warning y skip.
   - `inventory_remove`: busca item case-insensitive en `status.inventory`, decrementa qty, remueve si llega a 0, UPDATE. Defensive: log warning si el item no está.

**`/gold` admin command:**
- `/gold <character> <±amount> <coin>` permite al GM ajustar dinero manualmente
- Parser: last arg=coin, second-to-last=amount, resto=name (soporta nombres con espacios)
- Validación de coin type (`cp/sp/ep/gp/pp`) y amount (entero con signo)
- Clamp a 0 (no permite negativos)
- Reusa `_find_character_in_active_campaign` (mismo helper que `/delegate` y `/memory`)

**Auto-refresh character post-SAM:**
- Nuevo `useRealtime` en `game-layout.tsx` sobre `messages` filtered by `campaign_id`
- Cuando llega un mensaje con `role === 'assistant'`, programa `setTimeout(fetchCharacterData, 1500)` — el delay da tiempo al backend a aplicar todos los `state_updates` antes del re-fetch
- Belt-and-suspenders: ya hay un `useRealtime` en `characters` table, pero el merge inmutable a veces pierde fields nested. El re-fetch explícito garantiza la versión completa.

**Character sheet dialog — desktop polish (mobile intacto):**
1. **Bio & Gear tab vertical en desktop** — `grid grid-cols-2` → `grid grid-cols-2 md:grid-cols-1`. Bio textarea + Inventory ya no compiten por ancho en desktop, cada uno toma full width.
2. **Bio textarea más bajo en desktop** — `h-40 md:h-32` (compensación visual al ser full-width).
3. **Inventory columns más espaciadas en desktop** — Item `col-span-7 md:col-span-8`, Weight `col-span-3 md:col-span-2`. Más padding horizontal `p-2 md:px-3 md:py-2`.
4. **Spells table padding desktop** — `p-3 md:px-4 md:py-3` en header y rows.
5. **Spacing entre secciones** — TabsContent `space-y-4 md:space-y-6` y grid `gap-4 md:gap-6`.

### Commits en main (8 Abr 2026, extra)
```
f48bb55 fix: re-fetch character via existing chat-interface message listener (avoid duplicate Realtime channel)
5a692ac feat: re-fetch character on SAM message + desktop layout polish
71af51b feat: /gold admin command — adjust character money manually
317b374 feat: spell slot consumption + inventory item consumption
7682909 fix: carry spell_slots into formData + dedupe spells by name+level
36dcbc9 fix: PDF parse — bump max_output_tokens to 65536, disable thinking budget, simplify actions extraction
f1379a1 fix: PDF parse — force JSON mode (response_mime_type) + remove apostrophe-breaking quote replacement + log finish_reason
bb9a200 debug: log JSON length + chars 600-900 around PDF parse error for diagnosis
6e747ac fix: PDF character import — clean trailing commas + 2nd-pass aggressive JSON parse with logging
```

### Sesión 9 Abr 2026 — Mini Sheet Redesign, Character Sheet Mobile Polish, Spell Sorting

**Mini sheet redesign (sidebar character card):**
1. **Ready Attacks y Spells Prepared eliminados** del mini sheet — reemplazados por:
   - **Spell Slots dots:** `1: ●●●○` con `●` en `text-purple-400` (disponible) y `○` en `text-gray-600` (usado). `flex flex-wrap`, sort numérico por level, skip levels con `total <= 0`.
   - **Gold compact:** Solo monedas con valor > 0, ordenadas descendente: `"15 GP · 5 SP · 21 CP"` en `text-amber-400 font-mono`.
   - HP/AC row intacto.

**Character sheet dialog — mobile polish (6 commits):**
1. **Stats tab:** `gap-8` → `gap-4 sm:gap-8` entre Saving Throws y Core Stats.
2. **Combat tab — vitals:** `flex` → `grid grid-cols-2 gap-2 sm:flex sm:gap-4` (2×2 en mobile, horizontal en desktop). Height `h-16` → `h-12 sm:h-16`. Text `text-2xl` → `text-lg sm:text-2xl`. Inputs reducidos proporcionalmente.
3. **Combat tab — HP row:** Los 3 campos (Max HP div, Current HP input, Temp HP input) normalizados a `h-8 sm:h-10`, `text-sm sm:text-lg`, `px-2 sm:px-3`, `font-bold`. Max HP cambiado de `bg-muted` a `bg-transparent` para matchear inputs. Container con `overflow-hidden`.
4. **Combat tab — attacks:** Removido `overflow-x-auto` + `min-w-[400px]` wrapper. Tabla ahora inline con `text-xs sm:text-sm`, `p-2 sm:p-3`, `truncate` en names, `break-all` en damage/type. Container con `overflow-x-hidden`.
5. **Spells tab — responsive columns:** `min-w-[500px]` removido. Grid `grid-cols-6 sm:grid-cols-12`. Mobile muestra solo **Lvl | Name | Time** (3 cols esenciales). Range, Duration, Effect/School con `hidden sm:block`. Cantrip display: `"Cantrip"` → `"C"`.
6. **Spells tab — sorting:** Nuevo state `spellSort: 'level' | 'name'`. Headers Lvl y Name clickeables (`cursor-pointer`), header activo en `text-purple-400` con `▲`. Sort: cantrips primero (level 0), luego por nivel numérico, luego por nombre. IIFE pattern para computar `sortedSpells` inline.
7. **Bio & Gear tab:** `grid grid-cols-2 md:grid-cols-1` → `grid grid-cols-1` (vertical stack siempre).
8. **Sidebar header:** `px-4` → `px-4 pr-10 md:pr-4` para evitar que el botón X del Sheet se solape con el icono de dark mode toggle.

### Commits en main (9 Abr 2026)
```
a1d231b fix: sidebar header pr-10 on mobile to prevent Sheet X button overlapping dark mode toggle
4c7bd6f fix: align HP row boxes — same height, text size, padding, and bg across Max/Current/Temp
25d88b2 fix: combat tab mobile — smaller vitals boxes, compact HP row, inline attacks table with break-all, overflow-x-hidden
6e5c53e fix: combat vitals 2x2 grid on mobile, spells responsive columns, sortable spells by level/name
64d0989 fix: character sheet mobile — reduce saves gap, wrap vitals, scroll spells table, stack bio/gear vertical
a93c302 feat: replace Ready Attacks/Spells Prepared with Spell Slots dots + Gold display in mini sheet
```

### Sesión 12 Abr 2026 — Avatares AI, Narrator Tuning, Realtime Fix, localStorage Cleanup

**AI-Generated Avatars (Imagen 4):**
1. **`generate_avatar()`** — Genera retratos de personaje con Imagen 4. Prompt D&D-focused: "Fantasy character portrait, head and shoulders, dramatic lighting, dark background. {race} {char_class} named {name}. {bio_snippet}." Fallback chain: `imagen-4.0-fast-generate-001` (barato) → `imagen-4.0-generate-001` (quality). Si ambos fallan, cae a DiceBear SVG como antes.
2. **`upload_avatar()`** — Sube bytes PNG a Supabase Storage bucket `avatars/characters/{id}.png`. Retorna URL pública.
3. **`parse_character_pdf()`** — Intenta avatar AI primero. Si funciona, guarda como `data:image/png;base64,...` para preview (el character ID no existe aún). Si falla, genera DiceBear con seed `{name}-{race}-{class}`.
4. **Migration `schema_avatar_storage.sql`** — Bucket `avatars` público con RLS: authenticated upload, public read.

**Narrator Prompt Tuning:**
1. **Brevedad reforzada** — "2-4 paragraphs max" → "Maximum 2 short paragraphs, NEVER exceed 120 words. Players are on mobile — every extra word is a crime."
2. **Regla 15 (Character Knowledge)** — SAM ahora está instruido a responder preguntas sobre stats del personaje con datos exactos del CHARACTER IN SCENE context. Calcula totales de skill checks (d20 + modifier + proficiency). Nunca dice "check your sheet".

**Realtime Subscription Stability:**
- **Root cause encontrado:** `createClient()` en `use-realtime.ts` se ejecutaba en cada render, creando una nueva referencia que disparaba el `useEffect` → unsubscribe + resubscribe en cada render de React. Durante el gap, eventos de Realtime se perdían.
- **Fix:** `useRef(createClient())` crea el client una sola vez. Removido `supabase` del dep array. Channel names mejorados para incluir el filtro.

**localStorage Stale Character Cleanup:**
- **`fetchCharacterData()`** — Si GET character devuelve 404, limpia localStorage + setSelectedCharacter(null) + auto-selecciona el primer personaje de `/api/characters/user/me`.
- **`loadCharacter()` (on-mount)** — Mismo patrón 404 en la carga inicial desde localStorage.
- **`handleDelete()`** en `character-list.tsx` — Al borrar un personaje, limpia localStorage si el ID matchea.

### Commits en main (12 Abr 2026)
```
14c0b1f fix: switch to Imagen 4.0 models (fast first, then standard)
21a39f8 fix: try 3 Imagen model versions as fallback chain + diagnosis
f12ea77 fix: remove negative_prompt from Imagen config
e03df55 feat: AI-generated character avatars via Imagen 4 + Supabase Storage
ecbaa28 fix: narrator prompt — enforce 120 word limit + character stats awareness
e189447 fix: stabilize Realtime subscriptions — useRef for Supabase client
6408ef4 fix: clear stale character from localStorage on 404 or delete
```

**Bug fix posterior — auto-refresh character no funcionaba (commit `f48bb55`):**
La primera implementación creó un `useRealtime` separado en `game-layout.tsx` para escuchar `messages.INSERT`. Resultó conflictivo con el `useRealtime` ya existente en `chat-interface.tsx` para la misma tabla — Supabase no garantiza routing limpio cuando un mismo cliente se subscribe dos veces al mismo table con filtros distintos, y el `createClient()` en cada render del hook causa re-subscriptions agresivas. Fix: eliminar el listener duplicado y reusar el de `chat-interface.tsx` via callback prop `onSamMessageReceived?: () => void`. Cuando el listener procesa un mensaje con `role === 'assistant'`, llama el callback que dispara `setTimeout(fetchCharacterData, 1500)` en `game-layout.tsx`. Una sola subscription, callback con deps frescas via `useCallback`.

### Sesión 23-24 Abr 2026 — Combat System: Trigger, Bug Fixes, Visible Initiative, HP Ground Truth

**Contexto:** El orchestrator tenía toda la infraestructura de combate (`CombatState`, `_resolve_npc_turns`, `resolve_npc_turn`, `DiceRoller`) desde la Sesión 26 Mar, pero nunca se activaba en el nuevo flujo multi-agente. Esta sesión implementa el trigger completo y resuelve 10+ bugs detectados en playtest.

**Fase 1 — Trigger y Monster Lookup (`6673cd0`):**
1. **Intent `start_combat`** — Nuevo tipo en `interpreter.py`. Solo se activa cuando `in_combat=False`. Detecta lenguaje agresivo EN/ES ("ataco al golem", "I charge at the creature", "saco mi espada"). Extrae `target` del mensaje. Si `in_combat=True`, el interpreter usa `"attack"` en vez de `"start_combat"`.
2. **`_handle_start_combat()`** — En `orchestrator.py`. Rola iniciativa para todos los PCs (1d20 + dex_mod) y NPC, llama `combat.start_combat()`, emite facts con orden de iniciativa.
3. **`_lookup_monster()`** — Busca monstruo via `match_compendium` RPC (embedding con nombre del target), luego re-query directo a tabla `monsters` por nombre para obtener datos estructurados (hp, ac, cr, stats, actions → attacks). Fallback genérico `{hp:50, ac:15, attacks: [{bonus:"+5", damage:"1d8+3"}], cr:3}` si no se encuentra.
4. **Combat reminder** — Si `combat.active` y el intent es roleplay/movement/free_action/ability, inyecta fact "It's X's turn. Remind the player to declare their action and roll their dice." El narrator ya no puede resolver ataques narrativos sin dados.
5. **Narrator RULE 16** — Reglas de combate: anunciar iniciativa dramáticamente, siempre decir de quién es el turno, NUNCA resolver ataques sin dados, narración ≤1 párrafo por turno, enforce Extra Attack a nivel 5+.

**Fase 2 — Auto-resolver primer turno + Frontend contract (`255681d`):**
- **Bug 1:** Si el primer turno en initiative order era de un NPC o player delegado (`controlled_by != None`), el combate se congelaba porque nadie rolaba. **Fix:** `_resolve_npc_turns` acepta `advance_first` (default `True`). El flujo de `dice_roll` sigue usando el default; `_handle_start_combat` llama con `advance_first=False` cuando el primer combatiente es NPC o delegado.
- **Bug 2:** Frontend `chat-interface.tsx` leía `combatState.current_turn` (string con nombre) pero `CombatState.to_dict()` solo exponía `current_turn_index`. Placeholder mostraba "undefined's turn". **Fix:** `to_dict()` ahora incluye `current_turn: <name>` derivado de `get_current_turn()`.

**Fase 3 — Damage parser + DM_ROLL emission (`88c6d34`):**
- **Bug:** `resolve_npc_turn` y `_double_dice` crasheaban con damage strings que incluyen damage type (ej: `"2d10 fire"`, `"1d6+2 slashing"`). El parser hacía `split("d")` sobre el string completo → `int("10 fire")` crasheaba.
- **Fix:** Tokenizar con `split()` (whitespace) primero. Primer token = dice expression (`"2d10"`, `"1d6+2"`), resto = damage type (`"fire"`, `"slashing"`). Aplicado en ambos lugares. Guard `ValueError` con fallback a `1d6` si malformed. Nuevos campos `damage_type` y `damage_spec` en el resultado del attack.
- **DM_ROLL para NPC attacks:** `_resolve_npc_turns` ahora emite `<DM_ROLL>` tags para attack roll Y damage roll en formato frontend: `{"result", "roll", "reason"}`. Matchea el renderer existente en `chat-interface.tsx` línea 745.
- **Narrator RULE 9 split:** 9 sigue prohibiendo inventar tags XML; 9a requiere preservar `<DM_ROLL>` verbatim cuando viene en MECHANICAL FACTS. Sin esto, el narrator los stripearía.

**Fase 4 — Delegated PCs + HP updates (`d1613fa`):**
- **Bug 1 (CRÍTICO):** Personajes delegados (`controlled_by != None`) atacaban a sus propios aliados en vez de los enemigos. `_resolve_npc_turns` pasaba `players_in_combat` como targets sin importar quién atacaba. **Fix:** Construir DOS listas (`players_in_combat`, `npcs_in_combat`). NPCs reales atacan players; PCs delegados atacan NPCs.
- **Bug 2:** PCs delegados usaban ataques genéricos en vez de los del character sheet. **Fix:** Nuevo helper `_build_combatant_from_character(char)` extrae ataques del `status.attacks` real. Fallback inteligente: `max(STR_mod, DEX_mod) + proficiency_bonus` (calculado del level, no hardcoded +5).
- **Bug 3:** HP no actualizaba después de ataques. **Root cause:** `resolve_npc_turn` leía `target_char.get("hp_current")` (top-level) pero las filas DB de party_characters lo tienen dentro de `status` nested dict → retornaba 0 → `calculate_hp_change(0, damage, 0)` → new_hp=0 siempre. **Fix:** Nuevo helper `_flatten_player_for_combat(char)` hoista `status.hp_current/hp_max/ac` a top-level antes de pasarlo al engine. Guard defensivo en `mechanic.resolve_npc_turn`: si top-level falta, lee de `status`; si `hp_max` es 0, usa `hp_current` como floor.
- **Bug 4:** Narrator pedía "1d6+4" para la greataxe de Björn (debería ser 1d12+STR). **Fix:** RULE 16 reforzada con referencia 5e (Greataxe 1d12, Longsword 1d8, Rapier 1d8+DEX, etc.) + instrucción estricta de leer `status.attacks`. `_resolve_npc_turns` inyecta cheat-sheet de armas en los facts cuando es turno de un player: "Björn's available attacks: Greataxe: to-hit +7, damage 1d12+4 slashing".
- **Extra fix:** Parser de `attack.bonus` ahora maneja `"-1"` y padding correctamente.

**Fase 5 — Initiative visible + HP ground truth (`d337241`):**
- **Fix 1:** SAM auto-rolaba iniciativa pero no mostraba los rolls. **Fix:** `_handle_start_combat` pre-rola init para el NPC también, emite un `<DM_ROLL>` tag por combatiente con formato frontend (`{"result":18,"roll":"1d20+1","reason":"Björn Initiative"}`), agrega breakdown legible a los facts + instrucción al narrator para anunciar dramáticamente. Narrator RULE 16 actualizada para narrar cada roll y preservar tags.
- **Fix 2:** Narrator inventaba HP del monstruo (drift entre turnos: "41/50" luego "43/50" en la misma pelea). **Fix:** `_resolve_npc_turns` inyecta bloque `COMBAT STATUS:` al final con HP exacto de todos los combatientes (fuente de verdad: `combat.initiative_order` para NPCs, `party_characters[].status.hp_current/hp_max` para players con overlay fresh DB values). El flujo principal también inyecta el bloque cuando `combat.active` y aún no está presente (player mid-action con pending roll). Narrator RULE 16 nueva cláusula "HP GROUND TRUTH": citar verbatim, nunca inventar ni redondear.

**Arquitectura final del combat loop:**
1. Player escribe "ataco al golem" → interpreter detecta `start_combat` (porque `in_combat=False`)
2. `_handle_start_combat` → lookup monster, rola init para todos (PCs via DEX mod, NPC via compendium mod), emite DM_ROLL tags, llama `combat.start_combat()`
3. Si primer turno es NPC/delegado → auto-resolver con `advance_first=False`
4. Facts incluyen: COMBAT STARTED + Initiative rolls + Initiative order + COMBAT STATUS + weapon cheat-sheet + "It's X's turn"
5. Narrator preserva DM_ROLL tags + anuncia iniciativa + pide acción al primer player real
6. Player escribe "ataco con hacha" → interpreter detecta `attack` (porque `in_combat=True`)
7. Player rolea 1d20 → mechanic procesa → si acierta, pide damage roll
8. Player rolea damage → mechanic aplica → `_resolve_npc_turns` ejecuta NPC turns con DM_ROLL tags + COMBAT STATUS + weapon cheat-sheet para el siguiente player

### Commits en main (23-24 Abr 2026)
```
d337241 Feat: Visible initiative rolls + authoritative combat HP status for narrator
d1613fa Fix: Delegated PCs attack enemies not allies, HP updates from nested status, weapon cheat-sheet
88c6d34 Fix: damage dice parser handles damage type suffix + DM_ROLL emission for NPC attacks
255681d Fix: Auto-resolve NPC/delegated first turns after combat starts + current_turn name
6673cd0 Feat: Combat system trigger — start_combat intent, monster lookup, combat reminders
```

### Sesión 16 Abr 2026 — Fetch robustness + admin persistence + player damage

**Fetch error handling (`3a71c4e`):**
- **Problema:** `authenticatedFetch` podía colgarse indefinidamente en mobile background suspension; el frontend renderizaba mensajes optimísticamente pero no detectaba 4xx/5xx ni network failures de forma consistente; el dice tray caía a fallback client-side (`Math.random`) silenciosamente sin avisar al usuario.
- **Fix 1:** `DEFAULT_TIMEOUT_MS = 30000` + `AbortController` en `lib/api.ts`. Señal se combina con `options.signal ?? controller.signal` para respetar aborts externos. `clearTimeout` en `finally` — nunca leaks.
- **Fix 2:** `handleSendMessage` en `chat-interface.tsx` ahora hace `if (!res.ok) throw new Error(...)` antes de parsear JSON → los errores HTTP caen al `catch` que ya mostraba toast con retry action.
- **Fix 3:** `dice-tray.tsx` importa `toast` y muestra `toast.warning("⚠️ Dice rolled locally")` cuando `/api/roll` falla antes de caer al fallback local. El usuario ya no roba resultados "fake" silenciosamente.

**Admin command persistence (`52e95de`):**
- **Problema:** Respuestas de comandos admin (`/list`, `/checkpoint`, `/load`, `/gold`, `/memory`, `/delegate`, `/undelegate`) se devolvían directamente como JSON del endpoint pero NO se insertaban en la tabla `messages`. El jugador que ejecutó el comando veía el resultado, pero el resto de la party no — y el GM no tenía record histórico al recargar.
- **Fix:** Después de `AdminService.handle_command()` y antes del `return`, si `cid` está disponible y el comando NO es `/reset` (que ya hace su propio broadcast con `CLEAR_CHAT`), insertar `admin_response` en `messages` como `role=assistant`, `sender_id=None`, `visibility=public`. El INSERT dispara Realtime → todos los clientes reciben la respuesta.
- **Defensive:** Wrap en try/except — si el insert falla, el comando igual retorna al jugador original.

**Player damage application (`a8ced24`) — BUG CRÍTICO:**
- **Problema:** Durante combate, las tiradas del dice tray (d20 de ataque, d12 de daño) no aplicaban daño al HP del NPC. El `COMBAT STATUS` fact seguía mostrando HP original → narrator inventaba HP → combate infinito.
- **Root cause:** El interpreter clasificaba `[SYSTEM EVENT] rolled 1d20` como `dice_roll`, pero `engine.pending_player_roll` era `None` (nadie llamó `process_attack`). `process_player_roll` hacía return con `{"action": "freeform_roll"}` → sin side effects → HP del NPC intacto.
- **Fix:** Nuevo método `_setup_combat_freeform_pending()` en `orchestrator.py`. Antes de `_handle_dice_roll`, si `combat.active` y no hay pending, infiere intent del dado:
  - **d20** → `pending_player_roll = weapon_attack` contra el primer NPC vivo, usando el primer arma del personaje (`status.attacks[0]`). Fallback: unarmed strike.
  - **non-d20** → `pending_player_roll = weapon_damage`, matcheando el dado (ej: d12) contra el `weapon.damage` del personaje (ej: `"1d12+4 slashing"`). Fallback: primer arma.
- **Por qué funciona:** Los resolvers existentes (`_resolve_weapon_attack`, `_resolve_weapon_damage`) ya llaman `combat.update_npc_hp(name, new_hp)`, y `CombatState.update_npc_hp` ya llama `remove_combatant` si `hp <= 0`, que llama `end_combat` si no quedan NPCs vivos. Solo faltaba que el flujo `dice_roll` alcanzara esos resolvers.
- **Flujo completo post-fix:**
  1. Björn tira d20 → orquestador detecta combat + no pending → autoconfigura `weapon_attack` con greataxe contra zombie → `_resolve_weapon_attack` hace d20+bonus vs AC → HIT → deja `pending_player_roll = weapon_damage` persistido en `combat_dict`
  2. Björn tira 1d12 → restaurado como `weapon_damage` → `_resolve_weapon_damage` aplica vía `update_npc_hp` → si HP ≤ 0, `remove_combatant` + `end_combat` si no quedan NPCs
  3. Post-damage roll (pending limpio) → `_resolve_npc_turns` ejecuta — respetando que el turno enemigo sucede **después** del daño, no del attack roll
  4. `COMBAT STATUS` inyectado al narrador refleja el HP real del NPC

### Commits en main (16 Abr 2026)
```
a8ced24 fix: apply player damage to NPC HP during combat
52e95de feat: persist admin command responses to messages table
3a71c4e feat: 30s AbortController timeout + robust fetch error handling
```

### Sesión 24 Abr 2026 — DM_ROLL grouping + turn enforcement + tickets system

**DM_ROLL chips stacking (`73f8a38`):**
- **Problema UX:** chips `<DM_ROLL>` inline dentro del párrafo dejaban los rolls de iniciativa (3-4 seguidos) esparcidos a través del texto.
- **Fix:** `renderMessageContent()` en `chat-interface.tsx` ahora camina los parts del split y agrupa DM_ROLLs consecutivos separados solo por whitespace en un `<div flex flex-col gap-1 my-2 items-start>`. Un solo DM_ROLL sigue inline; 2+ → columna. Typo `Invlaid` → `Invalid` corregido. (Ticket SAM-001 sigue IN_PROGRESS — hoist absoluto aún pendiente.)

**Turn enforcement + Extra Attack (`839ba73`) — SAM-002 DONE:**
- **Problema:** jugadores podían actuar fuera de turno (escribir "ataco al zombie" cuando era el turno de otro) y el sistema procesaba la acción. Además, no se respetaba Extra Attack (martials nivel 5+).
- **Turn guard en `orchestrator.process_message()`:** el intent se parsea primero, luego el guard revisa. Si `combat.active` y `sender_name != current_name`:
  - Intents `attack`/`spell`/`ability`/`start_combat` → bloqueados, emite fact `OUT_OF_TURN: It's {current}'s turn, not {sender}'s.` → narrator produce solo recordatorio in-character.
  - Intent `dice_roll` → permitido solo si `pending_player_roll.character_name == sender_name` (stamped en `_setup_combat_freeform_pending` con `sender_name`).
- **Action economy en `combat_state.py`:**
  - Nuevo helper top-level `has_extra_attack(combatant)` — True si class ∈ {Barbarian, Fighter, Paladin, Ranger} y level ≥ 5 (Fighter 11/20 simplificado a 2).
  - `actions_remaining` seeded por `_set_actions_for_current_turn()` en `start_combat` y al final de `advance_turn` → si nuevo current es player, 2 o 1 según extra attack; si NPC, 0.
  - `consume_action()` + `turn_is_over()` (`actions_remaining <= 0 and pending_action is None`).
  - Field persistido en `to_dict()` → sobrevive entre requests.
- **Dice_roll handler en orchestrator:** snapshot de `previous_pending_type` antes de `_handle_dice_roll`. Después, si pending se limpió:
  - Consume acción si previous ∈ {`weapon_attack`, `weapon_damage`, `spell_attack`, `spell_damage`} — cubre HIT + damage aplicado Y también MISS (attack resuelto sin damage follow-up).
  - `turn_is_over()` → `_resolve_npc_turns()` normal.
  - Else → facts += `"→ Björn has 1 action(s) remaining. Ask if they attack again."`
- **Player combatants stamped con `class` + `level`** en `_handle_start_combat` para que `advance_turn` pueda calcular Extra Attack sin cargar el character de DB.
- **Narrator RULE 16 ampliada:** bullet para OUT_OF_TURN (<30 words, in-character) + bullet para "action(s) remaining" (invitar segundo ataque en una oración, NO narrar).

**Admin command persistence verification (`52e95de`):** Confirmado en playtest que `/list`, `/checkpoint`, etc. ahora broadcastean via Realtime.

**Sistema de tickets (`061f24a`):** Nuevo archivo `SAM_tickets.md` con 13 tickets iniciales + convenciones (IDs `SAM-XXX`, tipo, prio P0-P3, estado OPEN/IN_PROGRESS/BLOCKED/DONE). Workflow: ticket abierto antes de instrucción, referenciado en el título, cerrado con commit + absorción de detalle en este log.

**Initiative ground truth (`738f85f`) — SAM-013 DONE:**
- **Problema:** narrator inventaba números de iniciativa violando el `result` dentro de los `<DM_ROLL>` tags. Playtest mostró chip con `result:5` narrado como "la criatura se mueve con un 9" y turn order incongruente.
- **Fix:** RULE 16 del narrator reemplaza el bullet genérico de initiative con "INITIATIVE GROUND TRUTH" — 4 sub-reglas explícitas: (1) preservar tags verbatim, (2) prosa cita `result` exacto, (3) turn order list cita números exactos, (4) empates siguen el orden de los facts. Agregada cláusula "Violation of this rule breaks the player's trust in the dice."

**DM_ROLL hoist (`c215cc7`) — SAM-001 DONE:**
- **Problema:** el agrupador del `73f8a38` solo funcionaba cuando los `<DM_ROLL>` estaban separados por whitespace puro. Gemini los intercala con prosa corta ("Björn saca un 17, mientras la criatura..."), así que en la práctica los chips quedaban esparcidos por el párrafo.
- **Fix:** `renderMessageContent` ahora cuenta los `<DM_ROLL>` en el mensaje y branchea:
  - **2+ rolls → modo HOIST:** extrae los chips con `content.matchAll(/<DM_ROLL>([\s\S]*?)<\/DM_ROLL>/g)`, los renderiza en un `<div flex flex-col gap-1 my-2 items-start>` al tope de la burbuja, y renderiza el texto narrativo (`content.replace(dmRollRegex, "")`) debajo. Limpieza de whitespace post-strip: `[ \t]+ → " "`, ` *\n → \n`, `\n{3,} → \n\n`, `trim()`.
  - **0 o 1 roll → modo INLINE:** se mantiene el split-and-walk clásico para que un chip solitario (ej. skill check) siga fluyendo dentro de la oración.
- **Estilos del chip:** idénticos en ambos modos (fondo negro semi, borde morado, emoji 🎲, mono font, `w-fit` en hoist, `mx-1 my-1` en inline).

### Commits en main (24 Abr 2026)
```
c215cc7  fix(SAM-001): hoist all DM_ROLL chips to the top when 2+ are present
738f85f  fix: enforce INITIATIVE GROUND TRUTH in narrator RULE 16 (SAM-013)
061f24a  chore: add SAM_tickets.md with 13 initial tickets and workflow conventions
839ba73  feat: combat turn enforcement + Extra Attack action economy
73f8a38  feat: stack consecutive DM_ROLL chips vertically + fix typo
```

### Sesión 5 Jun 2026 — SAM-017: regresión KeyError en narrator (combate caía al legacy)

**Contexto:** Playtest del 5 Jun reveló que TODOS los mensajes de combate caían al legacy `SAMBrain` (`ai.py`). Logs de Render (`2026-06-05T20:54:21`) mostraban `KeyError: '"result"'` en `narrator.py:122` (`narrate_mechanics` → `SYSTEM_PROMPT.format(...)`), seguido de `⚠️ Orchestrator failed, falling back to legacy SAMBrain`.

**Causa raíz (regresión de SAM-013, commit `738f85f`):** El bullet "INITIATIVE GROUND TRUTH" agregado a RULE 16 incluyó un ejemplo JSON literal `{"result": 5, "reason": "enemy Initiative"}` dentro del `SYSTEM_PROMPT`. Como ese prompt pasa por `str.format()`, Python interpretó `{"result"...}` como placeholder y buscó un argumento `"result"` → `KeyError`.

**Impacto:** Al caer al legacy en cada combate se perdían turn enforcement, persistencia consistente de HP, y la validez de los DM_ROLLs. Esto convirtió a SAM-017 en causa raíz de tres síntomas observados en playtest (SAM-014 HP no persiste, SAM-015 DM_ROLL "Invalid Roll Data", SAM-016 Extra Attack no se activa), que quedaron BLOCKED hasta validar el fix.

**Fix:**
1. **Escape de llaves** — En RULE 16, `{"result": 5, "reason": "enemy Initiative"}` → `{{"result": 5, "reason": "enemy Initiative"}}` (escape de `str.format()`).
2. **Auditoría completa** — `grep` de todas las `{` del archivo. Confirmado que la línea 66 era la única llave literal sin escapar; el resto son placeholders válidos del `.format()` (`dm_style`, `campaign_context`, `character_context`, `party_context`, `mechanical_facts`, `character_name`, `player_message`) o f-strings de código Python (líneas 177, 194, 206, 209) que no pasan por `.format()`.
3. **Smoke test local** — `Narrator.SYSTEM_PROMPT.format(dm_style=..., campaign_context=..., character_context=..., party_context=...)` corre sin `KeyError` (6596 chars).

**Pendiente:** validación post-deploy en prod (campaña Genie's Wishes): confirmar que ningún chat de combate cae al legacy, que los logs muestran `💚 HP updated:` consistente, y que el sidebar HP coincide con el HP narrativo tras F5. Según resultado, cerrar SAM-014/015/016 como "resuelto por SAM-017" o diagnosticar individualmente.

**Lección:** cualquier ejemplo con llaves literales (`{`/`}`) dentro de un string que después pasa por `str.format()` debe escaparse como `{{`/`}}`. Vale la pena un smoke test del `.format()` cada vez que se edita un prompt con llaves.

### Sesión 5 Jun 2026 (cont.) — SAM-020 auditoría + SAM-018 fix de stats

**SAM-020 — Auditoría arquitectónica (`SAM_audit_2026-06-05.md`, commits `03bc7b9`/`3cba19c`):** mapa read-only del estado real del sistema en 8 secciones (tags, intent, combate, persistencia HP, legacy vs orchestrator, contratos rotos, formato, errores silenciosos). Hallazgo principal: el pipeline nuevo (orchestrator) **no implementa loot/XP/level-up/imágenes** — solo viven en el legacy `ai.py`, alcanzado solo por excepción → en operación normal se descartan. Generó 13 tickets (SAM-018, 021–032) y reconcilió SAM-014/015/016 con la causa raíz SAM-017.

**SAM-018 — Initiative/ataque-delegado modifiers +0 (commit `5f6a880`):**
- **Causa raíz:** `characters` tiene dos columnas jsonb separadas: `stats` (top-level, `{str,dex,...}` enteros) y `status` (HP/AC/attacks/...). El orchestrator leía `status.get("stats")` (anidado, siempre vacío) en `_handle_start_combat` (`orchestrator.py:488`, iniciativa de jugadores) y `_build_combatant_from_character` (`:603`, ataques de PC delegado) → `dex_mod`/`str_mod` = 0 → toda iniciativa y ataque delegado sin modificador. `mechanic.py:419` (skill checks) ya leía el lugar correcto → asimetría que delató el bug.
- **Fix:** ambos call-sites pasan a `pc.get("stats")`/`char.get("stats")` (top-level). `status` se mantiene para HP/AC/attacks.
- **Verificación pre-deploy (query read-only a prod Supabase):** Björn Glacierfist (Barbarian, `stats.dex`=14 → +2) y Vex Was (Rogue, `stats.dex`=20 → +5); `status.stats` = `None` en ambos. Confirma el diagnóstico. `py_compile` OK.
- **Hallazgo lateral (corrige la reconciliación previa de SAM-016):** el campo `class` viene del PDF con sufijo de nivel (`"Barbarian 7"`, `"Rogue 7"`). `has_extra_attack` (`combat_state.py:17,22`) hace membresía EXACTA de set (`cls in EXTRA_ATTACK_CLASSES`) → `"barbarian 7"` ∉ `{"barbarian",...}` → **Extra Attack nunca se activa** para personajes importados de PDF, aún con el orchestrator activo. SAM-016 tiene por tanto DOS capas: el fallback legacy (SAM-017) y este class-matching roto. Ticket SAM-016 actualizado a OPEN con fix propuesto (`cls.split()[0]` o match por prefijo).
- **Lección:** un contrato de datos con dos niveles posibles (`stats` top-level vs `status.stats`) es una trampa silenciosa; leer del nivel equivocado se enmascara como "todo en +0" sin crashear (gracias al `or {}`). Verificar el shape real en BD antes de asumir.

**SAM-016 — Extra Attack: normalizar `class` en `has_extra_attack` (commit `186e462`):**
- **Causa raíz (de SAM-018):** `has_extra_attack` (`combat_state.py`) hacía membresía exacta de set sobre el `class` crudo, pero el PDF import lo guarda con sufijo de nivel (`"Barbarian 7"`) → `"barbarian 7"` ∉ `{"barbarian",...}` → Extra Attack nunca se activaba para martials importados de PDF.
- **Fix:** `cls_raw.split()[0] if cls_raw else ""` — extrae la primera palabra (la clase real), con guard anti-IndexError para class vacío.
- **Verificación pre-deploy (query read-only):** `level` es columna entera poblada (Björn 7, Vex 7), separada del `class` → `level >= 5` ya funcionaba, **sin segundo bug**. Björn (Barbarian 7) → 2 ataques; Vex (Rogue 7) → 1.
- **Capas de SAM-016:** (1) fallback legacy sin action economy (SAM-017, revalidar) + (2) class-matching roto (este fix). Ambas debían resolverse.
- **Lección:** un campo que mezcla dos datos (`class` = clase + nivel) rompe cualquier comparación exacta; normalizar antes de comparar.

### Sesión 9 Jun 2026 — SAM-034 end_turn + SAM-035 skill_check action economy

**Contexto (instrucción 219):** playtest del 9 Jun reveló tres bugs nuevos: el narrator alucinó un combate completo sin mechanical facts (SAM-033, queda OPEN), no existía forma de terminar el turno voluntariamente (SAM-034) y los skill checks en combate no consumían acción (SAM-035). Se implementaron 034 y 035 en un solo commit (`89cda66`).

**SAM-034 — intent `end_turn`:**
- `interpreter.py`: nuevo ACTION TYPE 11 `{"type": "end_turn"}` con triggers ("Paso", "Termino mi turno", "No hago nada más", "No tomo más acciones") activos SOLO con `in_combat=True`; fuera de combate las mismas frases son `free_action`. Regla agregada a RULES.
- `orchestrator.py`: handler nuevo antes del branch de roleplay — con combate activo pone `actions_remaining=0`, limpia el `pending_player_roll` abandonado (p.ej. ataque declarado nunca tirado) y llama `_resolve_npc_turns`; sin combate, cae a narración pura. `end_turn` agregado al tuple del turn guard → pasar fuera de turno produce el recordatorio OUT_OF_TURN estándar.
- `narrator.py`: bullet en RULE 16 — reconocer el pase en 1 línea (sarcasmo bienvenido), narrar los turnos NPC de los facts, NO volver a pedir declaración de acción. Sin llaves literales (lección SAM-017); smoke test de `SYSTEM_PROMPT.format()` OK en ambos prompts.

**SAM-035 — skill_check consume acción:**
- Timing: el d20 del check llega en el request SIGUIENTE, así que el consumo no puede ocurrir al declarar. El branch `skill_check` estampa `character_name` + `consumes_action` en el `pending_player_roll` (que ya persiste entre requests via `combat_state`), y el flujo `dice_roll` consume la acción al resolverse el pending — patrón idéntico al de `weapon_damage`/`spell_damage` (`previous_pending` snapshot).
- **Decisión de diseño:** `consumes_action` solo es True si el check pertenece al jugador en turno. El turn guard deja pasar `skill_check` de jugadores fuera de turno (checks reactivos, válidos en 5e); sin este gate, un check reactivo de Vex consumiría la acción de Björn. Stampear `character_name` además cierra un hueco del guard: antes un pending de skill_check sin owner bloqueaba el d20 del propio dueño si no era el current turn.

**Verificación local (sin LLM real, FakeLLM + stub de langchain):** 6 escenarios — end_turn básico (NPC actúa, round avanza, acciones reseedean), end_turn limpia pending abandonado, skill_check consume acción y dispara NPCs cuando era la última, check reactivo NO consume, turn guard bloquea end_turn ajeno, end_turn fuera de combate cae a roleplay. Todos pasan. Nota de entorno: `python` no existe en esta máquina y el `.venv` del workspace apunta a un perfil viejo; se usó `python3.14` de `~/.local/bin`.

**Pendiente post-deploy:** Tests A–D del playtest (pasar turno básico, pasar con Extra Attack restante, shove consume acción, "Paso" fuera de combate). SAM-033 (narrator alucina combate en roleplay) queda OPEN P1 — probable mitigación via sanitización del history legacy + refuerzo del ROLEPLAY_TEMPLATE.

### Sesión 9 Jun 2026 (cont.) — SAM-033 anti-alucinación + SAM-003 Sneak Attack

**Instrucciones 220 y 221, un solo commit de código (`2c08fcb`), deploy junto con 219.**

**SAM-033 — Narrator no puede inventar mecánica sin facts:**
- **Regla 9b** (SYSTEM_PROMPT): prohibido generar tags `<DM_ROLL>` propios en CUALQUIER formato (ni JSON, ni el attribute-style viejo `<DM_ROLL formula=.../>`); solo se permiten los copiados verbatim de MECHANICAL FACTS. Los tags legacy del history son artefactos deprecados, nunca imitarlos.
- **ROLEPLAY_TEMPLATE**: bloque "CRITICAL — NO COMBAT MECHANICS IN ROLEPLAY MODE" — sin mechanical facts no hay iniciativas, ni "¡COMBATE INICIADO!", ni resolución de ataques/daño/HP, ni tags DM_ROLL. Si el jugador quiere pelear, se le pide declarar el ataque para que el sistema arranque combate real.
- **Sanitización del history** (`_invoke`): los mensajes assistant se limpian con regex de los DM_ROLL legacy attribute-style ANTES de pasar al LLM (la fuente del formato alucinado). Los DM_ROLL en formato JSON se conservan (son el ejemplo bueno). Orden importante: la forma emparejada (`<DM_ROLL formula=...>...</DM_ROLL>`, DOTALL) se procesa antes que la self-closing — la regex self-closing matchearía el tag de apertura y dejaría un `</DM_ROLL>` huérfano.
- Ambos prompts pasan smoke test de `.format()` (lección SAM-017).

**SAM-003 — Sneak Attack como chain de pending rolls:**
- **Diseño:** dados por nivel de Rogue `(level+1)//2` d6 (Vex Rogue 7 → 4d6). MVP: aplica automáticamente si la clase es Rogue (asumimos ventaja/aliado adyacente en party de 2). Límite RAW: una vez por turno.
- **`combat_state.py`:** campo `sneak_used` (persiste en `to_dict`/`__init__`, resetea en `_set_actions_for_current_turn` y `end_combat`) + `mark_sneak_used()`/`sneak_available()`.
- **`orchestrator.py`:** `_get_sneak_dice()` (tolera sufijo de nivel en class, mismo patrón SAM-016); el pending `weapon_attack` lleva `sneak_dice` tanto en ataque declarado (`_handle_attack`, que ahora también estampa `character_name` para el turn guard) como en d20 freeform del dice tray (`_setup_combat_freeform_pending`). `sneak_damage` agregado al tuple de consumo de acción → la acción se consume UNA vez al final del chain completo (weapon_damage se saltea el consumo porque el pending de sneak sigue vivo). `_get_roll_prompt` pide el sneak en español.
- **`mechanic.py`:** `_resolve_weapon_attack` propaga `sneak_dice` al pending de daño en HIT; `_resolve_weapon_damage` aplica el daño del arma y, si había `sneak_dice` y el target sigue vivo, encadena pending `sneak_damage` con el target actualizado (HP post-daño) — si el target murió, no hay chain. `_resolve_sneak_damage` (nuevo) aplica el daño al mismo target via `update_npc_hp` y marca `sneak_used`. `get_results_summary` narra el sneak como parte del mismo ataque.
- **Warning de orphan rolls refinado:** antes disparaba para cualquier dice_roll sin `state_updates` (incluyendo daño a NPC correctamente aplicado, que vive en combat state). Ahora solo dispara si no hay resultados, ni pending, ni updates — rolls realmente huérfanos (el caso del 4d6 de abril).
- **`interpreter.py`:** regla nueva — "ataco con rapier y sneak attack" sigue siendo type `attack` (no `ability`), el sistema aplica el sneak solo.

**Verificación local (FakeLLM, 8 escenarios):** sanitización del history (legacy fuera, JSON intacto, sin closers huérfanos) · attack declara sneak_dice 4d6 · HIT propaga al weapon_damage · weapon damage aplica 11 (6+5) y encadena sneak SIN consumir acción · 4d6 aplica 14 más, consume UNA acción, NPCs actúan, turno avanza · once-per-turn (sneak_used=True → sin chain) · no-Rogue sin sneak · kill por weapon damage no encadena y termina combate · freeform d20 del dice tray también arma el chain. Todos pasan, cero warnings espurios.

**Pendiente post-deploy:** test SAM-033 con la frase exacta ("Quiero probar mi suerte en combate e iniciativa" → no debe inventar nada) y test SAM-003 con Vex no-delegada (d20 → 1d8+5 → 4d6, HP del NPC baja dos veces, una sola acción, sneak no repetible en el mismo turno).

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
- Mensajería privada (commlink) — usa campaignId real, dropdown de recipients, sender resolution. Pendiente: Realtime de nuevos mensajes y auto-mark-as-read.
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
- **Multi-agent architecture:** `backend/agents/` con DiceRoller, Rules, CombatState, MechanicEngine, IntentInterpreter, Narrator, SAMOrchestrator + KnowledgeService. Conectado a `server.py` con fallback a `ai.py` legacy. **`pending_player_roll` persiste entre requests** via `combat_state`.
- **Self-damage flow:** Intent type `self_damage` → MechanicEngine resuelve daño → state_update aplica HP. Cubre auto-lesiones, caídas, trampas.
- **Healing items:** Pociones de curación reconocidas por el interpreter (con dice + modifier). Pending roll → MechanicEngine aplica curación al target (self o party member). Tabla D&D 5e estándar.
- **CR balancing:** SAM recibe el rango recomendado de CR según el nivel del party. Tablas `CR_XP_VALUES` y `ENCOUNTER_THRESHOLDS` en `rules.py`. SAM no usa monstruos sobre el CR boss recomendado.
- **Character delegation:** `/delegate <name>` cede control de un personaje a SAM. Útil para jugadores ausentes en combate. Resolución como NPC en `_resolve_npc_turns`.
- **Campaign memories:** Tabla `campaign_memories` (fact/npc/location/plot/item/decision + importance 1-10). `MemoryService` extrae hechos auto via Gemini 2.5-flash después de cada respuesta (fire-and-forget background task, max 3 facts <100 chars). Memorias inyectadas en `campaign_context` para que SAM "recuerde" entre sesiones. Fallback de recuperación de JSON truncado.
- **`/memory` command:** GM puede listar/agregar/borrar memorias desde el chat (`/memory list`, `/memory add <type> <text>`, `/memory delete <#N|UUID>`).
- **Commlink recipients:** Endpoint `GET /api/messages/recipients` lista party members + entrada SAM. Frontend usa dropdown real + resuelve sender names en inbox (S.A.M., propio personaje, otros players).
- **PDF character import mejorado:** `max_output_tokens=65536` + `thinking_budget=0` (gemini-2.5-flash gastaba todo el budget en thinking interno). `response_mime_type="application/json"`. Cleanup defensivo de trailing commas + 2do intento agresivo. Prompt instruye extraer ALL spells/items de TODAS las páginas. Nuevo campo `status.spell_slots`. Actions/bonus_actions/reactions skip standard 5e actions.
- **Spell slots tracking:** Panel interactivo en character sheet (tab Spells) para gastar/recuperar slots con clicks. **`spell_slots` se carga correctamente** del backend (bug previo: el `useEffect` lo descartaba). Spell duplicates dedup'd por `name-level`.
- **Resource consumption automático:** Cuando un jugador castea un spell, el orchestrator emite `spell_slot_consume` y el backend decrementa el slot del nivel correspondiente (cantrips no consumen). Cuando usa un item, emite `inventory_remove` y el backend decrementa qty (remueve si llega a 0). Defensive: si el slot/item no existe, log warning sin crashear.
- **`/gold` admin command:** GM puede ajustar dinero manualmente con `/gold <character> <±amount> <coin>`. Soporta nombres con espacios, valida coin type, clamp anti-negativo.
- **Auto-refresh character post-SAM:** Cuando el listener de Realtime en `chat-interface.tsx` procesa un mensaje con `role === 'assistant'`, dispara el callback `onSamMessageReceived` provisto por `game-layout.tsx`, que hace `setTimeout(fetchCharacterData, 1500)`. Reusa el listener existente en lugar de crear un canal duplicado.
- **Character sheet responsive:** Bio & Gear siempre vertical. Combat vitals 2×2 grid mobile, HP row normalizado. Spells responsive cols (3 mobile / 6 desktop) con sorting clickeable (level/name). Attacks inline con break-all. Sidebar header `pr-10` para Sheet X.
- **Mini sheet redesign:** Spell Slots dots (`●●○` purple/gray) + Gold compact (`15 GP · 5 SP`) reemplazan las listas inertes de Ready Attacks y Spells Prepared.
- **Avatares AI (Imagen 4):** `generate_avatar()` con fallback chain (fast → standard → DiceBear). Supabase Storage bucket `avatars`. Base64 preview en PDF import.
- **Narrator tuning:** Max 120 words, 2 paragraphs. Regla 15: responde preguntas de stats con datos exactos del personaje.
- **Realtime estable:** `useRef(createClient())` evita re-subscriptions en cada render. Channel names incluyen filtro.
- **localStorage cleanup:** 404 en character → limpia + auto-select fallback. Delete character → limpia localStorage.
- **Narrator constraints:** Nunca cambia stats/level/abilities por pedido del jugador. Levels solo via XP.
- **Mobile UX:** `100dvh` layout, `pb-safe` para iOS notch, header compacto, dice tray con botones pequeños + auto-close, input area con margin extra.
- **Combat damage application completo:** Dice-tray rolls (d20/non-d20) durante combate autoconfiguran `pending_player_roll` → `_resolve_weapon_attack` y `_resolve_weapon_damage` aplican daño real al HP del NPC vía `combat.update_npc_hp()`. NPCs muertos se limpian con `remove_combatant` → `end_combat` automático si no quedan enemigos. COMBAT STATUS refleja HP real.
- **Fetch robustness:** `authenticatedFetch` aborta tras 30s vía `AbortController` (protege contra mobile background hangs). `handleSendMessage` valida `!res.ok` antes de parsear JSON. Dice tray muestra `toast.warning` cuando `/api/roll` falla antes de caer al fallback local (`Math.random`).
- **Admin commands persistidos:** Respuestas de `/list`, `/checkpoint`, `/load`, `/gold`, `/memory`, `/delegate`, `/undelegate` se insertan en `messages` table (`role=assistant`, `sender_id=NULL`) → broadcast a toda la party vía Realtime. `/reset` queda excepcional (ya hace su propio broadcast con `CLEAR_CHAT`).
- **Turn enforcement en combate:** Turn guard en `orchestrator.process_message()` bloquea intents `attack/spell/ability/start_combat` cuando `sender_name != current_turn` → emite `OUT_OF_TURN:` fact → narrator produce solo recordatorio in-character (<30 palabras). Dice rolls permitidos sólo si `pending_player_roll.character_name == sender_name`.
- **Extra Attack action economy:** `CombatState.actions_remaining` seeded por `has_extra_attack()` (Barbarian/Fighter/Paladin/Ranger ≥ lvl 5 → 2 acciones, resto → 1). `consume_action()` post-damage/miss. `turn_is_over()` gate antes de `_resolve_npc_turns`. Si queda acción, facts inyectan "X has N action(s) remaining. Ask if they attack again." y narrator invita al segundo swing.
- **Initiative ground truth:** Narrator RULE 16 con contrato explícito — los números dentro de cada `<DM_ROLL>` son autoritativos, prosa + turn order MUST citar el `result` exacto, empates siguen el orden de los facts. Fin de "la criatura se mueve con un 9" cuando el chip dice 5.
- **DM_ROLL hoist:** Cuando un mensaje tiene 2+ `<DM_ROLL>`, `renderMessageContent` los levanta a un `flex flex-col` al tope de la burbuja y renderiza el texto narrativo sin tags debajo (whitespace colapsado). Con 0 o 1 chip se mantiene inline.
- **Sistema de tickets:** `projects/SAM/SAM_tickets.md` trackea bugs/features/chores con IDs `SAM-XXX`, tipo, prio P0-P3 y estado. Workflow: ticket abierto antes de instrucción, referenciado en el título, cerrado con commit + absorción de detalle en este log.

### Completitud: ~97% (app funcional) + arquitectura multi-agente + combat loop completo con turn enforcement + Extra Attack

### Pendiente para "done"
- Commlink: Realtime para nuevos mensajes + auto-mark-as-read al abrir
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
*Última actualización: 24 Abr 2026 — DM_ROLL stacking (73f8a38) → hoist when 2+ rolls (c215cc7, SAM-001 DONE), turn enforcement + Extra Attack action economy (839ba73, SAM-002 DONE), tickets system (061f24a), initiative ground truth en narrator RULE 16 (738f85f, SAM-013 DONE). Sesión previa 16 Abr (a8ced24 + 52e95de + 3a71c4e): player damage application, admin command persistence, fetch robustness.*
