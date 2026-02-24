# Registro de Progreso: S.A.M. (Storytelling AI Master)

Este documento sirve como bitácora y resumen del estado actual del proyecto S.A.M., recopilando todo lo construido hasta la fecha para mantener el contexto claro, especialmente tras el cambio de sesión de chat.

## 1. Visión General del Proyecto
S.A.M. es una aplicación web diseñada para actuar como un Dungeon Master (Director de Juego) impulsado por Inteligencia Artificial para partidas de rol (D&D SRD), priorizando una arquitectura de bajo costo (Free Tiers).

## 2. Arquitectura Establecida
La arquitectura actual se basa en:
- **Frontend:** Next.js (TypeScript) desplegado en **Vercel**.
- **Backend:** Python (FastAPI/Motor de juego) desplegado en **Render**.
- **Base de Datos:** **Supabase** (PostgreSQL) con `pgvector` para Búsqueda Vectorial (RAG) y autenticación.
- **Modelo de IA:** Google Gemini API (Flash 1.5/2.0) por su gran ventana de contexto y bajo costo.

## 3. Estado Actual del Sistema (Lo Construido)

### A. Frontend (`projects/SAM/frontend/`)
- Proyecto Next.js inicializado.
- Archivos de configuración básicos listos (`next.config.ts`, `tailwind.config`, `package.json`).
- Estructura de componentes y hooks en preparación.

### B. Backend (`projects/SAM/backend/`)
- Servidor central implementado (`server.py`).
- Módulo de administración y utilidades (`app/services/admin.py`, scripts de verificación).
- **Integración RAG y Modelos de IA:** Scripts para probar e interactuar con Gemini (`check_models.py`, `test_models.py`).
- **Base de Datos (SQL):** Extensa definición de esquemas SQL construidos iterativamente:
  - `schema.sql`, `schema_game_engine.sql`
  - `schema_multimedia.sql`, `schema_google_migration.sql`
  - `rag_schema.sql` (Para el sistema de Retrieval-Augmented Generation con `pgvector`)
  - Migraciones y correcciones por fases (`phase9`, `phase10`, `phase11`).

## 4. Problemas Actuales y Diagnóstico (Febrero 2026)

### A. Problema de Despliegue en Vercel
- **Error:** `The specified Root Directory "frontend" does not exist. Please update your Project Settings.`
- **Causa:** Vercel está buscando la carpeta `frontend` en la raíz del repositorio de GitHub (`dungeon-master-ai`), pero la estructura real dentro del repositorio es `projects/SAM/frontend`.
- **Solución Requerida:** Actualizar la configuración del proyecto en Vercel (Project Settings > Root Directory) para que apunte a `projects/SAM/frontend`.

### B. Problema de Despliegue en Render (Desactualizado)
- **Estado:** Último deploy registrado en junio de 2026 (potencial error de fecha o despliegue antiguo atascado).
- **Causa probable:** Debido a la confusión anterior con los múltiples remotos (`Antigravity.git` vs `dungeon-master-ai.git`), Render no ha estado recibiendo los *pushes* recientes del código del backend que está en `projects/SAM/backend`.
- **Solución Requerida:** 
  1. Confirmar que Render está conectado al repositorio correcto (`Mitiakamara/dungeon-master-ai`).
  2. Ajustar el "Root Directory" en Render a `projects/SAM/backend`.
  3. Ajustar el "Build Command" (ej. `pip install -r requirements.txt`) y el "Start Command" (ej. `uvicorn server:app --host 0.0.0.0 --port $PORT`).
  4. Realizar un nuevo `git push` para forzar el despliegue.

---
*Documento generado el 20 de Febrero de 2026.*
