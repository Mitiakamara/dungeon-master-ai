# S.A.M. — Tickets

Sistema de tracking de bugs, features y chores pendientes.

## Convenciones

- **IDs**: `SAM-XXX` secuencial, no se reusan
- **Tipo**: `BUG` | `FEAT` | `REFACTOR` | `CHORE`
- **Prio**: `P0` bloqueante · `P1` alta · `P2` normal · `P3` nice-to-have
- **Estado**: `OPEN` | `IN_PROGRESS` | `BLOCKED` | `DONE`
- Tickets cerrados mantienen su row en la tabla histórica; el detalle se absorbe en `SAM_progress_log.md`

---

## Tabla resumen

| ID | Título | Tipo | Prio | Estado |
|----|--------|------|------|--------|
| SAM-001 | DM_ROLL chips apilados verticalmente | BUG | P1 | DONE |
| SAM-002 | Turn enforcement + Extra Attack | FEAT | P0 | DONE |
| SAM-003 | Sneak Attack modeling | FEAT | P1 | DONE |
| SAM-004 | `/delegate` rechaza rol `admin` | BUG | P2 | DONE |
| SAM-005 | Vex tiene Unarmed Strike incorrecto | BUG | P3 | OPEN |
| SAM-006 | MemoryService trunca JSON de Gemini | BUG | P3 | OPEN |
| SAM-007 | FK violation al crear personaje para usuarios nuevos | BUG | P2 | OPEN |
| SAM-008 | SAM verbosidad ocasional | BUG | P3 | OPEN |
| SAM-009 | Servicio de generación de imágenes (tag `<IMAGE>`) | FEAT | P2 | OPEN |
| SAM-010 | Vercel Root Directory config | CHORE | P3 | OPEN |
| SAM-011 | Commlink Realtime + auto-mark-as-read | FEAT | P2 | OPEN |
| SAM-012 | Quitar console.logs de debug (presence tracking) | CHORE | P3 | OPEN |
| SAM-013 | Narrator inventa números en iniciativa (no respeta DM_ROLL tag) | BUG | P1 | DONE |
| SAM-014 | NPC damage no persiste a `characters.status.hp_current` | BUG | P1 | DONE |
| SAM-015 | DM_ROLL chips de turnos NPC llegan como "Invalid Roll Data" | BUG | P1 | BLOCKED |
| SAM-016 | Extra Attack roto: `has_extra_attack` no matchea `class` con sufijo de nivel ("Barbarian 7") | BUG | P1 | DONE |
| SAM-017 | Narrator SYSTEM_PROMPT explota con KeyError por JSON literal (regresión SAM-013) | BUG | P0 | DONE |
| SAM-018 | Initiative/ataque-delegado modifiers +0 — orchestrator lee `status.stats` en vez de `stats` top-level | BUG | P1 | DONE |
| SAM-019 | Iniciativa manual para jugadores no delegados | DESIGN | P2 | OPEN |
| SAM-020 | Auditoría arquitectónica del sistema (`SAM_audit_2026-06-05.md`) | CHORE | P1 | DONE |
| SAM-021 | Orchestrator no implementa loot/XP/level-up/imágenes (solo en legacy `ai.py`) | REFACTOR | P1 | IN_PROGRESS |
| SAM-022 | COMBAT STATUS muestra HP de jugador stale → drift narrador vs BD/sidebar | BUG | P2 | OPEN |
| SAM-023 | Respuestas de comandos admin duplicadas para el emisor (optimista + Realtime) | BUG | P2 | OPEN |
| SAM-024 | Legacy `<UPDATE>` HP solo client-side + ambigüedad de atribución multiplayer | BUG | P2 | OPEN |
| SAM-025 | Extraer de `ai.py` piezas no-game-loop reusadas (DM style, Supabase client, PDF import, avatares) | REFACTOR | P2 | OPEN |
| SAM-026 | Código muerto: `pending_action` + `<ACTION>RELOAD_CHAT>` no manejado | CHORE | P3 | OPEN |
| SAM-027 | Log/warning cuando un intent llega sin handler mecánico dedicado | CHORE | P3 | OPEN |
| SAM-028 | Unificar shape de `settings.combat` entre legacy y orchestrator | BUG | P2 | OPEN |
| SAM-029 | Aplicar `state_updates` por `character_id` en vez de por `name` | REFACTOR | P2 | DONE |
| SAM-030 | Incluir `stats` en `_format_character_context` (gap narrator RULE 15) | CHORE | P3 | OPEN |
| SAM-031 | Gate `debug_log.txt` por env DEBUG (no I/O en hot-path) | CHORE | P3 | OPEN |
| SAM-032 | Retry/backoff para `RemoteProtocolError` httpx (Gemini/Supabase) | CHORE | P3 | OPEN |
| SAM-033 | Narrator alucina combate completo (rolls/daño/HP) sin mechanical facts | BUG | P1 | DONE |
| SAM-034 | No existe forma de terminar el turno voluntariamente | BUG | P1 | DONE |
| SAM-035 | skill_check en combate no consume acción → acciones infinitas | BUG | P2 | DONE |
| SAM-036 | Daño de PC delegado a NPC se emite como `player_hp` → nunca baja el HP del NPC | BUG | P0 | DONE |
| SAM-037 | Combate inactivo persiste `{"active": False}` descartando `initiative_order` → NPC revive a HP completo | BUG | P1 | DONE |
| SAM-038 | Instrumentación: logging de HP de NPC, transiciones de combate y descarte de estado | CHORE | P1 | DONE |
| SAM-039 | Weapon mismatch en el flow de ataque — pending toma un arma distinta a la declarada | BUG | P1 | DONE |
| SAM-040 | Estado de delegación invisible para el jugador | UX | P2 | DONE |
| SAM-041 | Declaraciones de acción producen facts vacíos → narrator de roleplay niega el ataque (deadlock) | BUG | P0 | DONE |
| SAM-042 | Crítico no duplica dados de daño — `_get_roll_prompt` ignora el flag `critical` del pending | BUG | P1 | DONE |
| SAM-043 | Monster lookup no matchea nombres en español ("lobo" ≠ "Wolf") → fallback genérico infla XP/loot | BUG | P3 | OPEN |
| SAM-044 | `state_updates` múltiples al mismo personaje se pisan entre sí (read-modify-write no consolidado en server.py) | BUG | P1 | DONE |
| SAM-045 | Attack rolls aceptan cualquier cantidad de d20 (3d20/4d20) — falta validar cantidad | BUG | P2 | DONE |
| SAM-046 | Unarmed Strike con daño fijo ("5"/"1d1") rompe prompt y validación — tratar como 1d4+STR | BUG | P2 | DONE |
| SAM-047 | Auditoría de multiplayer pre-playtest grupal (`SAM_audit_multiplayer_2026-06-11.md`) | CHORE | P1 | DONE |
| SAM-048 | Comandos admin sin verificación de rol server-side; `/reset` no-GM = nuclear wipe sin scope de campaña | BUG | P1 | OPEN |
| SAM-049 | Pendings sin validación de dueño fuera de combate → cualquier jugador consume el pending ajeno | BUG | P1 | SUPERSEDED |
| SAM-050 | Doble envío: INSERT de mensaje pre-lock + lock sin timeout + retry del cliente a 30s | BUG | P2 | OPEN |
| SAM-051 | Atribución por primer personaje del usuario (`limit 1`) — `/api/chat` sin `character_id` explícito | REFACTOR | P2 | IN_PROGRESS |
| SAM-052 | Roster del party con HP congelado (fetch único, sin Realtime) + subscripciones sin filtro de campaña | UX | P2 | OPEN |
| SAM-053 | Tirada sin pending se resuelve en el LLM: `freeform_roll` → facts vacíos → `narrate_roleplay` | BUG | P0 | DONE |
| SAM-054 | Regla 15 del narrator licencia al LLM a calcular totales de skill check | BUG | P0 | DONE |
| SAM-055 | `attacks[0]` como default silencioso en 3 sitios; sin marca de "no resuelto" ni log en el freeform | BUG | P1 | OPEN |
| SAM-056 | `_handle_start_combat` descarta `intent["weapon"]` | BUG | P1 | OPEN |
| SAM-057 | Pending pegajoso: roleplay no reemplaza, `end_combat` no limpia, sin TTL/round stamp | BUG | P1 | OPEN |
| SAM-058 | El fact de INVALID DICE no ofrece salida al jugador | FEAT | P1 | OPEN |
| SAM-059 | Ventaja/desventaja toma `rolls[0]` en vez de max/min | BUG | P1 | DONE |
| SAM-060 | Interpreter sin glosario ES→EN de armas ("mandoble" → Greataxe) | BUG | P1 | OPEN |
| SAM-061 | Sin soporte de N instancias del mismo NPC (nombres únicos, targeting, `resolve_npc_turn`) | FEAT | P2 | OPEN |
| SAM-062 | Healing sin validación de dados ni gate de inventario | BUG | P2 | OPEN |
| SAM-063 | Observabilidad: `metadata.engine`, log del freeform pending, fact visible para el reject de SAM-049 | CHORE | P2 | DONE |
| SAM-064 | El narrator puebla escenas con enemigos que no existen en combat state | BUG | P3 | OPEN |
| SAM-065 | Trackeo real de ventaja/desventaja (hoy se asume ventaja ante 2d20) | FEAT | P2 | OPEN |
| SAM-066 | Observabilidad: estampar `metadata.engine` (orchestrator/legacy) en los mensajes de SAM | CHORE | P3 | OPEN |
| SAM-067 | Frontend envía `campaign_id` en `/api/chat`; quitar la inferencia `limit(1)` del backend | FEAT | P1 | OPEN |

