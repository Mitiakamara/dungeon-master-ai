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
| SAM-003 | Sneak Attack modeling | FEAT | P1 | OPEN |
| SAM-004 | `/delegate` rechaza rol `admin` | BUG | P2 | OPEN |
| SAM-005 | Vex tiene Unarmed Strike incorrecto | BUG | P3 | OPEN |
| SAM-006 | MemoryService trunca JSON de Gemini | BUG | P3 | OPEN |
| SAM-007 | FK violation al crear personaje para usuarios nuevos | BUG | P2 | OPEN? |
| SAM-008 | SAM verbosidad ocasional | BUG | P3 | OPEN |
| SAM-009 | Servicio de generación de imágenes (tag `<IMAGE>`) | FEAT | P2 | OPEN |
| SAM-010 | Vercel Root Directory config | CHORE | P3 | OPEN |
| SAM-011 | Commlink Realtime + auto-mark-as-read | FEAT | P2 | OPEN |
| SAM-012 | Quitar console.logs de debug (presence tracking) | CHORE | P3 | OPEN |
| SAM-013 | Narrator inventa números en iniciativa (no respeta DM_ROLL tag) | BUG | P1 | DONE |
| SAM-014 | NPC damage no persiste a `characters.status.hp_current` | BUG | P1 | BLOCKED |
| SAM-015 | DM_ROLL chips de turnos NPC llegan como "Invalid Roll Data" | BUG | P1 | BLOCKED |
| SAM-016 | Extra Attack no se activa para Barbarian Lvl 7 (pendiente confirmar) | BUG | P1 | BLOCKED |
| SAM-017 | Narrator SYSTEM_PROMPT explota con KeyError por JSON literal (regresión SAM-013) | BUG | P0 | IN_PROGRESS |
| SAM-018 | Initiative/ataque-delegado modifiers +0 — orchestrator lee `status.stats` en vez de `stats` top-level | BUG | P1 | OPEN |
| SAM-020 | Auditoría arquitectónica del sistema (`SAM_audit_2026-06-05.md`) | CHORE | P1 | DONE |
| SAM-021 | Orchestrator no implementa loot/XP/level-up/imágenes (solo en legacy `ai.py`) | REFACTOR | P1 | OPEN |
| SAM-022 | COMBAT STATUS muestra HP de jugador stale → drift narrador vs BD/sidebar | BUG | P2 | OPEN |
| SAM-023 | Respuestas de comandos admin duplicadas para el emisor (optimista + Realtime) | BUG | P2 | OPEN |
| SAM-024 | Legacy `<UPDATE>` HP solo client-side + ambigüedad de atribución multiplayer | BUG | P2 | OPEN |
| SAM-025 | Extraer de `ai.py` piezas no-game-loop reusadas (DM style, Supabase client, PDF import, avatares) | REFACTOR | P2 | OPEN |
| SAM-026 | Código muerto: `pending_action` + `<ACTION>RELOAD_CHAT>` no manejado | CHORE | P3 | OPEN |
| SAM-027 | Log/warning cuando un intent llega sin handler mecánico dedicado | CHORE | P3 | OPEN |
| SAM-028 | Unificar shape de `settings.combat` entre legacy y orchestrator | BUG | P2 | OPEN |
| SAM-029 | Aplicar `state_updates` por `character_id` en vez de por `name` | REFACTOR | P3 | OPEN |
| SAM-030 | Incluir `stats` en `_format_character_context` (gap narrator RULE 15) | CHORE | P3 | OPEN |
| SAM-031 | Gate `debug_log.txt` por env DEBUG (no I/O en hot-path) | CHORE | P3 | OPEN |
| SAM-032 | Retry/backoff para `RemoteProtocolError` httpx (Gemini/Supabase) | CHORE | P3 | OPEN |

> Detalle completo de SAM-018, SAM-021–032 en `SAM_audit_2026-06-05.md` (auditoría SAM-020). SAM-019 reservado/sin asignar.

---

## Detalle — Tickets activos

