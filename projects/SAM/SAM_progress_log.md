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

**System prompt update:**
- **HP UPDATES refactored** — Tools son ahora "preferred" en vez de "mandatory". Si tools no están disponibles (fallback), SAM calcula y genera `<UPDATE>` y `<LOOT>` tags inline directamente. El frontend ya parsea estos tags sin importar si vienen de tools o inline. Esto completa el circuito de resiliencia: SDK nuevo → fallback sin tools → tags inline → frontend los procesa.

### Commits en main (25 Mar 2026)
```
9110278 fix: fallback tool execution via inline XML tags in system prompt
26d2e29 Fix: Clean tool-related messages from history before no-tools fallback
6b7d256 Fix: Fallback to no-tools response when Gemini thought_signature error occurs
407f1cf Refactor: Migrate from google-generativeai (legacy) to google-genai (new SDK) + upgrade langchain-google-genai to 2.1.12
48ed864 Fix: Prefix current user message with character name for multiplayer attribution
cad16de Docs: Update progress log — multiplayer polish, roster, dedup, admin commands
```

## 4. Estado Actual — Marzo 2026

### Lo que funciona
- Login/auth via Supabase JWT
- Crear/importar personajes (PDF via Gemini)
- Chat con SAM (narrativa + mecánicas)
- Dados (backend con `secrets.randbelow`, fallback client-side)
- Daño/curación via tools (`apply_damage`, `apply_healing`)
- Loot procesado y persistido en inventario (money + items)
- XP tracking y notificaciones
- DM rolls visualizados (chips morados)
- Compendio D&D 5e con búsqueda semántica (spells, monsters, items)
- RAG sobre módulos PDF de campaña
- Upload PDF de módulos de campaña (GM-only, con vectorización)
- Checkpoints (save/load/reset/list)
- Mensajería privada (commlink) — usa campaignId real
- Realtime sync via Supabase WebSocket (filtrado por campaña)
- **Multiplayer MVP:** mensajes filtrados por campaign_id, header dinámico, re-fetch al cambiar campaña
- **Multiplayer atribución:** sender_id en backend, burbujas diferenciadas por jugador (azul + nombre personaje), SAM con estilo original
- **Selector de campaña:** dropdown en dialog de crear personaje, fetch de campañas disponibles via API
- **Deduplicación robusta:** sin optimistic update, mensajes llegan solo via Realtime, dedup por id de BD
- **Party roster:** sidebar muestra otros personajes de la campaña con HP status
- **Admin commands GM-only:** `/reset`, `/checkpoint`, `/load`, `/list` solo para GM
- **Reset broadcast:** sincroniza limpieza de chat a todos los clientes via Realtime
- **SAM multiplayer-aware:** distingue jugadores por nombre (prefix `[CharacterName]` en mensaje actual + historial), no controla personajes ajenos
- **SDK migrado:** `google-genai` (nuevo SDK) reemplaza `google-generativeai` (legacy). Sin conflictos de dependencias.
- **Gemini resilience:** Fallback automático sin tools cuando `thought_signature` error ocurre. Historial limpio (sin ToolMessage) antes de reintentar. System prompt instruye a SAM a generar tags `<UPDATE>`/`<LOOT>` inline cuando tools no están disponibles.
- **`langchain-google-genai` 2.1.12:** Soporta `thought_signature` nativamente.

### Completitud: ~90-95%

### Pendiente para "done"
- Auto-creación de perfil para usuarios nuevos (trigger Supabase)
- Generated scene placeholder (tag `<IMAGE>` sin servicio de imágenes conectado)
- Playtest completo con grupo de amigos
- Vercel Root Directory config

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
| **Sin presence indicators** | No se ve quién está online | — |
| **Commlink sin recipients** | No hay lista de jugadores para enviar mensajes | `commlink-dialog.tsx` |
| **Campaign join/invite** | No hay sistema de invitación | — |

## 6. Próximos Pasos Prioritarios

1. ~~**Probar upload PDF end-to-end**~~ — ✅ Completado
2. **Auto-creación de perfil** — Trigger en Supabase o endpoint para que usuarios nuevos no necesiten INSERT manual
3. **Multiplayer extras** — membership table, presence indicators, commlink recipients
4. **Campaign join/invite** — sistema de invitación por código o link
5. **Image generation** — Conectar servicio de imágenes (Imagen 3 o similar) al tag `<IMAGE>`
6. **Tests** — al menos smoke tests para el gameplay loop
7. **Vercel config** — configurar Root Directory → `projects/SAM/frontend`

---
*Última actualización: 25 Mar 2026*