> SAM-053–064 salieron del diagnóstico post-playtest multijugador (instrucción 235). SAM-066/067 de la instrucción 239. Detalle en `SAM_progress_log.md`.

> Detalle completo de SAM-018, SAM-021–032 en `SAM_audit_2026-06-05.md` (auditoría SAM-020). SAM-019 estuvo reservado hasta la instrucción 224, donde se asignó a iniciativa manual (decisión de diseño revisada post-playtest).

---

## Detalle — Tickets activos

### SAM-004 — `/delegate` rechaza rol `admin`

**Tipo:** BUG · **Prio:** P2 · **Estado:** DONE · Instrucción 239 (verificar con cuenta admin en el próximo playtest)

Usuarios con rol `admin` (no GM) reciben "No active campaign found for GM" al intentar `/delegate`. El resolver solo acepta `gm_id` como dueño de campaña.

**Resuelto (239 A3):** no existía un helper "es GM o admin" — el único era `verify_admin` en `invitations.py` (solo rol). Nuevo `app/core/access.py` (`is_admin`, `is_gm`, `is_gm_or_admin`, `has_character_in_campaign`, `can_access_campaign`); `verify_admin` delega ahí. `AdminService.handle_command` recibe el `campaign_id` que `/api/chat` resolvió y `_find_character_in_active_campaign(name, user_id, campaign_id)` lo acepta si `is_gm_or_admin`; sin campaña o sin derechos cae al lookup legacy por `gm_id`. Un admin sin personaje ni GM-ship solo queda cubierto cuando el frontend mande `campaign_id` (SAM-067).

---

### SAM-005 — Vex tiene Unarmed Strike incorrecto

**Tipo:** BUG · **Prio:** P3 · **Estado:** OPEN

El PDF import de Vex dejó "Unarmed Strike" como uno de sus ataques principales. Debería ser solo Rapier (melee) + Hand Crossbow (ranged) + Fire Bolt (cantrip racial). Unarmed Strike contamina el fallback de `_build_combatant_from_character`.

**Archivos afectados:** dato en DB (`characters.status.attacks` de Vex), o lógica de filtrado en `backend/agents/orchestrator.py` (`_build_combatant_from_character`).

**Criterio de done:** Vex nunca ataca con Unarmed Strike cuando hay delegación activa.

---

### SAM-006 — MemoryService trunca JSON de Gemini

**Tipo:** BUG · **Prio:** P3 · **Estado:** OPEN

Gemini corta el JSON de memorias generadas en el fire-and-forget del MemoryService. El parser falla silenciosamente. Low-impact (es background), pero genera ruido en logs.

Log ejemplo: `MemoryService: failed to parse JSON (Unterminated string starting at: line 1 column 152)`.

**Archivos afectados:** `backend/services/memory_service.py`.

**Criterio de done:** el servicio recupera al menos las memorias completas parseables cuando el JSON llega truncado, o aumenta `max_output_tokens` lo suficiente para evitar el corte.

---

### SAM-007 — FK violation al crear personaje para usuarios nuevos

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN · Instrucción 238

El progress log del 18 Mar 2026 reporta resuelto via trigger `handle_new_user` (migration 006). Pre-vuelo de solo lectura del 6 Sep 2026 (instrucción 238) contra la instancia:

- **Huérfanos (`auth.users` sin `public.profiles`): 1** — `96d231b2-f734-44e5-ad34-ece13ed23544`, `fcorrea@flexflow8.com`, provider `google`, creado 2026-01-21. Es anterior a la migration 006 (Mar 2026), así que no prueba que el trigger falle: prueba que el backfill manual de enero (`INSERT profiles`, progress log) no cubrió esta cuenta. Hoy esa cuenta no puede crear personaje (`app/routers/characters.py:116`, FK `characters.user_id → profiles(id)` en `schema_game_engine.sql:7`) y el INSERT de sus mensajes de chat falla con WARNING (`server.py:318-329`, FK `messages.sender_id → profiles(id)`).
- **Trigger `on_auth_user_created` / función `handle_new_user`:** existencia y `prosrc` en la instancia **pendientes de verificar** (queries 1 de la instrucción 238, sin resultado aún). El repo los define en `backend/schema_invitations.sql:51-70`; no hay runner de migraciones, así que el código no puede confirmar que estén aplicados.
- **Key del backend:** `SUPABASE_KEY` es `service_role` (claim del JWT). El comentario "should be the ANON key" en `app/core/security.py:10` está desactualizado. RLS no interviene en los inserts del backend; el fallo es la FK, no la policy.
- **Superficie:** los dos caminos que crean filas en `auth.users` — `invitations.py:171-176` (signup con código) y Google OAuth en `frontend/components/profile-menu.tsx:85-90` — dependen 100% del trigger; ninguno inserta en `profiles`.

**Criterio de done:** trigger verificado en la instancia con cuerpo idéntico al del repo, huérfanos = 0 (backfill de la cuenta listada), y un usuario recién registrado crea un personaje sin FK violation. Nada se aplica en Supabase sin instrucción explícita.

---

### SAM-008 — SAM verbosidad ocasional

**Tipo:** BUG · **Prio:** P3 · **Estado:** OPEN

Narrator tiene límite de 120 palabras / 2 párrafos pero no siempre lo respeta. Empeora en combate y descripciones ambientales.

**Archivos afectados:** `backend/agents/narrator.py` (SYSTEM_PROMPT).

**Criterio de done:** mensajes promedio bajo 100 palabras en sesiones de prueba. Puede requerir truncado hard en backend como fallback.

---

### SAM-009 — Servicio de generación de imágenes

**Tipo:** FEAT · **Prio:** P2 · **Estado:** OPEN

El tag `<IMAGE>` se parsea y limpia pero no conecta a un servicio real. Imagen 3 / Imagen 4 disponibles via Gemini API.

**Archivos afectados:** nuevo módulo `backend/services/image_service.py`, integración en `backend/server.py` o pipeline del orchestrator, renderer en frontend.

**Criterio de done:** SAM puede generar una imagen de escena/personaje/item cuando emite `<IMAGE>`, la imagen se guarda en Supabase Storage y se muestra inline en el chat.

---

### SAM-010 — Vercel Root Directory config

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

Configurar manualmente en Vercel dashboard: Root Directory → `projects/SAM/frontend`. Actualmente funciona pero requiere esta config para el monorepo.

**Criterio de done:** deploy de Vercel toma como root el frontend, no la raíz del workspace.

---

### SAM-011 — Commlink Realtime + auto-mark-as-read

**Tipo:** FEAT · **Prio:** P2 · **Estado:** OPEN

Commlink actualmente requiere refresh manual para ver nuevos mensajes privados. Falta suscripción Realtime. Además, al abrir un hilo los mensajes no se marcan como leídos automáticamente.

**Archivos afectados:** `frontend/components/commlink-dialog.tsx`, posible endpoint de mark-read en `backend/routes/messages.py`.

**Criterio de done:** mensajes privados aparecen en tiempo real sin refresh; abrir un hilo marca los mensajes como leídos.

---

### SAM-012 — Quitar console.logs de debug

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

Quedan `console.log` de debugging especialmente alrededor del presence tracking (`🟢 Presence:`, etc.) que ensucian la consola del browser.

**Archivos afectados:** `frontend/components/party-roster.tsx`, `frontend/components/game-layout.tsx` u otros.

**Criterio de done:** consola del browser en producción limpia de logs manuales de debug.

---

### SAM-040 — Estado de delegación invisible para el jugador

**Tipo:** UX · **Prio:** P2 · **Estado:** DONE · Instrucción 234 (badge en roster)

La delegación (`/delegate`) persiste en DB (`controlled_by`) y sobrevive a `/reset`. En el playtest 2026-06-11 Vex actuó como delegada de una sesión anterior sin que el jugador lo supiera ni pudiera verlo en ningún lado.

**Resuelto (instrucción 234) — opción (a), badge en el roster:** `party-roster.tsx` muestra un chip "🤖 SAM" (con `title="Controlado por S.A.M. (delegado)"`) junto a cada personaje con `controlled_by` truthy. **Hallazgo de verificación:** el endpoint `/api/characters/campaign/{id}` devolvía `List[CharacterResponse]` que **stripeaba `controlled_by`** (no estaba declarado en el modelo) → se agregó `controlled_by: Optional[str] = None` a `CharacterResponse` (`characters.py`), por lo que SAM-040 necesitó un cambio mínimo de backend además del frontend (dos deploys: Render + Vercel, un commit). **Sync:** el roster hace un fetch al montar — suficiente porque la delegación solo cambia con `/delegate`/`/undelegate` (refresh tras el comando); live updates quedan para SAM-052 (roster Realtime). **Scope:** el badge cubre a los OTROS PCs del roster (el caso del playtest: ver que Vex está delegada); el propio PC del jugador se filtra del roster — su badge en el mini-sheet propio quedaría para una iteración aparte. Las opciones (b) facts de inicio de combate y (c) `/reset` report no se implementaron (el badge cubre el criterio).

**Criterio de done:** ✅ un jugador ve en <5 segundos qué personajes del party controla SAM.

