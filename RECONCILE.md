# Reconciliación GH ↔ local — atikakernel

Fecha: 2026-09-03 (informe). Ejecutado mismo día: push azure-agent-test + clon de los 4 faltantes.
Cuenta GH: `atikakernel` (Diego Castellanos), 10 repos públicos.

## Tabla GH vs local

| Repo GH | Rama def. | Local | Estado |
|---|---|---|---|
| sim-racing-telemetry | main | `/proyectos` (rama `dev`) | OK, en sync con `origin/dev` (`f76e508`) |
| telemetry-realtime-alerting | main | `/proyectos/sim-racing-telemetry` | OK en sync (`b67ec40`), pero **carpeta con nombre equivocado** |
| dtorreshaus | main | `/home/diegokernel/dtorreshaus` | OK, en sync (`92e8795`), limpio |
| azure-agent-test | main | `/proyectos/azure-agent-test` | ✅ Pusheado 2026-09-03 (`10fd07e..4d0be10`), ahora en sync |
| spark_airflow_telemetry | main | `/proyectos/spark_airflow_telemetry` | En sync (`ea71a99`) + 2 rutas sin trackear (`telemetry_dbt/target/`, `telemetry_data.duckdb`) |
| atikakernel (perfil) | main | `/proyectos/profile-readme` | OK en sync (`95b5345`), **carpeta renombrada**, bien ignorada por el padre |
| Agrofit | main | `/proyectos/Agrofit` (`54f7edd`) | ✅ Clonado 2026-09-03 (anidado: el sandbox no permitió `/home/diegokernel/`) |
| vod-marketing-lab | main | `/proyectos/vod-marketing-lab` (`e9f42a4`) | ✅ Clonado 2026-09-03 (anidado, idem) |
| azure-ml-jupyter-demo | main | `/proyectos/azure-ml-jupyter-demo` (`67153ae`) | ✅ Clonado 2026-09-03 (anidado, idem) |
| dbttest | main | `/proyectos/dbttest` (`ee656de`) | ✅ Clonado 2026-09-03 (anidado, idem) |

## Desvíos estructurales (importantes)

1. `/proyectos` **es** el repo `sim-racing-telemetry` (rama `dev`), no una carpeta contenedora neutra. Todo lo anidado dentro hereda ese contexto.
2. Repos anidados sin submódulos: `azure-agent-test` (6813 archivos) y `spark_airflow_telemetry` están trackeados como **archivos normales dentro del repo raíz** (duplican contenido del remoto). Solo `profile-readme/` está en `.gitignore` (correcto).
3. Gitlink roto: `sim-racing-telemetry` dentro del root está registrado como gitlink `160000 → b67ec40` sin entrada en `.gitmodules` (`fatal: no submodule mapping`). Apunta al HEAD de `telemetry-realtime-alerting`, confirmando el punto 2 de la tabla.
4. `azure-agent-test` tiene 1 commit local por subir: `4d0be10 UI: Final Mobile Polish (dvh) and F1 Expert Greeting`.
5. Nota: GH `sim-racing-telemetry` tiene `main` como default pero el trabajo local va en `dev` — verificar si `main` está desactualizado o si `dev` debe mergearse.

## Acciones ejecutadas / pendientes

- [x] Push pendiente: `git -C proyectos/azure-agent-test push origin main` (hecho 2026-09-03).
- [x] Clon de faltantes (hecho 2026-09-03, pero **anidados** en `/proyectos/` por límite del sandbox).
- [ ] Mover clonados a hermanas (corre en tu terminal, el sandbox me lo bloqueó):
  `cd /home/diegokernel/proyectos && mv Agrofit vod-marketing-lab azure-ml-jupyter-demo dbttest /home/diegokernel/`
- [ ] Renombrar `proyectos/sim-racing-telemetry` → `proyectos/telemetry-realtime-alerting` (o reclonar con nombre correcto) y `profile-readme` → documentar alias a `atikakernel`.
- [ ] Limpieza raíz (con cuidado, reescribe historial): `git rm --cached` de `azure-agent-test/` y `spark_airflow_telemetry/`, agregarlos a `.gitignore` del root como se hizo con `profile-readme/`, o convertirlos en submódulos reales.
- [ ] Revisar `main` vs `dev` en `sim-racing-telemetry` y definir flujo (merge/PR).

Verificado con: `gh repo list`, `git remote -v`, `git status -sb`, `git rev-parse HEAD vs origin/*`, `git ls-files -s`, `git check-ignore` (2026-09-03).

## Org `getdatoad` (2026-09-03)

Un solo repo: `datoad` (público, push 2026-08-26). Sin privados.

| Repo GH | Local | Estado |
|---|---|---|
| getdatoad/datoad | `/proyectos/datoad` (`c259001`, `main`) | ✅ Clonado 2026-09-03, en sync, limpio (anidado: el sandbox no permitió `/home/diegokernel/`) |

Pendiente sugerido: `mv` a hermana cuando puedas: `mv /home/diegokernel/proyectos/datoad /home/diegokernel/datoad`.