### SAM-003 — Sneak Attack modeling

**Tipo:** FEAT · **Prio:** P1 · **Estado:** OPEN

El Rogue Sneak Attack es 1d8 weapon damage + 4d6 sneak damage como una sola acción. El pipeline actual solo conoce `weapon_attack → weapon_damage`. El 4d6 llega como `dice_roll` huérfano y queda narrativo — no se aplica al NPC.

Log confirmatorio: `⚠️ Dice roll processed but no state_updates generated — damage may be narrative-only`.

**Archivos afectados:** `backend/agents/interpreter.py`, `backend/agents/mechanic.py`, `backend/agents/orchestrator.py`.

**Enfoque propuesto:** extender `pending_player_roll` con `follow_up_dice` (ej. `"4d6"`). Cuando se resuelve `weapon_damage` con follow-up seteado, encadenar un pending `sneak_damage` que aplique al mismo target.

**Criterio de done:** Vex tira d20 (hit) → 1d8 (aplica al NPC) → 4d6 (aplica al mismo NPC). HP del NPC refleja la suma total.

---

### SAM-004 — `/delegate` rechaza rol `admin`

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

Usuarios con rol `admin` (no GM) reciben "No active campaign found for GM" al intentar `/delegate`. El resolver solo acepta `gm_id` como dueño de campaña.

**Archivos afectados:** handler de `/delegate` en backend (probablemente `backend/routes/admin.py` o `backend/routes/commands.py`).

**Criterio de done:** el resolver acepta tanto `gm_id == user_id` como `user.role == 'admin'`.

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

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN?

El progress log del 18 Mar 2026 reporta resuelto via trigger `handle_new_user` (migration 006). Las memorias aún lo listan como pendiente. **Verificar en playtest si sigue ocurriendo.**

**Criterio de done:** un usuario recién registrado puede crear un personaje sin FK violation. Si ya está resuelto, mover a DONE y anotar commit.

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

### SAM-017 — Narrator SYSTEM_PROMPT explota con KeyError por JSON literal

**Tipo:** BUG · **Prio:** P0 · **Estado:** IN_PROGRESS

Regresión introducida en SAM-013 (commit `738f85f`). El bullet "INITIATIVE GROUND TRUTH" de RULE 16 agregó un ejemplo JSON literal `{"result": 5, "reason": "enemy Initiative"}` dentro del `SYSTEM_PROMPT`. `narrator.py:122` hace `SYSTEM_PROMPT.format(...)`, y `str.format()` interpreta `{"result"...}` como placeholder → `KeyError: '"result"'`.

**Impacto:** TODOS los mensajes de combate caían al legacy `SAMBrain` (`ai.py`), perdiendo turn enforcement, persistencia consistente de HP, y validez de DM_ROLLs. Causa raíz de SAM-014, SAM-015, SAM-016 (BLOCKED hasta validar).

Log (Render, 2026-06-05T20:54:21): `KeyError: '"result"'` en `narrate_mechanics` → `⚠️ Orchestrator failed, falling back to legacy SAMBrain`.

**Archivos afectados:** `backend/agents/narrator.py`.

**Fix aplicado:** llaves del JSON de ejemplo escapadas a `{{...}}` en RULE 16. Auditoría completa del archivo: era la única llave literal sin escapar. Smoke test local `SYSTEM_PROMPT.format()` pasa sin KeyError (6596 chars).

**Criterio de done:** smoke test local OK ✅ · en prod ningún chat de combate cae al legacy · logs muestran `💚 HP updated:` consistente · sidebar HP coincide con HP narrativo tras F5. Pendiente: validación post-deploy.

---

### SAM-014 — NPC damage no persiste a `characters.status.hp_current`

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017) — reconciliado por auditoría SAM-020