---

### SAM-019 — Iniciativa manual para jugadores no delegados

**Tipo:** DESIGN · **Prio:** P2 · **Estado:** OPEN (reabierto en instrucción 224; ID estaba reservado)

Decisión revisada por el director tras playtests: el auto-roll de iniciativa se aprobó en teoría pero en la mesa se siente mal — el jugador quiere tirar su propia iniciativa.

**Diseño objetivo:** al iniciar combate, SAM rolea iniciativa SOLO de NPCs y PCs delegados; a los jugadores reales les pide su tirada (d20, el dex mod lo suma el sistema). El combate arranca cuando todas las iniciativas están registradas.

**Complejidad a evaluar:** requiere un estado intermedio de combate ("esperando iniciativas") en `CombatState`, con pending de iniciativa por jugador. No trivial — estimar antes de implementar.

**Archivos:** `combat_state.py`, `orchestrator.py` (`_handle_start_combat`), prompts de interpreter/narrator.

---

### SAM-015 — DM_ROLL chips de turnos NPC llegan como "Invalid Roll Data"

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017) — reconciliado por auditoría SAM-020

**Reconciliación (auditoría 5 Jun):** confirmado el **formato dual de `<DM_ROLL>`**. El orchestrator emite JSON (`orchestrator.py:508,816,833`); el legacy `ai.py` instruye al LLM a emitir **texto libre/breakdown** (`ai.py:87,93,220`). El frontend hace `JSON.parse` (`chat-interface.tsx:740`) → si falla, renderiza `[Invalid Roll Data]` (`:782,796`). El texto libre del screenshot nace en el legacy → bajo fallback (SAM-017) todos los DM_ROLL de NPC fallan el parse.

**Criterio de done:** se resuelve al no caer al legacy (SAM-017). *Defensivo opcional:* hacer `parseRoll` tolerante a texto libre (mostrar el texto crudo en vez de `[Invalid Roll Data]`).

---

### SAM-021 — Orchestrator no implementa loot/XP/level-up/imágenes

**Tipo:** REFACTOR/BUG · **Prio:** P1 · **Estado:** IN_PROGRESS — **fase 1/3 DONE** (XP/level-up, commit `d7aa6fb`, instrucción 225, validada en prod) · **fase 2/3 DONE — VALIDADA COMPLETA** (loot híbrido, commit `31b29f1`; SAM-044 resuelto en instrucción 230). Playtest 2026-06-11: oro+XP+ítem persisten juntos (💾 Status flushed único por PC), y **killer tracking confirmado** — Vex dio el golpe final → Vex recibió el ítem (atribución por killer real, no por default). Pendiente: **solo fase 3 imágenes (SAM-009)**.

Hallazgo principal de la auditoría SAM-020. El pipeline nuevo no portaba features del legacy: `mechanic.award_xp` existía pero nunca se llamaba; `give_loot` solo está en tools legacy; el narrator tiene prohibido emitir `<LOOT>/<XP_GAIN>/<EVENT>/<IMAGE>` (`narrator.py:39`). Esas features solo viven en `ai.py`, alcanzado solo por excepción. **Subsume SAM-009** (servicio de imágenes).

**Fase 1 implementada (XP/level-up):** muerte de NPC → `combat.defeated_this_request` (snapshot en `update_npc_hp`, transiente) → el orchestrator otorga XP ANTES de narrar (`award_xp` arreglado: lee `status.xp`, divide con ceil, calcula HP de level-up por clase+CON) → server.py solo persiste valores precalculados (XP a `status.xp`, `level`, HP, sufijo del class string). Logs `⭐ XP` / `🎉 LEVEL UP`. `xp_value` estampado en combatants desde `_lookup_monster` con fallback por CR (`get_xp_for_cr` acepta '1/2'). **Validada en prod** (playtest 2026-06-11: logs, narración y `status.xp=350` en ambos PCs).

**Fase 2 implementada (loot híbrido — Python presupuesta, Gemini describe):** mismo hook de `defeated_this_request`. `get_loot_budget(cr)` (rules.py) rolea el oro por banda de CR (2d6 → 8d6x10) y fija slots/rareza de ítems (trinket/common/uncommon — nunca armas/stats). El LLM liviano solo NOMBRA los ítems (`LOOT_ITEM_PROMPT`, JSON validado por Python: malformado → fallback "{Monster} Trophy", overflow → truncado a los slots). Oro al party (ceil, `money_award` → `status.money.gp`); ítems al PC del golpe final (`killer` threaded por `update_npc_hp` desde los 4 kill sites, `item_award` → `status.inventory` shape `{item, qty, description}`). Persistencia server-side (evita el defecto client-side de SAM-024); el parser `<LOOT>` legacy queda para el fallback. Facts "LOOT:"/"LOOT ITEM:" precalculados antes de narrar; RULE 16 prohíbe inventar loot extra.

**Validación PARCIAL (playtest 2026-06-11, instrucción 229):** logs `💰 Loot: Björn +17 gp` / `💰 Loot: Vex +17 gp` y `🎁 ... Smooth River Stone` al killer (Björn, golpe final correcto); narración completa en orden muerte → XP → oro → ítem. El ítem **sí** llegó al inventario del frontend. **PERO el oro NO aparece en el wallet de Björn.** Query a prod: Björn `money.gp=0, xp=0` (con el Smooth River Stone en inventory); Vex `money.gp=17, xp=0`. → confirma **SAM-044** (los `state_updates` al mismo personaje se pisan entre sí: para Björn, `item_award` pisó el write de `money_award` y de `xp_update`; doble confirmación vía `xp=0` en ambos, sin que hubiera `/reset` — Vex conserva 17 gp). **No cerrar la fase 2 hasta resolver SAM-044.**

**Criterio de done (fases restantes):** encontrar tesoro persiste loot en inventario (fase 2); SAM puede generar imágenes (fase 3) — todo sin depender del fallback legacy. Detalle en `SAM_audit_2026-06-05.md` §1, §5.

---

### SAM-022 — COMBAT STATUS muestra HP de jugador stale (drift narrador vs BD)

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

El overlay de HP de jugador en el bloque `COMBAT STATUS` (`orchestrator.py:856-868` y `:319-329`) lee `party_characters[].status.hp_current` = snapshot del inicio del request (`server.py:247`), ANTES de que el `state_update` de este turno se persista (`server.py:293` corre después de `process_message`). Resultado: el narrador ve HP viejo en COMBAT STATUS pero HP nuevo en el fact `damage_applied`; RULE 16 lo manda a citar COMBAT STATUS → narra el viejo. Tras F5, el sidebar lee BD = nuevo → mismatch narrativo↔sidebar. Residual de SAM-014, independiente de SAM-017.

**Evidencia adicional (playtest 2026-06-11):** SAM narró "su HP bajando a 35/50" tras el hit, ANTES del damage roll (el HP real baja recién en el damage). Drift cosmético, sigue P2.

**Criterio de done:** el bloque COMBAT STATUS refleja el HP post-daño (leído de los resultados del engine / `state_updates`, no de `party_characters` stale). Detalle en `SAM_audit_2026-06-05.md` §4.

---

### SAM-023 — Respuestas de comandos admin duplicadas para el emisor

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

`server.py:159-168` inserta la respuesta admin en `messages` (→ Realtime INSERT) y además la retorna al frontend; el frontend hace **append optimista** del `data.response` **sin `id`** (`chat-interface.tsx:693-701`). Cuando llega el Realtime INSERT con `id` real, la dedup `prev.some(m => m.id === incomingMsg.id)` no matchea (el optimista tiene `id=undefined`) → se agrega de nuevo → **duplicado**. Afecta `/delegate`, `/undelegate`, `/gold`, `/memory` (`/reset` se exime, `/load` se enmascara con su reload).

**Criterio de done:** eliminar el append optimista de comandos admin (confiar solo en Realtime, como el chat normal) o estampar un `id` compartido. Detalle en `SAM_audit_2026-06-05.md` §7.

---

### SAM-024 — Legacy `<UPDATE>` HP solo client-side + ambigüedad multiplayer

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

Bajo fallback legacy, `server.py` ignora los `updates` que retorna `generate_response` (`ai.py:480`); el HP depende del `<UPDATE>` parseado **client-side** (`chat-interface.tsx:253-275`) y se aplica al `selectedCharacter` del **espectador**, sin atribución de personaje. En multiplayer, si SAM daña al jugador A, la pantalla del jugador B aplicaría el `<UPDATE>` a su propio personaje.

**Criterio de done:** mitigado si se deprecia el legacy (SAM-025) o se porta todo al orchestrator (SAM-021). Mientras el legacy exista, evaluar atribución del `<UPDATE>`. Detalle en `SAM_audit_2026-06-05.md` §1, §4.

---

### SAM-025 — Extraer de `ai.py` piezas no-game-loop reusadas

**Tipo:** REFACTOR · **Prio:** P2 · **Estado:** OPEN

El orchestrator depende del legacy: `sam_brain.supabase` (cliente Supabase usado por todo `server.py` y `KnowledgeService`), `_build_dm_style` (`server.py:260`), `parse_character_pdf` + avatares (`characters.py:71`). No se puede deprecar `generate_response` sin extraer esto a módulos neutrales.

