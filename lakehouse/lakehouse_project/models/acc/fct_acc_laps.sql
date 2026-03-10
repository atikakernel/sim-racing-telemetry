-- Gold Layer: Métricas por vuelta ACC
-- Agregados para análisis de performance

{{ config(materialized='table') }}

WITH telemetry AS (
    SELECT * FROM {{ ref('stg_acc_telemetry') }}
),

-- Detectar vueltas basado en lap_beacon o segmentos de tiempo
lap_segments AS (
    SELECT 
        *,
        SUM(CASE WHEN lap_beacon > 0 THEN 1 ELSE 0 END) 
            OVER (PARTITION BY source_file ORDER BY sample_index) AS lap_number
    FROM telemetry
),

lap_stats AS (
    SELECT
        source_file,
        source_path,
        track,
        car,
        session_date,
        lap_number,
        
        -- Samples
        COUNT(*) AS samples,
        MIN(time_ms) AS lap_start_ms,
        MAX(time_ms) AS lap_end_ms,
        (MAX(time_ms) - MIN(time_ms)) / 1000.0 AS lap_duration_sec,
        
        -- Velocidad
        MAX(speed_kmh) AS top_speed_kmh,
        AVG(speed_kmh) AS avg_speed_kmh,
        MIN(speed_kmh) AS min_speed_kmh,
        
        -- Throttle
        AVG(throttle_pct) AS avg_throttle_pct,
        SUM(CASE WHEN throttle_pct > 99 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS full_throttle_pct,
        
        -- Brake
        AVG(brake_pct) AS avg_brake_pct,
        SUM(CASE WHEN brake_pct > 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS braking_pct,
        MAX(brake_pct) AS max_brake_pct,
        
        -- G-Forces
        MAX(ABS(g_lateral)) AS max_g_lateral,
        MAX(ABS(g_longitudinal)) AS max_g_longitudinal,
        AVG(ABS(g_lateral)) AS avg_g_lateral,
        
        -- Neumáticos - Temps promedio
        AVG(tyre_temp_lf) AS avg_tyre_temp_lf,
        AVG(tyre_temp_rf) AS avg_tyre_temp_rf,
        AVG(tyre_temp_lr) AS avg_tyre_temp_lr,
        AVG(tyre_temp_rr) AS avg_tyre_temp_rr,
        
        -- Neumáticos - Temps max
        MAX(tyre_temp_lf) AS max_tyre_temp_lf,
        MAX(tyre_temp_rf) AS max_tyre_temp_rf,
        MAX(tyre_temp_lr) AS max_tyre_temp_lr,
        MAX(tyre_temp_rr) AS max_tyre_temp_rr,
        
        -- Frenos
        MAX(brake_temp_lf) AS max_brake_temp_lf,
        MAX(brake_temp_rf) AS max_brake_temp_rf,
        MAX(brake_temp_lr) AS max_brake_temp_lr,
        MAX(brake_temp_rr) AS max_brake_temp_rr,
        
        -- RPM
        MAX(rpm) AS max_rpm,
        AVG(rpm) AS avg_rpm
        
    FROM lap_segments
    WHERE lap_number > 0  -- Excluir vuelta de salida
    GROUP BY 1, 2, 3, 4, 5, 6
)

SELECT 
    *,
    -- Métricas derivadas
    ROUND(avg_speed_kmh / top_speed_kmh * 100, 1) AS speed_efficiency_pct,
    ROUND((avg_tyre_temp_lf + avg_tyre_temp_rf) / 2, 1) AS avg_tyre_temp_front,
    ROUND((avg_tyre_temp_lr + avg_tyre_temp_rr) / 2, 1) AS avg_tyre_temp_rear,
    ROUND(avg_tyre_temp_rear - ((avg_tyre_temp_lf + avg_tyre_temp_rf) / 2), 1) AS tyre_temp_balance
FROM lap_stats
ORDER BY source_file, lap_number
