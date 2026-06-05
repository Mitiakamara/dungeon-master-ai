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

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017)

Detectado en playtest. El HP del PC no se actualiza tras el turno de contraataque del NPC. **Sospecha:** síntoma del fallback al legacy causado por SAM-017, no un bug propio del pipeline multi-agente. Validar tras deploy de SAM-017: si el HP persiste correctamente → cerrar como "resuelto por SAM-017". Si persiste, diagnóstico dedicado.

---

### SAM-015 — DM_ROLL chips de turnos NPC llegan como "Invalid Roll Data"

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017)

Detectado en playtest. Los `<DM_ROLL>` de los turnos NPC se renderizan como "Invalid Roll Data". **Sospecha:** el legacy `SAMBrain` no emite los tags en el formato que espera el renderer del frontend. Validar tras deploy de SAM-017: si los DM_ROLLs llegan parseables → cerrar como "resuelto por SAM-017".

---

### SAM-016 — Extra Attack no se activa para Barbarian Lvl 7

**Tipo:** BUG · **Prio:** P1 · **Estado:** BLOCKED (por SAM-017)

Detectado en playtest (pendiente confirmar). SAM no pregunta por el segundo ataque tras el primer damage roll de un Barbarian nivel 7. **Sospecha:** la action economy vive en el pipeline multi-agente (`combat_state.py`), inactivo bajo el fallback legacy. Validar tras deploy de SAM-017: si SAM invita al segundo ataque → cerrar como "resuelto por SAM-017".

---

---

## Tickets cerrados

### SAM-002 — Turn enforcement + Extra Attack

**Tipo:** FEAT · **Prio:** P0 · **Estado:** DONE · **Commit:** `839ba73`

Implementado en instrucción 209. Turn guard bloquea acciones fuera de turno; Extra Attack para martials ≥ lvl 5 respetado via `actions_remaining` + `consume_action()` + `turn_is_over()`. Detalle completo en `SAM_progress_log.md`.

### SAM-013 — Narrator inventa números en iniciativa

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `738f85f`

Implementado en instrucción 212. RULE 16 del narrator reforzada con "INITIATIVE GROUND TRUTH" — el `result` dentro de cada `<DM_ROLL>` es autoritativo, prosa y turn order deben citar números exactos, ties se resuelven por orden listado en los facts. Detalle en `SAM_progress_log.md`.

### SAM-001 — DM_ROLL chips apilados verticalmente

**Tipo:** BUG · **Prio:** P1 · **Estado:** DONE · **Commit:** `c215cc7`

Implementado en instrucción 213. `renderMessageContent` ahora cuenta los `<DM_ROLL>` del mensaje: si hay 2+, entra en modo HOIST — renderiza todos los chips en un `<div flex flex-col gap-1 my-2 items-start>` al inicio de la burbuja y abajo el texto narrativo con los tags removidos y el whitespace colapsado (spaces/tabs → 1 space, espacios antes de `\n` eliminados, `\n{3,}` → `\n\n`). Con 0 o 1 chip se mantiene el flujo inline anterior. Detalle en `SAM_progress_log.md`.