**Reconciliación (auditoría 5 Jun):** en el pipeline NUEVO el HP del jugador **sí persiste server-side** — `server.py:293-299` aplica el `state_update` tipo `player_hp` con `UPDATE characters.status.hp_current`. El síntoma "no persiste" era el fallback al legacy (SAM-017), donde el HP depende del `<UPDATE>` client-side y nunca pasa por ese handler. Validar tras deploy de SAM-017: si el daño NPC persiste y el sidebar coincide con la BD → cerrar como "resuelto por SAM-017".

**Residual independiente:** el bloque `COMBAT STATUS` que ve el narrador lee HP de jugador desactualizado (`party_characters` stale) → drift narrativo. Trackeado por separado en **SAM-022** (no se cierra con SAM-017).

---

### SAM-015 — DM_ROLL chips de turnos NPC llegan como "Invalid Roll Data"

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017) — reconciliado por auditoría SAM-020

**Reconciliación (auditoría 5 Jun):** confirmado el **formato dual de `<DM_ROLL>`**. El orchestrator emite JSON (`orchestrator.py:508,816,833`); el legacy `ai.py` instruye al LLM a emitir **texto libre/breakdown** (`ai.py:87,93,220`). El frontend hace `JSON.parse` (`chat-interface.tsx:740`) → si falla, renderiza `[Invalid Roll Data]` (`:782,796`). El texto libre del screenshot nace en el legacy → bajo fallback (SAM-017) todos los DM_ROLL de NPC fallan el parse.

**Criterio de done:** se resuelve al no caer al legacy (SAM-017). *Defensivo opcional:* hacer `parseRoll` tolerante a texto libre (mostrar el texto crudo en vez de `[Invalid Roll Data]`).

---

### SAM-016 — Extra Attack no se activa para Barbarian Lvl 7

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017) — reconciliado por auditoría SAM-020

**Reconciliación (auditoría 5 Jun):** la action economy del orchestrator es **correcta** — `combat_state.py:37-90` (`has_extra_attack`, seed/`consume_action`/`turn_is_over`) y los combatientes se estampan con `class`/`level` en `orchestrator.py:503-504`. El legacy NO tiene esta lógica → bajo fallback (SAM-017) Extra Attack desaparece.

**Criterio de done:** se resuelve al no caer al legacy (SAM-017). Revalidar con Barbarian Lvl 7: SAM debe invitar al segundo ataque tras el primer damage roll.

---

### SAM-018 — Initiative/ataque-delegado modifiers +0 (stats nesting)

**Tipo:** BUG · **Prio:** P1 · **Estado:** OPEN

Contrato roto confirmado en auditoría SAM-020. `stats` es **columna top-level** (`schema_game_engine.sql:16`, `characters.py:29`), pero el orchestrator la lee anidada: `orchestrator.py:488` (iniciativa de jugadores) y `:603` (`_build_combatant_from_character`, ataques de PC delegado) hacen `status.get("stats")` → vacío → `dex_mod`/`str_mod` = 0. En cambio `mechanic.py:419` (skill modifier) lee `character.get("stats")` top-level → correcto. Asimetría.

**Archivos afectados:** `backend/agents/orchestrator.py` (2 call-sites: `:488`, `:603`).

**Criterio de done:** iniciativa de jugador refleja su DEX mod real (no +0); ataque de PC delegado usa STR/DEX+proficiency reales. Detalle en `SAM_audit_2026-06-05.md` §6.

---

### SAM-021 — Orchestrator no implementa loot/XP/level-up/imágenes

**Tipo:** REFACTOR/BUG · **Prio:** P1 · **Estado:** OPEN

Hallazgo principal de la auditoría SAM-020. El pipeline nuevo no porta features del legacy: `mechanic.award_xp` (`:614`) existe pero **nunca se llama**; `give_loot` solo está en tools legacy; el narrator tiene prohibido emitir `<LOOT>/<XP_GAIN>/<EVENT>/<IMAGE>` (`narrator.py:39`). Esas features solo viven en `ai.py`, alcanzado solo por excepción (`server.py:398-406`). En operación normal (orchestrator OK) se descartan en silencio. **Subsume SAM-009** (servicio de imágenes).