**Criterio de done:** `_build_dm_style` → `services/style.py`; cliente Supabase → `core/supabase.py`; PDF import + avatares → `services/character_import.py`. Recién entonces evaluar deprecación del game-loop legacy. Precondición de SAM-021. Detalle en `SAM_audit_2026-06-05.md` §5.

---

### SAM-026 — Código muerto: `pending_action` + `<ACTION>RELOAD_CHAT>`

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

`pending_action`/`set_pending_action`/`clear_pending_action` (`combat_state.py:119-125`) nunca se invocan; siempre vale `None`; `turn_is_over` (`:88-90`) depende de eso. Coexiste con el `pending_player_roll` vivo (confusión de nombres). Además, `/load` emite `<ACTION>RELOAD_CHAT</ACTION>` (`admin.py:172`) que el frontend nunca maneja.

**Nota 239 (B10):** `turn_is_over()` SÍ tiene un caller — `orchestrator.py` en el bloque de `dice_roll` (`if combat.turn_is_over():` antes de `_resolve_npc_turns`) — así que no se tocó nada de `combat_state.py`. Como `pending_action` es siempre `None`, hoy equivale a `actions_remaining <= 0`. Se resuelve aparte.

**Criterio de done:** eliminar `pending_action` y helpers muertos; simplificar `turn_is_over` a `actions_remaining <= 0`; remover/implementar `RELOAD_CHAT`. Detalle en `SAM_audit_2026-06-05.md` §1, §3.

---

### SAM-027 — Warning cuando un intent llega sin handler mecánico

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

Agregar un intent nuevo al interpreter sin handler en el orchestrator cae silenciosamente al grupo de narración (`orchestrator.py:253`). No hay log de "intent sin handler". `ability` y `movement` hoy son narración-only (sin resolución mecánica).

**Criterio de done:** log defensivo cuando un intent no tiene handler dedicado. Opcional: resolución mecánica básica de `ability`. Detalle en `SAM_audit_2026-06-05.md` §2.

---

### SAM-028 — Unificar shape de `settings.combat` legacy vs orchestrator

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

El legacy escribe `settings.combat` con shape distinto al de `CombatState.to_dict()` (sin `actions_remaining`/`current_turn_index`; `initiative_order` viene del LLM, `server.py:425-427`). Si un mensaje cae al legacy a mitad de combate y el siguiente vuelve al orchestrator, `CombatState.from_dict` lee estado inconsistente (p.ej. `actions_remaining=0` → `turn_is_over` inmediato).

**Criterio de done:** unificar el shape o impedir que el legacy escriba `settings.combat` cuando el orchestrator es dueño del combate. Mitigado si se deprecia el legacy. Detalle en `SAM_audit_2026-06-05.md` §3.

---

### SAM-030 — Incluir `stats` en `_format_character_context`

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

`_format_character_context` (`orchestrator.py:970-982`) no incluye los ability scores → el narrador no puede responder preguntas de stats con exactitud, aunque RULE 15 (`narrator.py:46`) promete lo contrario.

**Criterio de done:** el contexto del narrador incluye STR/DEX/CON/INT/WIS/CHA. Detalle en `SAM_audit_2026-06-05.md` §6.

---

### SAM-031 — Gate `debug_log.txt` por env DEBUG

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

`ai.py:418` (cada respuesta legacy) y `:507` (cada import PDF) escriben `debug_log.txt`. En Render (FS efímero) crece sin rotación y es I/O en el hot-path.

**Criterio de done:** escritura condicionada a una env var `DEBUG`; sin I/O de disco en producción por defecto. Detalle en `SAM_audit_2026-06-05.md` §8.

---

### SAM-032 — Retry/backoff para `RemoteProtocolError` (httpx)

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

`RemoteProtocolError` de httpx (transporte Gemini/Supabase) no tiene manejo dedicado → burbujea al `except` genérico (`ai.py:484`, `server.py:476`) y el usuario ve "SYSTEM ERROR". Es transitorio.

**Criterio de done:** retry con backoff corto en las llamadas Gemini/Supabase antes de degradar a error de usuario. Detalle en `SAM_audit_2026-06-05.md` §8.

---

### SAM-048 — Comandos admin sin verificación de rol server-side

**Tipo:** BUG/SEC · **Prio:** P1 · **Estado:** OPEN

Auditoría SAM-047 §7. El frontend bloquea `/reset|/checkpoint|/load|/list` para no-GM (`chat-interface.tsx:593-599`) pero es **client-side only**: ni el interceptor (`server.py:149-182`) ni `AdminService.handle_command` verifican rol. Un `/reset` de un no-GM vía API saltea el pass 1 (resuelve por `gm_id` → vacío) y dispara el pass 3 "nuclear" que **borra TODOS los mensajes** (`admin.py:209-215`). Además la curación de `/reset` recorre **todos los personajes de la BD sin filtro de campaña** (`admin.py:181-191`, resetea money/XP de todos) — incluso para el GM legítimo. `/checkpoint` snapshotea sin filtro; `/load` borra/restaura por `user_id`.

**Criterio de done:** verificación de GM server-side en el interceptor; `/reset`/`/checkpoint`/`/load` scoped a la campaña del GM; eliminar (o scoping estricto de) el pass 3 nuclear. **Mitigación pre-playtest:** brief a Fekas — no usar comandos `/`.

---

### SAM-049 — Pendings sin validación de dueño fuera de combate

**Tipo:** BUG · **Prio:** P1 · **Estado:** SUPERSEDED by per-character pending (instrucción 239) · antes DONE en la 234

**Superseded (239):** la comparación por nombre de `process_player_roll` fue eliminada. Con `pending_rolls` keyed por `character_id`, `process_player_roll` solo ve el slot del roller (`get_pending(character["id"])`): un dado ajeno no encuentra pending y sale como `ORPHAN ROLL`, con fact; el slot del dueño ni se toca. Desaparece también el hueco "owner vacío" (`set_pending` siempre estampa). `test_sam049.py` borrado — sus escenarios viven en `tests/test_pending_rolls.py` (b, c) salvo S5 "ownerless lenient", que ahora es exactamente el comportamiento prohibido.

Auditoría SAM-047 §6 (hallazgo principal). `pending_player_roll` es uno por campaña; la validación de propiedad vive solo en el turn guard, que corre **solo si `combat.active`** (`orchestrator.py:83`). Fuera de combate (skill checks de exploración, hechizos, pociones), **cualquier dado de cualquier jugador consume el pending ajeno**: Björn pide Perception → Fekas tira un d20 → el check de Björn se resuelve con los modificadores de Fekas. Con dos humanos explorando esto ocurre en los primeros minutos. Además los pendings de spell (`process_spell`, `_resolve_spell_attack`) no estampan `character_name` (sin dueño).

**Fix propuesto:** `process_player_roll` valida `pending.character_name` contra el personaje que tira, SIEMPRE; mismatch → el dado se procesa como `freeform_roll` del que tiró y el pending ajeno queda intacto. Estampar `character_name` en los pendings de spell.

**Criterio de done:** con un pending de Björn activo (en o fuera de combate), un dado de Fekas NO lo consume; el pending sobrevive y Björn puede resolverlo después.

**Resuelto (instrucción 234):** `process_player_roll` valida `owner = pending.character_name` vs `roller = character.name` (normalizado case/space) ANTES de validar dados; mismatch → `freeform_roll` del que tiró, pending intacto, log `🚫 Roll by X ignored — pending belongs to Y`. Estampado `character_name` en los pendings que faltaban: `spell_damage`/`spell_attack` (process_spell), `spell_damage` (_resolve_spell_attack), `healing` (orchestrator item). Pendings sin dueño quedan lenient (compat). Tests `test_sam049.py`: 11 checks (combate y exploración, Fekas no consume el pending de Björn, match normalizado, ownerless lenient, spell owner). Sin regresión en 039/042/044/045/046.

---

### SAM-050 — Doble envío: INSERT pre-lock + lock sin timeout + retry a 30s

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

Auditoría SAM-047 §1. El INSERT del mensaje de usuario ocurre antes del lock (`server.py:133-146`) sin idempotencia; el lock espera sin tope; el cliente aborta a 30s y ofrece "Reintentar" → el retry inserta el mensaje de nuevo y SAM responde dos veces. Con dos jugadores encolando tras un request lento del LLM, la ventana es real. **Nota:** el lock es in-process (`asyncio.Lock`, `server.py:82-88`) — correcto con 1 instancia; si Render escala a 2+ instancias/workers se necesita lock distribuido (advisory lock de Postgres).

**Nota 239:** sin cambios. El lock sigue siendo in-process, aceptado para 1 worker. Diagnóstico 237 agregó que `process_message` es síncrono y bloquea el event loop durante el LLM (serialización global de facto).

**Criterio de done:** un retry del cliente no duplica el mensaje ni la respuesta (idempotencia o INSERT dentro del lock con dedup), o el lock responde "SAM está ocupado" antes del timeout del cliente.

---

### SAM-051 — Atribución por primer personaje del usuario (`limit 1`)

**Tipo:** REFACTOR · **Prio:** P2 · **Estado:** IN_PROGRESS · backend listo en la instrucción 239, falta SAM-067

Auditoría SAM-047 §5. `/api/chat` no recibe `character_id`/`campaign_id`; el backend toma el **primer** personaje del usuario (`server.py:117`, `limit(1)`) para derivar campaña y sender_name. Con un usuario multi-personaje (p.ej. dos campañas), la atribución puede salir del personaje equivocado. Inocuo para el playtest (1 personaje por humano).

