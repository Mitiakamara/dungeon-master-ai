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
| Embeddings | gemini-embedding-001 (768 dims, truncated) | Google Cloud |
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
- Mensajería privada (commlink) — parcial
- Realtime sync via Supabase WebSocket

### Completitud: ~75-80%

## 5. Análisis Multiplayer

### Infraestructura existente
- `messages` table tiene `campaign_id` FK (NOT NULL)
- Backend auto-detecta campaña via personaje del usuario o propiedad GM
- Supabase Realtime entrega mensajes a todos los conectados
- RLS policies en todas las tablas

### Gaps críticos para multiplayer
| Gap | Detalle | Archivo |
|-----|---------|---------|
| **Sin filtro de campaña en chat** | `fetchHistory()` carga TODOS los mensajes sin `.eq('campaign_id')` | `chat-interface.tsx` |
| **Sin selector de campaña** | No hay UI para elegir campaña | `sidebar-left.tsx` |
| **Sin roster de jugadores** | No se ve quién más está en la campaña | — |
| **Commlink hardcodeado** | `campaign_id: "FIXME_CAMPAIGN_ID"` | `commlink-dialog.tsx` |
| **Character creation hardcodea UUID** | Todas las characters van a la misma campaña | `character-create-dialog.tsx` |
| **Header hardcodeado** | Dice "La Mina Perdida" siempre | `chat-interface.tsx` |
| **Sin membership table** | No hay concepto formal de "jugadores en campaña" | schema |
| **Sin presence indicators** | No se ve quién está online | — |

### Lo que se necesita para MVP multiplayer
1. Filtrar mensajes por `campaign_id` en frontend
2. Selector de campaña en sidebar (o auto-detect por personaje seleccionado)
3. Header dinámico con nombre de campaña
4. Roster: mostrar personajes de otros jugadores en la campaña
5. Commlink: poblar recipients con jugadores de la campaña
6. Campaign join/invite system (código de invitación o link)

## 6. Próximos Pasos Prioritarios

1. **Probar upload PDF end-to-end** — verificar que el PDF se vectoriza y SAM lo usa como contexto RAG
2. **Multiplayer MVP** — filtro de mensajes + selector de campaña + roster
3. **Admin Dashboard** — controles GM funcionales
4. **Tests** — al menos smoke tests para el gameplay loop
5. **Mobile responsive** — verificar y pulir layout en móvil
6. **Vercel config** — configurar Root Directory → `projects/SAM/frontend`

---
*Última actualización: 18 Mar 2026*