**Enfoque:** agregar intents/handlers de loot y XP al orchestrator (o delegación explícita al legacy, no por excepción) + conectar generación de imagen.

**Criterio de done:** matar un enemigo otorga XP + dispara level-up; encontrar tesoro persiste loot en inventario; SAM puede generar imágenes — todo sin depender del fallback legacy. Detalle en `SAM_audit_2026-06-05.md` §1, §5.

---

### SAM-022 — COMBAT STATUS muestra HP de jugador stale (drift narrador vs BD)

**Tipo:** BUG · **Prio:** P2 · **Estado:** OPEN

El overlay de HP de jugador en el bloque `COMBAT STATUS` (`orchestrator.py:856-868` y `:319-329`) lee `party_characters[].status.hp_current` = snapshot del inicio del request (`server.py:247`), ANTES de que el `state_update` de este turno se persista (`server.py:293` corre después de `process_message`). Resultado: el narrador ve HP viejo en COMBAT STATUS pero HP nuevo en el fact `damage_applied`; RULE 16 lo manda a citar COMBAT STATUS → narra el viejo. Tras F5, el sidebar lee BD = nuevo → mismatch narrativo↔sidebar. Residual de SAM-014, independiente de SAM-017.

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

### SAM-029 — Aplicar `state_updates` por `character_id` en vez de por `name`

**Tipo:** REFACTOR · **Prio:** P3 · **Estado:** OPEN

`server.py` matchea personajes por nombre al aplicar state_updates (`:295`, `:303`, `:321`, `:354`). Homónimos colisionan; un rename rompe el update.

**Criterio de done:** los handlers de `player_hp`/`xp_update`/`spell_slot_consume`/`inventory_remove` resuelven por `character_id`. Requiere que el engine propague el id en los `state_updates`. Detalle en `SAM_audit_2026-06-05.md` §4.

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

---

## Tickets cerrados

### SAM-020 — Auditoría arquitectónica del sistema

**Tipo:** CHORE · **Prio:** P1 · **Estado:** DONE · **Commit:** `03bc7b9`

Auditoría read-only del estado real del sistema (instrucción 215). Entregable: `SAM_audit_2026-06-05.md` — 8 secciones (tags, intent, combate, persistencia HP, legacy vs orchestrator, contratos rotos, formato, errores silenciosos) con ESTADO ACTUAL / INCONSISTENCIAS / RIESGOS / TICKETS. Produjo 13 tickets nuevos (SAM-018, 021–032) y reconcilió SAM-014/015/016 con la causa raíz SAM-017. Sin cambios de código.

### SAM-002 — Turn enforcement + Extra Attack

**Tipo:** FEAT · **Prio:** P0 · **Estado:** DONE · **Commit:** `839ba73`

Implementado en instrucción 209. Turn guard bloquea acciones fuera de turno; Extra Attack para martials ≥ lvl 5 respetado via `actions_remaining` + `consume_action()` + `turn_is_over()`. Detalle completo en `SAM_progress_log.md`.

### SAM-013 — Narrator inventa números en iniciativa

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `738f85f`

Implementado en instrucción 212. RULE 16 del narrator reforzada con "INITIATIVE GROUND TRUTH" — el `result` dentro de cada `<DM_ROLL>` es autoritativo, prosa y turn order deben citar números exactos, ties se resuelven por orden listado en los facts. Detalle en `SAM_progress_log.md`.

### SAM-001 — DM_ROLL chips apilados verticalmente

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `c215cc7`

Implementado en instrucción 213. `renderMessageContent` ahora cuenta los `<DM_ROLL>` del mensaje: si hay 2+, entra en modo HOIST — renderiza todos los chips en un `<div flex flex-col gap-1 my-2 items-start>` al inicio de la burbuja y abajo el texto narrativo con los tags removidos y el whitespace colapsado (spaces/tabs → 1 space, espacios antes de `\n` eliminados, `\n{3,}` → `\n\n`). Con 0 o 1 chip se mantiene el flujo inline anterior. Detalle en `SAM_progress_log.md`.