**Avance (239 A1-A4):** `ChatRequest.campaign_id` opcional; si viene, acceso validado (`can_access_campaign` → 403) y `char_name`/`char_ctx` resueltos DENTRO de esa campaña (nunca un personaje de otra campaña; sin personaje → GM mode con ctx vacío). Si no viene, inferencia `limit(1)` con `WARNING: campaign_id inferido, frontend desactualizado`. Se cierra cuando el frontend lo mande y se quite la inferencia (SAM-067).

**Criterio de done:** el frontend manda `character_id` (ya lo tiene en `selectedCharacter`); el backend valida pertenencia y atribuye por ese personaje, con fallback al comportamiento actual.

---

### SAM-052 — Roster del party con HP congelado + subscripciones sin filtro

**Tipo:** UX · **Prio:** P2 · **Estado:** OPEN

Auditoría SAM-047 §4/§9. El party roster hace UN solo fetch al montar (`party-roster.tsx:34-52`) — sin Realtime ni re-fetch → el HP del compañero queda congelado al cargar (Björn no ve bajar el HP de Fekas sin F5). La suscripción global de `characters` en `game-layout.tsx:136-164` recibe esos updates pero los descarta (solo mira el selectedCharacter). Además las subscripciones de `characters` y `campaigns` no tienen `filter` → cada browser recibe eventos de todas las campañas (ruido + payloads ajenos).

**Criterio de done:** el roster refleja el HP del compañero en vivo (reusar la suscripción de characters con filtro por campaña, o re-fetch on SAM message); subscripciones filtradas por campaña. La presencia (punto verde) ya es live — no tocar.

---

### SAM-055 — `attacks[0]` como default silencioso en tres sitios

**Tipo:** BUG · **Prio:** P1 · **Estado:** OPEN

Diagnóstico 235, Áreas 2 y 3. Tres caminos arman un pending de ataque con `attacks[0]` cuando no pueden resolver el arma: `_handle_attack` cuando `_find_weapon` falla (`orchestrator.py:975`, con warning), y las dos ramas de `_setup_combat_freeform_pending` (`orchestrator.py:534-546` d20, `547-570` no-d20, **ambas sin log**). Como `attacks[0]` de Björn es Unarmed Strike y el de Vex es Fire Bolt, un fallo de resolución se ve como una acción plausible. `_effective_damage` (`mechanic.py:881-899`) no distingue "el arma ES Unarmed" de "no pude resolver" — no existe marca de fallo en ningún lado, y normaliza el daño fijo `"5"` a `1d4+STR`, cerrando el enmascaramiento.

**Criterio de done:** ningún sitio usa `attacks[0]` como fallback; se reusa la última arma usada por ese personaje y, si no hay, se pregunta. Todo fallback deja log.

---

### SAM-056 — `_handle_start_combat` descarta `intent["weapon"]`

**Tipo:** BUG · **Prio:** P1 · **Estado:** OPEN

Diagnóstico 235, Área 2. `_handle_start_combat` (`orchestrator.py:588-697`) lee solo `intent["target"]` (línea 595) y tira el arma declarada. El jugador escribe "Ataco al primer gigante con mi great sword", arranca el combate y no queda pending — su siguiente d20 cae en el freeform y sale Unarmed Strike (13-ago 15:33→15:34).

**Criterio de done:** `start_combat` arma el pending de ataque con el arma declarada, o deja constancia de por qué no puede.

---

### SAM-057 — Pending pegajoso

**Tipo:** BUG · **Prio:** P1 · **Estado:** OPEN

Diagnóstico 235, Área 3. Un pending vivo solo se reemplaza si el intent siguiente es `attack`/`spell`/`skill_check`/`item`/`self_damage`; `roleplay`/`movement`/`free_action`/`ability` lo dejan intacto (`orchestrator.py:317-331`) y se re-persiste (`472-473`). `end_turn` es la única salida explícita, y solo en combate. `end_combat` (`combat_state.py:144-152`) tampoco lo limpia: el pending vive en el engine y se re-adjunta al `{"active": False}`. Si `_out_of_actions` o el turn guard bloquean la declaración nueva, esta ni llega a `process_attack` y el pending viejo sobrevive. Fekas quedó seis turnos bloqueada (17-ago 14:01→14:06). La campaña quedó con un pending de Unarmed Strike 1d4+4 colgado ocho días.

**Nota 239:** con slots por personaje, un pending pegajoso ya no bloquea a los demás (Fekas no pudo haber quedado bloqueada por el slot de Björn) ni congela el avance de turno ajeno. El slot propio sigue siendo pegajoso ante roleplay (ahora aparece como `PENDING ROLLS` en el contexto del narrador en vez de re-pedirse), `end_combat` sigue sin limpiar. Queda el TTL/round stamp.

**Criterio de done:** declarar una acción nueva reemplaza el pending; existe cancelación explícita; `end_combat` limpia; el pending lleva sello de ronda para detectar rancios.

---

### SAM-058 — El fact de INVALID DICE no ofrece salida

**Tipo:** FEAT · **Prio:** P1 · **Estado:** OPEN

Diagnóstico 235, Área 3. Las tres variantes de `mechanic.py:1054-1073` terminan en "roll X", y `narrator.py` refuerza que nada cuenta hasta tirar el dado pedido. El jugador no tiene forma de saber que puede declarar otra acción o pasar el turno.

**Criterio de done:** el fact menciona las salidas ("o declara otra acción / pasa el turno") y el narrator las transmite.

---

### SAM-060 — Interpreter sin glosario ES→EN de armas

**Tipo:** BUG · **Prio:** P1 · **Estado:** OPEN

Diagnóstico 235, Área 2. "Otra vez mandoble" (11-ago 13:25) produjo `weapon: "Greataxe"` — el interpreter tradujo mal; `_find_weapon` matcheó correctamente lo que le pidieron. El prompt (`interpreter.py`) no tiene glosario de armas en español, solo la regla genérica de "closest match". Mismo patrón que ya se resolvió para habilidades en SAM-053.

**Criterio de done:** mandoble→Greatsword, hacha grande→Greataxe, estoque→Rapier, ballesta→Crossbow, etc.; el arma emitida existe en `status.attacks`.

---

### SAM-061 — Sin soporte de N instancias del mismo NPC

**Tipo:** FEAT · **Prio:** P2 · **Estado:** OPEN

Diagnóstico 235, Área 4. `_handle_start_combat` construye exactamente un NPC (`orchestrator.py:632-639`); no hay noción de cantidad en ninguna capa. SAM narró "tres esbirros" y "dos guardias gigantes" y el combate tuvo un único combatiente con el fallback genérico (50/50, AC 15, CR 3). Requiere: `count` en el intent; nombres únicos (`update_npc_hp` matchea por nombre, `combat_state.py:119-142`); `_find_target` con match exacto (hoy substring, `orchestrator.py:1191-1205`); `resolve_npc_turn` sin `targets[0]` fijo (`mechanic.py:660-661`); revisar el presupuesto de loot por kill.

---

### SAM-062 — Healing sin validación de dados ni gate de inventario

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

Diagnóstico 235, Área 5. `_check_dice` saltea `healing` por completo (`mechanic.py:344-345`): con un pending de curación vivo, cualquier dado lo resuelve — un 1d20 curaría d20+mod. Y la curación no está gateada por el inventario: `orchestrator.py:255-288` arma el heal sin verificar que la poción exista; si no está, `server.py:243-245` solo loguea un warning y el HP ya se restauró.

**Criterio de done:** el pending de healing valida contra `healing_dice`; no se arma si el ítem no está en el inventario.

---

### SAM-063 — Observabilidad del pipeline

**Tipo:** CHORE · **Prio:** P2 · **Estado:** DONE · Instrucción 239

Diagnóstico 235, Áreas 1 y 6. Hoy el único discriminador orchestrator/legacy es accidental (`messages.metadata` NULL vs no-NULL, porque solo el path legacy escribe `debug_info`). Estampar `metadata.engine` explícito. Además: el reject de dueño de SAM-049 (`mechanic.py:211-212`) no deja rastro en la transcripción — el dado se vuelve un freeform silencioso; debería producir un fact para que el narrator diga "ese dado no es tuyo". (El dado sin pending ya produce fact desde SAM-053.)

**Cerrado (239):** el dado ajeno tragado en silencio ya no puede ocurrir — sin slot propio es `ORPHAN ROLL` con fact; el diagnóstico "Dice roll swallowed" del orchestrator se eliminó por obsoleto. El freeform pending loguea `ℹ️ Pending replaced` / `set_pending refused` según el caso. La parte de `metadata.engine` no entraba en el alcance de la 239 y se movió a **SAM-066**.

---

### SAM-066 — Observabilidad: `metadata.engine`

**Tipo:** CHORE · **Prio:** P3 · **Estado:** OPEN

Heredado de SAM-063 (instrucción 239). Estampar `metadata.engine = "orchestrator" | "legacy"` en el INSERT del mensaje de SAM (`server.py`, payload `ai_payload`) para que el discriminador forense deje de depender de que `debug_info` sea NULL.

---

### SAM-067 — Frontend envía `campaign_id` en `/api/chat`; quitar la inferencia

**Tipo:** FEAT · **Prio:** P1 · **Estado:** OPEN

