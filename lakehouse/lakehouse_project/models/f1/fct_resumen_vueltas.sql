-- models/f1/fct_resumen_vueltas.sql

{{ config(
    materialized='incremental',
    unique_key='inicio_vuelta'
) }}

WITH silver AS (
    -- Lee los datos de la vuelta ACTUAL que acabamos de cargar
    SELECT * FROM {{ ref('stg_telemetry') }}
),

resumen_vuelta_actual AS (
    SELECT
        MIN(fecha_hora) as inicio_vuelta,
        MAX(velocidad_kmh) as top_speed,
        CAST(AVG(velocidad_kmh) AS INTEGER) as avg_speed,
        
        -- Cálculo de % a fondo
        ROUND(
            (COUNT(CASE WHEN acelerador_pct > 0.99 THEN 1 END) * 100.0) / COUNT(*)
        , 1) as full_throttle_pct,
        
        MAX(rpm) as max_rpm

    FROM silver
)

SELECT * FROM resumen_vuelta_actual

-- Lógica Incremental:
-- Si dbt detecta que la tabla ya existe, solo inserta la fila si el 'inicio_vuelta' NO está ya guardado.
{% if is_incremental() %}
  WHERE inicio_vuelta NOT IN (SELECT inicio_vuelta FROM {{ this }})
{% endif %}