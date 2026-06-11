# SAM — Auditoría de Multiplayer (pre-playtest grupal)

**Fecha:** 2026-06-11 · **Ticket:** SAM-047 · **Tipo:** diagnóstico read-only, sin fixes
**Contexto:** todo el testing hasta hoy fue single-player (un humano + Vex delegada a SAM). El playtest con Fekas será la primera vez con **dos clientes humanos concurrentes**. Este documento mapea lo que puede fallar, encontrado en lectura de código — no en vivo.

> Citas `archivo:línea` relativas a `projects/SAM/`. Líneas aproximadas al estado de `main` (commit `a4d8f73`).

---

## 0. Resumen ejecutivo

### ¿Está SAM listo para un playtest de 2 humanos? → **SÍ, CON RIESGOS.**

La infraestructura core de multiplayer **existe y es sólida**: mensajes filtrados por campaña con Realtime + dedup, lock por campaña que serializa las respuestas de SAM, turn guard server-side simétrico, atribución server-side por `user_id`, `state_updates` atómicos por `character_id` (SAM-044/029), XP dividido y loot por killer. Los gaps de la auditoría original (filtro por campaña, selector, header, roster, presence, invitaciones) están resueltos.

**Pero hay 1 bloqueante técnico real y 1 riesgo operativo serio:**

| | Hallazgo | Por qué importa con Fekas |
|--|----------|--------------------------|
| 🔴 **BLOQUEANTE** | **F2 — pendings sin dueño fuera de combate.** El turn guard solo valida la propiedad del `pending_player_roll` cuando `combat.active`. Fuera de combate (exploración: skill checks, hechizos, pociones), el pending de Björn lo consume **cualquier** dado que tire Fekas — resuelto con los stats del personaje equivocado. | La exploración con dos humanos tirando dados es el caso MÁS común de una sesión. Va a pasar en los primeros 10 minutos. **Fix corto (owner check en `process_player_roll`) → hacerlo ANTES del playtest.** |
| 🔴 **RIESGO OPERATIVO** | **F1 — comandos admin sin verificación de rol server-side.** El frontend bloquea `/reset|/checkpoint|/load|/list` para no-GM, pero el backend no verifica NADA. Un `/reset` de un no-GM vía API dispara el "nuclear wipe" (borra TODOS los mensajes) y además `reset_campaign` cura/resetea TODOS los personajes de la BD sin filtrar por campaña. | Con Fekas (confiable, usando la UI) la mitigación operativa alcanza: *"no uses comandos /"*. El fix server-side es necesario pero puede ir justo después del playtest. |

**Molestias tolerables** (no bloquean, anotar para la retro): roster con HP congelado del compañero (F8), posible doble-envío con lock lento + retry (F3), dup de comandos admin para el emisor (SAM-023), drift cosmético de HP narrado (SAM-022).

### Set mínimo pre-Fekas (recomendación)

1. **SAM-049** (P1, fix corto): validar `pending.character_name` contra quien tira en `process_player_roll`, SIEMPRE (no solo en combate). Único bloqueante técnico.
2. **Mitigación operativa de SAM-048**: brief a Fekas — no usar comandos `/`. (Fix server-side recomendado, post-playtest si hay apuro.)
3. **Brief de reglas de mesa**: si un jugador se desconecta a mitad de turno, el GM lo delega (`/delegate`) — es el escape diseñado (F14).
4. Todo lo demás → retro post-playtest.

---

## 1. Concurrencia y locking

**ESTADO ACTUAL:**
- Lock por campaña: `asyncio.Lock` en dict in-process (`server.py:82-88`), adquirido en `/api/chat` antes de leer historial/party y liberado en `finally` (`server.py:186-190`, `:472-475` aprox). El fetch de `party_characters`, el `process_message`, los `state_updates` (flush atómico SAM-044) y la persistencia de `combat_state` ocurren **dentro** del lock → dos mensajes simultáneos de Björn y Fekas se **serializan**: el segundo espera, no falla ni se pierde. El segundo además ve la respuesta de SAM al primero (historial se lee dentro del lock — diseño de la sesión 26 Mar).
- El INSERT del mensaje del usuario ocurre **antes** del lock (`server.py:133-146`) → ambos mensajes aparecen de inmediato vía Realtime aunque SAM responda en serie. Correcto.