Instrucción 239 A2 dejó `ChatRequest.campaign_id` opcional con inferencia `limit(1)` como compatibilidad temporal (log `WARNING: campaign_id inferido, frontend desactualizado`). `chat-interface.tsx` ya tiene `campaignId` como prop (`:78`); falta incluirlo en el body del POST (`:648-658`). Con eso: quitar la rama de inferencia en `server.py`, cerrar SAM-051 y cubrir el caso admin-sin-personaje de SAM-004.

**Criterio de done:** el backend rechaza (400) un `/api/chat` sin `campaign_id`; el log de WARNING desaparece de Render.

---

### SAM-064 — El narrator puebla escenas con enemigos que no existen

**Tipo:** BUG · **Prio:** P3 · **Estado:** OPEN

Diagnóstico 235, Área 4. `ROLEPLAY_TEMPLATE` prohíbe *resolver* combate pero no prohíbe *poblar* la escena: "tres esbirros del Jarl" (10-ago 17:27:51) sin respaldo mecánico. Cuando el combate arranca, la ficción y el `initiative_order` no coinciden.

---

### SAM-065 — Trackeo real de ventaja/desventaja

**Tipo:** FEAT · **Prio:** P2 · **Estado:** OPEN

Abierto por la instrucción 236. No existe estado de ventaja/desventaja en ninguna capa: ni en el intent, ni en el pending, ni en `CombatState`. `DiceRoller.roll_advantage/roll_disadvantage` (`dice.py:31-40`) existen y nunca se llaman. SAM-059 mitigó lo urgente asumiendo ventaja ante 2d20 y declarándolo en los facts, pero la desventaja real (Blur, armadura pesada, condiciones) es indistinguible.

**Criterio de done:** el interpreter emite el modo cuando el jugador lo declara; el pending lo transporta; `_pick_d20` usa max/min según el modo y solo cae al "ADVANTAGE ASSUMED" cuando no hay modo declarado.

---

### SAM-043 — Monster lookup no matchea nombres en español

**Tipo:** BUG · **Prio:** P3 · **Estado:** OPEN

Playtest 2026-06-11: el target "lobo" no encontró "Wolf" en el compendio → `_lookup_monster` cayó al fallback genérico (HP 50, AC 15, CR 3). Eso infló el XP (350 en vez de ~50 de un Wolf CR 1/4) y el loot (presupuesto de CR 3 — un ítem que un CR 1/4 no daría).

**Hipótesis:** el embedding semántico (`match_compendium`, threshold 0.5) debería cruzar idiomas pero no lo hizo para "lobo"→"Wolf". Verificar el threshold, o traducir/normalizar el target al inglés antes del lookup.

**Actualización (playtest 2026-06-11):** el caso común **FUNCIONA** — el intent tradujo "lobo"→"wolf" y el lookup matcheó (stats reales en los chips de iniciativa). El ticket permanece OPEN solo para el caso borde donde la traducción del intent no ocurra. Prioridad confirmada P3.

**Archivos:** `backend/agents/orchestrator.py` (`_lookup_monster`).

**Criterio de done:** "lobo" (y nombres comunes en español) resuelven al monstruo correcto del compendio incluso si el intent no traduce; XP y loot reflejan el CR real, no el fallback.

---

## Tickets cerrados

### SAM-053 — Tirada sin pending se resuelve en el LLM

**Tipo:** BUG · **Prio:** P0 · **Estado:** DONE · **Commit:** `e754dca` · Instrucción 236

Causa raíz de los tags legacy del Área 1 y de la "curación doble" del Área 5. Con `pending = None`, `process_player_roll` devolvía `freeform_roll` **sin appendear a `self.results`** → `get_results_summary()` vacío → `mechanical_facts` falsy → `narrate_roleplay`, donde el LLM recibía el texto crudo del SYSTEM EVENT y improvisaba total, éxito/fallo y a veces un `<DM_ROLL formula=.../>`. Tres frentes: el narrator ya no pide tiradas fuera de los facts, el interpreter reconoce skill checks en español, y el dado huérfano produce un fact `ORPHAN ROLL` que lo manda a `narrate_mechanics`. Detalle en `SAM_progress_log.md`.

### SAM-054 — Regla 15 del narrator licencia aritmética al LLM

**Tipo:** BUG · **Prio:** P0 · **Estado:** DONE · **Commit:** `e754dca` · Instrucción 236

`narrator.py` regla 15 ordenaba literalmente *"For skill checks, calculate the total: d20 result + ability modifier + proficiency bonus. State the total clearly, e.g. 'With your +5 modifier, that's a total of 19.'"* — en el `SYSTEM_PROMPT`, o sea activa también en modo roleplay. Reemplazada por la regla inversa (15a): reportar solo números que aparezcan literalmente en los mechanical facts. Detalle en `SAM_progress_log.md`.

### SAM-059 — Ventaja/desventaja toma `rolls[0]`

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `e754dca` · Instrucción 236

SAM-045 acepta 2d20 como ventaja/desventaja pero nada registra cuál era, y los tres resolvers de d20 tomaban `rolls[0]`. El 13-ago Björn tiró `[19, 7]` y acertó por suerte: con `[7, 19]` el mismo golpe fallaba. Nuevo `_pick_d20` toma el mayor y lo declara en los facts (`ADVANTAGE ASSUMED`). Trackeo real → SAM-065. Detalle en `SAM_progress_log.md`.

### SAM-047 — Auditoría de multiplayer pre-playtest grupal

**Tipo:** CHORE · **Prio:** P1 · **Estado:** DONE · Instrucción 233

Auditoría read-only de preparación para el primer playtest con dos humanos concurrentes (Fekas). Entregable: `SAM_audit_multiplayer_2026-06-11.md` — 10 áreas (concurrencia/lock, turnos, iniciativa, Realtime/sync, atribución, pendings, admin, XP/loot/HP, presence/roster, gaps del assessment original). **Veredicto: SÍ-CON-RIESGOS.** Un bloqueante técnico (SAM-049: pendings sin dueño fuera de combate) y un riesgo operativo (SAM-048: admin sin verificación server-side, `/reset` no-GM = nuclear wipe). Infraestructura core sólida: lock serializa, turn guard simétrico server-side, atribución por user_id, state_updates por character_id, killer tracking, Realtime de mensajes/combate a ambos clientes. 5 tickets nuevos (SAM-048–052) + protocolo de playtest (brief a Fekas, fixes mínimos). Sin cambios de código.

### SAM-044 — `state_updates` múltiples al mismo personaje se pisan entre sí

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · Instrucción 230

Confirmado en diagnóstico 229: cada handler de `state_update` en `server.py` hacía su propio read-modify-write del `status` completo leyendo del `party_characters` en memoria (snapshot del inicio del request, nunca refrescado) → múltiples updates al mismo personaje se pisaban (last-write-wins: Björn perdió oro y XP, conservó el ítem por ser el último handler). **Fix:** la lógica se extrajo a `apply_state_updates(supabase, party_characters, state_updates)` (función de módulo en `server.py`) que **acumula** todos los cambios de `status` por personaje en memoria (`pending_status[char_id]`) y **flushea UN solo write por personaje** — status + columnas top-level (level/class del level-up) en el mismo `.update()`. El orden de los updates dejó de importar. Harness `test_sam044.py`: 6 escenarios / 15 checks, todos pasan (caso Björn xp+oro+ítem en un write, dos personajes sin cruce, hp+oro, level-up con columnas top-level, find_char por id/nombre, flush con fallo aislado por personaje). **Validado en prod (playtest 2026-06-11):** caso Björn xp+oro+HP en un mismo request → `💾 Status flushed` único por personaje, wallet (17 gp) y ficha (XP 350) correctos en el frontend. Lección: handlers que hacen read-modify-write del documento completo NO componen — acumular y flushear una vez.

### SAM-029 — Aplicar `state_updates` por `character_id` en vez de por `name`

**Tipo:** REFACTOR · **Prio:** P2 (subido de P3) · **Estado:** DONE · Instrucción 230

Junto con SAM-044. El loop de `state_updates` resuelve el personaje con `_find_char`: prefiere `character_id` si el update lo trae, fallback a match por nombre case/space-insensitive. Los 8 sitios de emisión estampan `character_id` (None-safe — el fallback por nombre cubre cualquier ausencia): `mechanic.py` (player_hp de healing/self_damage/npc-turn, xp_update de award_xp) y `orchestrator.py` (spell_slot_consume, inventory_remove, money_award, item_award — este último capturando el `killer_pc` dict). Homónimos y renames dejan de romper el update. Validado junto a SAM-044 en el playtest 2026-06-11 (id matching activo en los 8 emisores de state_updates).

### SAM-042 — Crítico no duplica dados de daño

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · Instrucción 231

Raíz: dos fuentes de prompt contradictorias — `_resolve_weapon_attack` duplicaba bien los dados pero `_get_roll_prompt` los recomputaba desde `weapon["damage"]` (sin duplicar), ignorando `critical`. **Fix (fuente única):** el pending de damage lleva `damage_spec` ya resuelto (duplicado en crit vía `_double_dice`, sin sufijo de tipo); `_get_roll_prompt` lo lee y NUNCA recalcula. Stampeado en los 4 orígenes de damage pending (weapon/spell/sneak + freeform del dice tray). El lado jugador del crit lo cierra la validación estricta (ver SAM-039). Tests `test_sam039_042.py` S1. **Validado en prod (playtest 2026-06-11):** la validación central de dados funcionó; los únicos bordes pendientes (attack-count, unarmed fijo) se cerraron en SAM-045/046.

