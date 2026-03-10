-- models/f1/stg_telemetry.sql

WITH source AS (
    -- Referenciamos la tabla RAW que creó tu Python
    SELECT * FROM raw_telemetry
)

SELECT
    "timestamp" AS tiempo_unix,
    -- Convertimos a timestamp legible
    strftime(to_timestamp(CAST("timestamp" AS BIGINT)), '%Y-%m-%d %H:%M:%S') as fecha_hora,
    
    -- Limpieza de tipos
    CAST(speed_kmh AS INTEGER) AS velocidad_kmh,
    CAST(throttle AS FLOAT) / 100 AS acelerador_pct,
    CAST(brake AS FLOAT) / 100 AS freno_pct,
    CAST(gear AS INTEGER) AS marcha,
    CAST(rpm AS INTEGER) as rpm

FROM source