**RIESGOS:**
- **F3 — doble envío por timeout + espera de lock sin tope.** El `authenticatedFetch` del frontend aborta a 30s (`lib/api.ts`); el lock espera sin límite. Cadena: Björn manda → SAM tarda 40s (interpreter+narrator+loot) → Fekas manda y queda encolado → el cliente de Fekas aborta a los 30s → toast con "Reintentar" → el reintento **inserta el mensaje de usuario otra vez** (el INSERT es pre-lock, sin idempotencia) → SAM responde dos veces. Con dos jugadores activos la ventana es real. **Severidad: MEDIA-ALTA.** → SAM-050.
- **F4 — el lock es in-process.** Correcto con 1 instancia/1 worker de Render (estado actual). Si algún día se escala a 2+ instancias o workers de uvicorn, el lock no cruza procesos → carrera real tipo SAM-044 pero entre jugadores. **Severidad: BAJA hoy, ALTA si se escala.** → nota en SAM-050 / ticket aparte P3.
- Los comandos admin (`/`) se ejecutan **antes** del lock (`server.py:149-182`) → un `/gold` puede intercalarse con un request de combate en curso. Menor (los flush por personaje de SAM-044 mitigan), pero existe la ventana.

**VEREDICTO:** serialización correcta para 2 humanos. El problema no es la carrera de datos sino la UX del lock lento (F3).

---

## 2. Turnos entre humanos

**ESTADO ACTUAL:** el turn guard (`orchestrator.py:83-102`) es **simétrico y server-side**: si `combat.active` y `sender_name != current_name`, bloquea `attack/spell/ability/start_combat/end_turn` y produce solo el recordatorio OUT_OF_TURN; los `dice_roll` solo pasan si `pending.character_name == sender_name`. No distingue humano vs NPC — **funciona igual para Björn vs Fekas en ambas direcciones**, aunque nunca se probó con dos humanos (la lógica no depende de eso).

**Cómo se entera el cliente de Fekas de que es su turno:** `combat_state` se persiste a `campaigns.settings.combat` (`server.py:387-396` región) → el cliente suscribe `campaigns` UPDATE vía Realtime (`game-layout.tsx:166-178`) → `combatState.current_turn` actualiza el banner y habilita/deshabilita el input (`chat-interface.tsx:106-114`, `:927-936`). **Push, sin refresh.** Si el Realtime se cae, el guard server-side igualmente rechaza acciones fuera de turno (defense in depth ✅).

**¿Robo de turno?** No para acciones mecánicas (lista del guard). `roleplay/movement/free_action` de un jugador fuera de turno pasan al narrador (by design: charlar durante el turno ajeno está bien; el fact de "Combat is active. It's X's turn" mantiene el foco).

**RIESGO menor:** cuando es turno de un NPC, `isMyTurn` es `true` para **todos** (`chat-interface.tsx:113`: `isNpcTurn → habilitado`) — ventana brevísima porque los turnos NPC se resuelven dentro del request del jugador anterior. Tolerable.

**VEREDICTO:** ✅ listo. Sin ticket.

---

## 3. Iniciativa con múltiples humanos

**ESTADO ACTUAL:** `_handle_start_combat` (`orchestrator.py:468+`) rolea iniciativa para **todos** los `party_characters` (humanos y delegados) con su DEX real (SAM-018 fixed) + el NPC, emite un `<DM_ROLL>` por combatiente y la lista ordenada en los facts. El mensaje narrado se inserta en `messages` → **ambos clientes lo reciben por Realtime**. El orden vive en una sola fuente (`settings.combat.initiative_order`) → el banner de ambos clientes muestra **exactamente lo mismo** (`chat-interface.tsx:820-843`).