### SAM-039 — Weapon mismatch + validación estricta de dados

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · Instrucción 231

Dos partes. **(a) Arma declarada:** `_find_weapon` reescrito — normaliza acentos/case/espacios (`_normalize_weapon`) y matchea substring en ambas direcciones, así "great axe"/"GreatAxe"/"Greataxe" resuelven al mismo ataque; el fallback a `attacks[0]` deja de ser silencioso (loguea `⚠️ Weapon ... not matched`). `_display_dice` garantiza que el prompt sea siempre `NdM[+X]` — nunca un número plano ("tira 5"). **(b) Validación estricta (raíz compartida con SAM-042):** `process_player_roll` valida el dado tirado contra el esperado del pending (`_check_dice`): attack roll → d20 (solo caras, advantage/disadvantage permite 2 d20); damage → N y M de `damage_spec`. Si no coincide → rechaza sin tocar HP/acción/turno, **preserva el pending** (persiste entre requests) y emite fact `INVALID DICE: expected … got … — Wrong die type/number of dice`. Narrator RULE 16: ante INVALID DICE pide el dado correcto sin narrar resultado. Anti-deadlock: `end_turn` (SAM-034) sigue siendo la salida (limpia el pending). Tests `test_sam039_042.py`: 28 checks (S1–S9 + advantage + `_display_dice`), todos pasan. **Validado en prod (playtest 2026-06-11):** el caso central funcionó; los dos bordes restantes (cantidad en attack rolls, unarmed con daño fijo) se cerraron en SAM-045/046.

### SAM-045 — Attack rolls no validan cantidad de d20 (3d20/4d20 aceptados)

**Tipo:** BUG · **Prio:** P2 · **Estado:** DONE · Instrucción 232

Playtest 2026-06-11: el jugador tiró 4d20 y 2d20 en attack rolls y el sistema los aceptó — `_check_dice` validaba las caras (d20) pero no la cantidad. Fix: para attack rolls, la cantidad debe ser **1 (normal) o 2 (ventaja/desventaja)**; 0 o 3+ se rechaza con fact `INVALID DICE: an attack roll uses 1d20 (or 2d20 with advantage/disadvantage)...`, preservando el pending. Con 2d20 el resolver toma hoy el PRIMER d20 (`rolls[0]`); ventaja/desventaja real (mayor/menor) es un feature aparte — acá solo se valida que no entren 3+. Tests `test_sam045_046.py` S1–S4.

### SAM-046 — Unarmed Strike daño fijo rompe prompt y validación → 1d4+STR

**Tipo:** BUG · **Prio:** P2 · **Estado:** DONE · Instrucción 232

Playtest 2026-06-11: Unarmed Strike generaba prompt "1d1+4" (feo) y la validación dejaba pasar un 1d20 como daño del puñetazo (19 aplicado) — el daño fijo no encajaba en el flujo de tiradas. Decisión del director: tratar Unarmed Strike como **1d4+STR**. Fix runtime (no toca el dato del PDF — eso es SAM-005): nuevo `_effective_damage(weapon, character)` en `mechanic.py` normaliza Unarmed Strike (o cualquier daño fijo/no parseable) a `1d4+{str_mod}` (str top-level, SAM-018) al armar el pending de `weapon_damage`; el `weapon` del pending lleva el daño normalizado para que el parse del modificador y el prompt coincidan. `_get_roll_prompt` emite "Tira 1d4+4 de daño". **Sanity / fail-closed (Change 3):** `_check_dice` ahora rechaza (en vez de aceptar) un roll contra un `damage_spec` degenerado/no parseable (`N<1` o `M<2`) con log `⚠️ Unparseable damage_spec` — evita que un 1d20 se cuele como daño de un "1d1" futuro. Tests `test_sam045_046.py` S5–S8 + regresión Greataxe.

### SAM-041 — Declaraciones de acción producen facts vacíos (deadlock narrativo)

**Tipo:** BUG · **Prio:** P0 · **Estado:** DONE · **Commit:** `4f4443b`

Instrucción 228 (causa raíz del diagnóstico 227, playtest 2026-06-11 ~02:12). Los intents declarativos (attack, spell con attack roll, skill_check) armaban el pending pero `get_results_summary` no tenía caso para renderizarlos → `mechanical_facts` vacío → `narrate_roleplay`, cuyo template prohíbe mecánica de combate desde SAM-033 → el narrator negaba el ataque ("ya usaste tus dos tajos") en vez de pedir el d20. Deadlock narrativo con motor sano (el estado vivo tenía `actions_remaining=2` y un pending armado que nadie anunciaba). Antes de SAM-033 el path se rescataba solo porque el narrator de roleplay improvisaba el pedido de tirada.

**Fix (principio: si hay pending, hay facts; si hay facts, narra `narrate_mechanics`):** (1) casos nuevos en `get_results_summary` para las tres declaraciones (`attack` con AC del target agregado en origen, `spell` esperando tirada, `skill_check`); (2) red de seguridad en el orchestrator — cualquier path futuro que arme pending sin facts sintetiza un fact mínimo + prompt y loguea warning; (3) bullet RULE 16 — ante "Awaiting ... roll" el narrator solo construye tensión y pide los dados, nunca niega la acción; (4) gate UX — declarar con 0 acciones no arma pending silencioso, los facts sugieren "paso". Verificado con harness de 6 escenarios incluyendo la reproducción completa del deadlock de round 2. Detalle en `SAM_progress_log.md`.

**Validado en prod (playtest 2026-06-11):** el combate colgado se destrabó tirando el d20 del pending viejo; la declaración de ataque en round 2 pide el d20 correctamente, cero negaciones falsas. De paso se validó la fase 1 de XP end-to-end: `⭐ XP` en logs, anuncio en narración y persistencia confirmada por query (`status.xp=350` en Björn y Vex).

### SAM-014 — NPC damage no persiste a `characters.status.hp_current`

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Resuelto por:** SAM-036 (`d0faa4c`)

Validado en playtest 2026-06-11: HP del lobo monotónicamente decreciente (27→17→2→0), cero rebotes, logs `💢 NPC HP` confirmando cada cambio. **Causa raíz real: SAM-036** (el daño de PCs delegados se emitía como `player_hp` contra un nombre inexistente), no SAM-017 como se cerró prematuramente la primera vez. Historial: abierto en playtest de abril → BLOCKED por SAM-017 → cerrado prematuramente → reabierto en instrucción 223 → cerrado con evidencia en instrucción 224. El residual de COMBAT STATUS stale sigue en SAM-022.

### SAM-037 — Combate inactivo descarta `initiative_order` (NPC revive a HP completo)

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Cerrado sin cambios de código adicionales** (instrumentación en `d0faa4c`)

Validado en playtest 2026-06-11: el log `💾 Persisting INACTIVE combat` apareció ÚNICAMENTE tras muerte legítima del NPC (2→0, `☠️`, `🏁`), nunca con NPCs vivos. El rebote de HP era consecuencia del daño perdido (SAM-036): el lobo "moría" espuriamente y el siguiente ataque lo recreaba a HP completo. Con SAM-036 cerrado, el rebote desapareció. La lógica de persistencia NO se cambió — descartar `initiative_order` en fin legítimo es el comportamiento correcto (no revivir muertos). La instrumentación queda en su lugar como centinela: si `💾 ... LIVE NPCs: [...]` aparece alguna vez, hay una desactivación anómala nueva.

### SAM-017 — Narrator SYSTEM_PROMPT explota con KeyError por JSON literal

**Tipo:** BUG · **Prio:** P0 · **Estado:** DONE · **Commit:** `12909eb`

Regresión de SAM-013 (commit `738f85f`): el bullet "INITIATIVE GROUND TRUTH" de RULE 16 metió un JSON literal sin escapar en el `SYSTEM_PROMPT` → `str.format()` lo interpretaba como placeholder → `KeyError: '"result"'` → TODOS los mensajes de combate caían al legacy `SAMBrain`, perdiendo turn enforcement, persistencia de HP y validez de DM_ROLLs. Fue causa raíz de SAM-015/016 y co-causa de SAM-014. Fix: llaves escapadas `{{...}}` (única llave literal sin escapar del archivo). Validado en playtests 2026-06-09/10/11: cero fallbacks al legacy en los logs de Render. Lección operativa permanente: todo cambio a prompts que pasan por `.format()` corre smoke test local antes de pushear.

### SAM-036 — Daño de PC delegado a NPC se emite como `player_hp`

**Tipo:** BUG · **Prio:** P0 · **Estado:** DONE · **Commit:** `d0faa4c`

Instrucción 223 (evidencia del diagnóstico 222: el HP del lobo no bajaba tras los turnos de Vex delegada). `resolve_npc_turn` (`mechanic.py`) emitía TODO el daño acumulado como `state_update` tipo `player_hp` sin mirar el target: cuando un PC delegado atacaba a un NPC, el update salía contra un nombre que no existe en `characters` y el HP del NPC en combat state nunca bajaba. Fix: bifurcación por `target.is_npc` — NPCs mutan `combat.update_npc_hp` (visible en logs `💢 NPC HP`), jugadores siguen por `player_hp`. El parámetro engañoso `players` se renombró a `targets` (el orchestrator pasa los NPCs enemigos cuando actúa un PC delegado — confirmado en `_resolve_npc_turns`). Verificado con harness local (Vex delegada +100 to-hit baja el HP del lobo; el lobo daña a Björn vía `player_hp`; cero `player_hp` con nombre de NPC). Validación final en playtest junto con SAM-014/037.

