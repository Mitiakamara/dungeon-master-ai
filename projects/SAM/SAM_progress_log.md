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
| Embeddings | text-embedding-004 (1536 dims) | Google Cloud |
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
- Checkpoints (save/load/reset/list)
- Mensajería privada (commlink) — parcial
- Realtime sync via Supabase WebSocket

### Completitud: ~70-75%

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

1. **Multiplayer MVP** — filtro de mensajes + selector de campaña + roster
2. **Admin Dashboard** — controles GM funcionales
3. **Upload módulos PDF** — UI frontend (backend ya listo)
4. **Tests** — al menos smoke tests para el gameplay loop
5. **Mobile responsive** — verificar y pulir layout en móvil

---
*Última actualización: 04 Mar 2026*