**RIESGO:** ninguno técnico. **SAM-019** (iniciativa manual — que cada humano tire la suya) sigue OPEN como decisión de diseño; el auto-roll funciona para el playtest y de hecho simplifica la primera sesión con dos humanos.

**VEREDICTO:** ✅ listo (auto-roll). SAM-019 queda para después.

---

## 4. Realtime y sincronización

**ESTADO ACTUAL:**
- **Mensajes:** ambos clientes suscriben `messages` filtrado por `campaign_id` (`chat-interface.tsx:188-193`), dedup por `id` de BD, resync con `fetchHistory` al volver de background/online (`:527-558`). ✅
- **Combat state:** suscripción a `campaigns` UPDATE (`game-layout.tsx:166-178`). ✅
- **HP propio:** suscripción a `characters` UPDATE (`game-layout.tsx:136-164`) que solo aplica si `id === selectedCharacter.id`, + re-fetch del personaje 1.5s después de cada mensaje de SAM (`handleSamMessageReceived`). ✅
- **HP del COMPAÑERO (F8):** el party roster hace **UN solo fetch al montar** (`party-roster.tsx:34-52`) — sin Realtime, sin polling, sin re-fetch on message. La suscripción global de `characters` en game-layout RECIBE los updates de Fekas pero los **descarta** (solo mira el selectedCharacter). → **Björn no ve bajar el HP de Fekas en el roster sin F5.** El COMBAT STATUS narrado sí refleja a ambos (server-side), así que la info llega por la narración — pero el panel queda stale. **Severidad: MEDIA (UX).** → SAM-052.
- **¿Estado solo-cliente sin sincronizar?** `selectedCharacter` en localStorage (se resincroniza on mount/visibility); los mensajes en memoria (resync por visibility). Sin estado de juego crítico solo-cliente. ✅
- **¿Aplicación de updates al espectador?** El path nuevo (`state_updates` server-side por `character_id`, SAM-029/044) escribe en la fila correcta de la BD — **resuelto para ambos**. El riesgo residual es el parser client-side legacy de `<UPDATE>/<LOOT>` (`chat-interface.tsx:252-457`): bajo fallback legacy, **ambos** clientes aplicarían el mismo tag a **su propio** personaje (doble aplicación cruzada). Hoy el fallback es raro (0 desde SAM-017), pero con 2 clientes el blast radius se duplica. → ya trackeado en **SAM-024** (mantener P2, anotar el agravante).
- **F16 (menor):** las suscripciones de `characters` y `campaigns` en game-layout no tienen `filter` → cada browser recibe los eventos de TODAS las campañas (ruido + payloads ajenos llegan al cliente). P3, juntar con SAM-052.

**VEREDICTO:** mensajes/turnos ✅; roster de HP ajeno stale (SAM-052, tolerable para el playtest porque la narración + COMBAT STATUS llevan la verdad).

---

## 5. Atribución de acciones

**ESTADO ACTUAL:** el backend atribuye por `user_id` del JWT — busca el personaje del usuario en la BD (`server.py:115-121`) y de ahí salen `cid` y `char_name` (el `sender_name` del orchestrator y del turn guard). El `[SYSTEM EVENT]` del dice tray incluye el nombre del personaje (`dice-tray.tsx:32,49`) y el interpreter lo extrae, pero **la autoridad es el lookup server-side por `user_id`** — Fekas no puede atribuirse el personaje de Björn ni aunque manipule el texto. ✅

**RIESGO — F5:** el lookup toma el **primer** personaje del usuario (`limit(1)`, `server.py:117`) sin que el frontend mande `character_id`/`campaign_id` en `/api/chat`. Si un usuario tiene 2+ personajes (p.ej. en dos campañas), la atribución puede salir del personaje/campaña equivocada. **Para el playtest (un personaje por usuario): inocuo.** **Severidad: MEDIA a futuro.** → SAM-051.

