# S.A.M. — Evaluación Técnica del Proyecto

**Fecha:** 04 Mar 2026 (actualizado)
**Repo:** `Mitiakamara/dungeon-master-ai`
**Último push:** 04 Mar 2026 (8 commits en main, commit `45b9aa7`)

---

## 1. ¿Qué es SAM?

SAM (Storytelling AI Master) es una aplicación web que actúa como **Dungeon Master virtual** para D&D 5e. La idea es que un grupo de jugadores pueda entrar a una sesión, elegir o crear personajes, y jugar una campaña narrada por una IA con personalidad propia — sarcástica, con humor oscuro, que aplica reglas mecánicas (tiradas, combate, loot) mientras mantiene una narrativa coherente.

No es un chatbot genérico con skin de fantasía. SAM tiene:
- **Herramientas mecánicas reales** (apply_damage, apply_healing, give_loot) que modifican el estado del personaje en base de datos
- **Compendio D&D 5e integrado** con búsqueda semántica (spells, monsters, items con embeddings vectoriales)
- **RAG sobre módulos de campaña** — el GM puede subir PDFs de aventuras y SAM los usa como contexto narrativo
- **Sistema de checkpoints** — saves/loads de partida completos (chat + estado de personajes)
- **Mensajería privada** (commlink) entre jugadores, separada del chat principal

---

## 2. ¿Qué está construido?

### Lo que funciona

**Backend (FastAPI — live en Render):**
- `server.py` — `/api/chat`, `/api/roll`, `/api/version`
- AI Brain (`ai.py`) — Gemini Flash + LangChain con tool calling (hasta 3 iteraciones)
- 5 tools funcionales: `search_spells`, `search_monsters`, `search_items`, `apply_damage/healing`, `give_loot`
- Tags especiales: `<UPDATE>`, `<LOOT>`, `<IMAGE>`, `<XP_GAIN>`, `<DM_ROLL>`, `<ACTION>`
- Auth JWT completa via Supabase
- CRUD personajes + import PDF via Gemini
- CRUD campañas + upload módulos PDF → RAG
- Checkpoints (save/load/reset/list via `/cmd`)
- Mensajería privada (commlink backend)
- Scripts de seeding: compendio D&D 5e con embeddings

**Frontend (Next.js 16 — Vercel):**
- Layout 3 paneles responsive
- Chat en tiempo real (Supabase Realtime WebSocket)
- Dice Tray (backend rolls con `secrets.randbelow`, fallback client-side)
- Character Sheet + Create Dialogs
- Parser resiliente de tags (repairJson, orphan recovery, ghost item filter)
- `stripSystemTags()` — tags invisibles al usuario, DM_ROLL preservado con renderer visual
- Commlink (parcial)
- Auth completa + `authenticatedFetch()`

**Base de datos (Supabase PostgreSQL + pgvector):**
- Schema Phase 11 maduro
- Tablas: profiles, campaigns, characters, messages, private_messages, documents, spells, monsters, items, checkpoints
- RPCs: `match_documents`, `match_compendium`
- RLS en todas las tablas
- Embeddings 1536 dims

### Nivel de completitud: ~70-75%

El core gameplay loop single-player está cerrado y testeado: login → crear personaje → chat con SAM → dados → daño/curación/loot/XP → checkpoint. Funcional en producción.

---

## 3. ¿Qué falta?

### 🔴 Bloqueantes — Resueltos ✅

| Issue | Estado |
|-------|--------|
| Deploy backend (Render) | ✅ Corregido — Root Directory `projects/SAM/backend`, live |
| Deploy frontend (Vercel) | ⚠️ Pendiente config manual Root Directory → `projects/SAM/frontend` |

### 🟡 Multiplayer — Gaps críticos

| Gap | Detalle | Esfuerzo |
|-----|---------|----------|
| **Filtro de mensajes por campaña** | `fetchHistory()` no filtra por `campaign_id` — mezcla campañas | Bajo |
| **Selector de campaña** | No hay UI, el usuario no puede elegir campaña | Medio |
| **Header dinámico** | Hardcodeado "La Mina Perdida" | Bajo |
| **Roster de jugadores** | No se ve quién más está en la campaña | Medio |
| **Commlink recipients** | `campaign_id: "FIXME"`, sin picker de destinatarios | Medio |
| **Character creation** | Hardcodea UUID de campaña, no usa la seleccionada | Bajo |
| **Membership table** | No hay concepto formal de "jugadores en campaña" | Medio |
| **Presence** | No se ve quién está online | Medio (Supabase Presence API) |

**Infraestructura backend existente:** `campaign_id` FK en messages, auto-detección por personaje/GM, Realtime broadcast. La base está, falta exponerla en frontend.

### 🟡 Funcionalidad incompleta

| Feature | Estado | Lo que falta |
|---------|--------|-------------|
| **Admin Dashboard** | Placeholder | UI para GM controls |
| **Upload módulos PDF** | Backend listo | Frontend form |
| **Generación de imágenes** | Tags parseados | Integrar servicio de imágenes |
| **Inventario avanzado** | JSONB funciona | UI equipar/usar/gestionar |

### 🔵 Features deseables

| Feature | Valor | Complejidad |
|---------|-------|-------------|
| Combate automatizado (state machine) | Alto | Alta |
| NPC memory/relationships | Medio | Media |
| Spell slots & resources | Medio | Baja |
| Mapas/battlemap | Alto (visual) | Alta |
| Mobile PWA | Alto | Baja |

---

## 4. Apreciaciones técnicas

### Lo que está bien hecho
1. **Stack $0/mes** — Supabase, Render, Vercel, Gemini Flash — todo en free tiers
2. **LangChain tools** — SAM ejecuta acciones reales sobre BD, no solo genera texto
3. **RAG sobre módulos** — diferenciador real vs chatbots genéricos
4. **Auth + RLS sólidas** — JWT, RLS en todas las tablas, sin shortcuts
5. **Schema maduro** — 11 iteraciones, JSONB flexible
6. **Parser resiliente** — repairJson, orphan recovery, ghost item filter, stripSystemTags

### Lo que preocupa
1. **Gemini Flash** puede ser limitante para DM de calidad en sesiones complejas
2. **Cero tests** — un bug puede arruinar una sesión en vivo
3. **Schema sin migraciones formales** — manual y propenso a errores
4. **Sin rate limiting** — `/api/chat` sin throttling
5. **Hardcoded GM fallbacks** — no escala a múltiples GMs

---

## 5. Recomendación actualizada

**Multiplayer es el siguiente milestone natural.** El single-player está probado y funcional. Para que SAM tenga valor real como producto, necesita soporte multiplayer — es lo que lo diferencia de simplemente chatear con una IA.

**Ruta sugerida:**
1. Filtrar mensajes por campaign_id + header dinámico (1 día)
2. Selector de campaña por personaje seleccionado (1 día)
3. Roster: mostrar otros personajes en la campaña (1-2 días)
4. Test multiplayer con 2+ usuarios reales (1 día)
5. Iterar sobre feedback

---

*Evaluación actualizada: 04 Mar 2026 — basada en código en GitHub y playtest single-player exitoso.*