### SAM-038 — Instrumentación de HP de NPC y transiciones de combate

**Tipo:** CHORE · **Prio:** P1 · **Estado:** DONE · **Commit:** `d0faa4c`

Instrucción 223, base de validación para SAM-036/037. `update_npc_hp` ahora matchea case/space-insensitive, loguea cada cambio (`💢 NPC HP: name old → new`), avisa con la initiative order completa si el nombre no matchea (antes fallaba en silencio), y loguea la muerte (`☠️ NPC down`). `start_combat`/`end_combat` loguean las transiciones (`⚔️`/`🏁`). El orchestrator loguea el descarte de combate inactivo distinguiendo fin legítimo de anómalo con NPCs vivos (`💾 ... LIVE NPCs: [...]` — la firma del rebote de SAM-037). **Validado en playtest 2026-06-11:** logs `💢`/`☠️`/`🏁`/`💾` funcionando en prod; fueron la evidencia con la que se cerraron SAM-014 y SAM-037.

### SAM-033 — Narrator alucina combate completo sin mechanical facts

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `2c08fcb`

Instrucción 220. Con intent `roleplay` y combate inexistente, el narrator inventó iniciativas, ataques enemigos, daño y "Tu HP baja a 61/68" — todo fake, con formato `<DM_ROLL formula=.../>` aprendido de mensajes legacy en el history (evidencia: playtest 2026-06-09). Fix en dos vectores: (1) regla 9b en SYSTEM_PROMPT — prohibido generar tags `<DM_ROLL>` propios en cualquier formato — y bloque CRITICAL en ROLEPLAY_TEMPLATE que prohíbe iniciativas/ataques/daño/HP/DM_ROLL sin mechanical facts; (2) sanitización del history en `_invoke`: regex elimina los DM_ROLL legacy attribute-style de mensajes assistant (los JSON correctos se conservan como buen ejemplo; la forma emparejada se procesa antes que la self-closing para no dejar closers huérfanos). Validación post-deploy pendiente con la frase exacta que disparó la alucinación. Detalle en `SAM_progress_log.md`.

### SAM-003 — Sneak Attack modeling

**Tipo:** FEAT · **Prio:** P1 · **Estado:** DONE · **Commit:** `2c08fcb`

Instrucción 221. El 4d6 de Sneak Attack llegaba como `dice_roll` huérfano y quedaba narrativo. Fix: chain de pending rolls — `_get_sneak_dice` detecta Rogue (tolera sufijo de nivel) y calcula `ceil(level/2)d6`; el pending `weapon_attack` (declarado o freeform d20 del dice tray) lleva `sneak_dice` si `combat.sneak_available()`; en HIT se propaga al pending `weapon_damage`; al aplicarse el daño del arma (target vivo) se encadena un pending `sneak_damage` contra el mismo target con HP actualizado; `_resolve_sneak_damage` aplica el daño, marca `sneak_used` (once per turn, persiste en `CombatState.to_dict`, resetea por turno). La acción se consume UNA vez al final del chain (`sneak_damage` agregado al tuple de consumo). El warning de rolls narrative-only ahora solo dispara para rolls realmente huérfanos. Interpreter: "sneak attack" mencionado con ataque de arma → type `attack`, no `ability`. Narrator RULE 16: narrar el sneak como parte del MISMO ataque. Verificado con harness local de 8 escenarios. **Validación parcial: código testeado con FakeLLM, falta playtest manual** con Vex no-delegada (d20 → 1d8+5 → 4d6, HP del NPC baja dos veces, una acción). Detalle en `SAM_progress_log.md`.

### SAM-034 — No existe forma de terminar el turno voluntariamente

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `89cda66`

Instrucción 219. En combate, "Paso" / "Termino mi turno" / "No hago nada más" caía al intent `free_action` → el orchestrator recordaba en loop que el jugador declare su acción; no había forma de ceder el turno. Fix: nuevo intent `end_turn` en el interpreter (solo con `in_combat=True`; fuera de combate esas frases siguen siendo `free_action`), handler en el orchestrator que pone `actions_remaining=0`, limpia cualquier `pending_player_roll` abandonado y dispara `_resolve_npc_turns`, `end_turn` agregado a la lista del turn guard (pasar fuera de turno → OUT_OF_TURN), y bullet en RULE 16 del narrator para reconocer el pase sin volver a pedir acción. Verificado con tests locales de los 5 escenarios (básico, pending abandonado, fuera de turno, fuera de combate). Detalle en `SAM_progress_log.md`.

### SAM-035 — skill_check en combate no consume acción

**Tipo:** BUG · **Prio:** P2 · **Estado:** DONE · **Commit:** `89cda66`

Instrucción 219. 5e RAW: usar una habilidad en combate (shove, grapple) consume la acción del turno, pero el branch `skill_check` nunca llamaba `consume_action()` → checks infinitos sin avance de turno. Como el d20 llega en el request siguiente, el fix estampa `consumes_action` + `character_name` en el `pending_player_roll` del check y consume la acción cuando el roll se resuelve (mismo patrón `previous_pending_type` de `weapon_damage`). `consumes_action` solo es True si el check es del jugador en turno — checks reactivos de jugadores fuera de turno no comen la acción del jugador activo. Detalle en `SAM_progress_log.md`.

### SAM-020 — Auditoría arquitectónica del sistema

**Tipo:** CHORE · **Prio:** P1 · **Estado:** DONE · **Commit:** `03bc7b9`

Auditoría read-only del estado real del sistema (instrucción 215). Entregable: `SAM_audit_2026-06-05.md` — 8 secciones (tags, intent, combate, persistencia HP, legacy vs orchestrator, contratos rotos, formato, errores silenciosos) con ESTADO ACTUAL / INCONSISTENCIAS / RIESGOS / TICKETS. Produjo 13 tickets nuevos (SAM-018, 021–032) y reconcilió SAM-014/015/016 con la causa raíz SAM-017. Sin cambios de código.

### SAM-018 — Initiative/ataque-delegado modifiers +0 (stats nesting)

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `5f6a880`

Instrucción 217. El orchestrator leía `status.stats` (anidado, vacío) en `_handle_start_combat` (iniciativa de jugadores) y `_build_combatant_from_character` (ataque de PC delegado), pero `stats` es columna top-level → todos los modificadores salían +0. Fix: leer `char.get("stats")` en ambos call-sites (`orchestrator.py:488,603`). Verificado contra prod Supabase (Björn DEX 14 → +2, Vex DEX 20 → +5; `status.stats` = None). Detalle en `SAM_audit_2026-06-05.md` §6 y `SAM_progress_log.md`. **Hallazgo lateral:** SAM-016 tiene causa raíz adicional (class con sufijo de nivel rompe `has_extra_attack`).

### SAM-016 — Extra Attack roto: `has_extra_attack` no matchea `class` con sufijo de nivel

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `186e462`

Instrucción 218 (causa raíz hallada en SAM-018). El PDF import guarda `class` con sufijo de nivel (`"Barbarian 7"`, `ai.py:553`), pero `has_extra_attack` (`combat_state.py`) hacía membresía exacta de set (`cls in EXTRA_ATTACK_CLASSES`) → `"barbarian 7"` nunca matcheaba → Extra Attack jamás se activaba para martials importados de PDF, aun con el orchestrator activo. Fix: extraer la primera palabra del class (`cls_raw.split()[0]`, con guard anti-IndexError). Verificado en prod que `level` es columna entera (7) separada del class → `level >= 5` ya funcionaba (sin segundo bug). Björn (Barbarian 7) → 2 ataques; Vex (Rogue 7) → 1. La capa SAM-017 (fallback legacy sin action economy) se valida por separado. Detalle en `SAM_progress_log.md`.

### SAM-002 — Turn enforcement + Extra Attack

**Tipo:** FEAT · **Prio:** P0 · **Estado:** DONE · **Commit:** `839ba73`

Implementado en instrucción 209. Turn guard bloquea acciones fuera de turno; Extra Attack para martials ≥ lvl 5 respetado via `actions_remaining` + `consume_action()` + `turn_is_over()`. Detalle completo en `SAM_progress_log.md`.

### SAM-013 — Narrator inventa números en iniciativa

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `738f85f`

Implementado en instrucción 212. RULE 16 del narrator reforzada con "INITIATIVE GROUND TRUTH" — el `result` dentro de cada `<DM_ROLL>` es autoritativo, prosa y turn order deben citar números exactos, ties se resuelven por orden listado en los facts. Detalle en `SAM_progress_log.md`.

### SAM-001 — DM_ROLL chips apilados verticalmente

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `c215cc7`

Implementado en instrucción 213. `renderMessageContent` ahora cuenta los `<DM_ROLL>` del mensaje: si hay 2+, entra en modo HOIST — renderiza todos los chips en un `<div flex flex-col gap-1 my-2 items-start>` al inicio de la burbuja y abajo el texto narrativo con los tags removidos y el whitespace colapsado (spaces/tabs → 1 space, espacios antes de `\n` eliminados, `\n{3,}` → `\n\n`). Con 0 o 1 chip se mantiene el flujo inline anterior. Detalle en `SAM_progress_log.md`.