**VEREDICTO:** ✅ para el playtest (1 personaje por humano). SAM-051 para multi-personaje.

---

## 6. Pending rolls entre jugadores — 🔴 EL HALLAZGO PRINCIPAL

**ESTADO ACTUAL:** `pending_player_roll` es **uno solo por campaña** (vive en `combat_dict`, persiste entre requests). El dueño se estampa (`character_name`) en los pendings de attack/damage/skill/self_damage/freeform. La validación de propiedad existe **solo en el turn guard**, y el turn guard corre **solo si `combat.active`** (`orchestrator.py:83`). `process_player_roll` (`mechanic.py`) consume el pending sin mirar el dueño.

**RIESGO — F2 (BLOQUEANTE):** **fuera de combate**, cualquier dado de cualquier jugador consume el pending ajeno:
1. Björn: "reviso la puerta" → SAM: "tira Perception" → pending `skill_check` (owner: Björn).
2. Fekas tira un d20 por cualquier motivo (curiosidad, su propio check pedido en otra línea, el dado equivocado).
3. `process_player_roll(character=Fekas, ...)` consume el pending de Björn → el check de Björn se resuelve **con los modificadores de Fekas**, y el pending real de Fekas (si lo había) se perdió.

Lo mismo aplica a pendings de `healing` (poción), `self_damage` y `spell_*` fuera de combate. En exploración con 2 humanos esto ocurre **temprano y seguido**. Además, en combate la validación del guard solo cubre `dice_roll` cuando hay pending — pero los pendings de spell (`spell_damage`/`spell_attack` de `process_spell`) **no estampan `character_name`** → el guard los trata como sin dueño (bloquea al otro jugador por `None != sender`, lo cual funciona de casualidad, pero es frágil).

**Severidad: ALTA.** → **SAM-049 (P1, pre-playtest):** validar `pending.character_name` contra el roller en `process_player_roll` SIEMPRE (combate o no); si no coincide → tratar el dado como `freeform_roll` del que tiró (no consumir el pending ajeno, no rechazar al legítimo). Estampar `character_name` también en los pendings de spell.

---

## 7. Comandos admin en multiplayer — 🔴 SIN VERIFICACIÓN SERVER-SIDE

**ESTADO ACTUAL:**
- El frontend bloquea `/reset|/checkpoint|/load|/list` para no-GM (`chat-interface.tsx:593-599`) — **client-side only**. `/delegate`, `/gold`, `/memory` ni siquiera están en esa lista (el backend los degrada con "No active campaign found for GM" porque resuelven por `gm_id` — fallo seguro ✅).
- El interceptor de comandos del backend (`server.py:149-182`) y `AdminService.handle_command` (`admin.py:16+`) **no verifican rol/GM en absoluto**.

**RIESGO — F1 (CRÍTICO como deuda, OPERATIVO para el playtest):**
- `/reset` por un **no-GM vía API**: `camp_res` (por `gm_id`) sale vacío → pass 1 (por campaña) se saltea → pass 3 "nuclear" detecta mensajes remanentes y **borra TODOS los mensajes de TODAS las campañas** (`admin.py:209-215`). Además el paso 1 de curación recorre **todos los personajes de la BD sin filtro de campaña** (`admin.py:181-191`) curando y reseteando money/XP de todos — esto pasa incluso con el GM legítimo (hoy hay una sola campaña activa, por eso nunca dolió).
- `/checkpoint` snapshotea TODOS los personajes sin filtro (`admin.py:122`); `/load` borra y restaura mensajes por `user_id` (`admin.py:167-169`) — scoping inconsistente.
- **SAM-023** (dup del emisor) no empeora con 2 clientes: el otro jugador lo ve UNA vez (sin append optimista en su pantalla); la inconsistencia entre pantallas se nota más, nada nuevo.

**Severidad: P1.** → **SAM-048:** verificación de GM server-side en el interceptor (o en `handle_command`) + scoping por campaña de `/reset`/`/checkpoint`. **Mitigación pre-playtest:** Fekas usa la UI (los 4 comandos grandes están bloqueados client-side) + brief "no uses comandos /".

---

## 8. XP / loot / HP con múltiples jugadores

**ESTADO ACTUAL:**
- **XP:** `award_xp` divide ceil entre **todos** los `party_characters` del campaign (`mechanic.py:675+`) — presentes o no. Si Fekas se desconecta a mitad de combate, su personaje sigue en la tabla → recibe su parte igual. Decisión razonable (no hay concepto de "presente"); documentar como regla de mesa. ✅
- **Loot/killer:** `update_npc_hp(..., killer=character.name)` desde los 4 kill-sites → si Fekas da el golpe final, `_killed_by` = su personaje y el `item_award` va a su `character_id` (`orchestrator.py:_award_loot`, con `killer_pc` dict de SAM-029). Validado en prod con Vex (mismo path). ✅
- **HP cruzado:** `state_updates` se aplican por `character_id` con flush atómico por personaje (SAM-044/029) → **el HP de Fekas no puede escribirse en la fila de Björn**. ✅
- El residual conocido: COMBAT STATUS narrado con HP de jugador stale (SAM-022, cosmético) — con 2 humanos se nota el doble (cada uno escucha narrar su HP viejo). Sigue P2.

**VEREDICTO:** ✅ listo. Sin tickets nuevos.

---

## 9. Presence y roster

**ESTADO ACTUAL:** Presence **existe** (gap original resuelto en `264477b`): `usePresence` (`game-layout.tsx:44`) trackea por campaña vía Supabase Presence; el roster muestra punto verde/gris en vivo. ✅
**Pero** (F8, §4): los **datos** del roster (HP/level del compañero) son un fetch único al montar — la presencia es live, el HP no. → SAM-052.
**SAM-040** (delegación invisible) es directamente relevante: si Vex sigue delegada de una sesión anterior, ni Björn ni Fekas lo ven. Brief pre-playtest: correr `/undelegate` de lo que no deba estar delegado, o revisar con `/delegate`-status mental. Sigue OPEN P2.

---

## 10. Gaps de la auditoría original (SAM-020 / assessment)

| Gap original | Estado hoy | ¿Bloquea playtest de 2? |
|--------------|-----------|------------------------|
| Filtro de mensajes por campaign_id | ✅ resuelto (`4b4c318`) | No |
| Selector de campaña | ✅ resuelto (`4211de3`) | No |
| Header dinámico | ✅ resuelto | No |
| Roster de jugadores | ✅ existe — ⚠️ HP estático (F8/SAM-052) | No (molestia) |
| Presence indicators | ✅ resuelto (`264477b`) | No |
| Campaign join/invite | ✅ resuelto (códigos de invitación) | No |
| Commlink recipients | ✅ resuelto; SAM-011 (realtime/mark-read) abierto | No (refresh manual) |
| **Membership table** | ❌ sigue informal (la pertenencia se infiere de `characters.campaign_id`) | **No** para 2 jugadores; deuda para escalar |

---

## 11. Tabla consolidada de hallazgos

| # | Hallazgo | Severidad | Ticket | ¿Pre-Fekas? |
|---|----------|-----------|--------|-------------|
| F2 | Pendings sin validación de dueño fuera de combate → cross-player consumption | 🔴 ALTA | **SAM-049** (P1) | **SÍ — bloqueante** |
| F1 | Comandos admin sin verificación de rol server-side; `/reset` no-GM = nuclear wipe; `reset/checkpoint` sin scope de campaña | 🔴 ALTA (deuda) | **SAM-048** (P1) | Mitigación operativa sí; fix puede ser post |
| F3 | Doble envío: INSERT pre-lock + lock sin tope + retry del cliente a 30s | 🟠 MEDIA-ALTA | **SAM-050** (P2) | No (brief: no spamear reintentar) |
| F8 | Roster con HP del compañero congelado (fetch único, sin Realtime) | 🟠 MEDIA (UX) | **SAM-052** (P2) | No (la narración lleva la verdad) |
| F5 | Atribución por primer personaje del usuario (`limit 1`), sin character_id en el request | 🟠 MEDIA (futuro) | **SAM-051** (P2) | No (1 personaje c/u) |
| F4 | Lock in-process — no cruza instancias/workers si se escala | 🟡 BAJA hoy | nota en SAM-050 | No |
| F16 | Subscripciones `characters`/`campaigns` sin filtro (ruido + payloads ajenos al browser) | 🟡 BAJA | junto a SAM-052 | No |
| F6 | `<UPDATE>` legacy client-side pega al espectador — doble aplicación con 2 clientes | 🟡 BAJA (fallback raro) | **SAM-024** (existente) | No |
| F7 | Dup de respuesta admin para el emisor | 🟡 BAJA | **SAM-023** (existente) | No |
| F14 | Desconexión a mitad de turno → combate espera; escape = `/delegate` del GM | 🟢 operativo | nota en SAM-040 | Brief sí |
| — | Turnos, iniciativa, XP/loot/HP, atribución, Realtime de mensajes | ✅ OK | — | — |

## 12. Tickets propuestos

- **SAM-047** — esta auditoría (DONE).
- **SAM-048** (BUG/SEC · P1): verificación de GM **server-side** para comandos admin + scope por campaña en `/reset` (curación de personajes y borrado de mensajes solo de la campaña del GM; eliminar el pass 3 "nuclear" o scoping estricto) y `/checkpoint`/`/load`.
- **SAM-049** (BUG · P1 · **pre-playtest**): `process_player_roll` valida `pending.character_name` contra el personaje que tira, SIEMPRE (no solo turn guard en combate). Mismatch → el dado se procesa como `freeform_roll` del que tiró, el pending ajeno queda intacto. Estampar `character_name` en los pendings de spell (`process_spell`/`_resolve_spell_attack`, hoy sin dueño).
- **SAM-050** (BUG · P2): anti doble-envío — idempotencia del INSERT del mensaje de usuario (o mover el INSERT dentro del lock con dedup), y/o timeout del lock con respuesta "SAM está ocupado". Nota: el lock es in-process; si Render escala a 2+ instancias se necesita lock distribuido (advisory lock de Postgres).
- **SAM-051** (REFACTOR · P2): `/api/chat` debe llevar `character_id`/`campaign_id` explícitos desde el frontend; el backend valida pertenencia en vez de `limit(1)`.
- **SAM-052** (UX · P2): roster del party en vivo — refrescar HP del compañero vía la suscripción de `characters` existente (con filtro por campaña) o re-fetch on SAM message; de paso, filtrar las suscripciones de `characters`/`campaigns` por campaña (F16).

## 13. Protocolo recomendado para el playtest con Fekas

1. **Antes:** fix SAM-049 desplegado. `/undelegate` de personajes que no deban estar delegados (SAM-040). `/reset` limpio por el GM.
2. **Brief a Fekas:** no usar comandos `/` (F1); si SAM tarda, no spamear "Reintentar" (F3); el HP del compañero en el roster puede verse viejo — la narración manda (F8).
3. **Durante:** monitorear logs de Render: `🔒/🔓` (lock), `OUT_OF_TURN`, `⛔ Invalid dice`, `💾 Status flushed`, y cualquier `⚠️ Orchestrator failed`.
4. **Después:** retro contra la tabla §11 — los hallazgos F3/F5/F8 tienen ticket listo para priorizar con evidencia real.

---

*Auditoría SAM-047 — 2026-06-11. Read-only, sin cambios de código. 5 tickets nuevos propuestos (SAM-048–052). Veredicto: SÍ-CON-RIESGOS — un bloqueante técnico (SAM-049) y un brief operativo (SAM-048) separan a SAM de su primer playtest a dos humanos.*
