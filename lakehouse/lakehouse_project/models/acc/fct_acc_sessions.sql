-- Gold Layer: Resumen por sesión ACC
-- Métricas agregadas de toda la sesión

{{ config(materialized='table') }}

WITH laps AS (
    SELECT * FROM {{ ref('fct_acc_laps') }}
),

session_stats AS (
    SELECT
        source_file,
        source_path,
        track,
        car,
        session_date,
        
        -- Vueltas
        COUNT(*) AS total_laps,
        SUM(samples) AS total_samples,
        SUM(lap_duration_sec) AS total_time_sec,
        
        -- Mejor vuelta (por velocidad promedio)
        MAX(avg_speed_kmh) AS best_avg_speed_kmh,
        
        -- Velocidad
        MAX(top_speed_kmh) AS session_top_speed_kmh,
        AVG(avg_speed_kmh) AS session_avg_speed_kmh,
        STDDEV(avg_speed_kmh) AS speed_consistency_std,
        
        -- Throttle
        AVG(full_throttle_pct) AS avg_full_throttle_pct,
        
        -- Brake
        AVG(braking_pct) AS avg_braking_pct,
        
        -- G-Forces
        MAX(max_g_lateral) AS session_max_g_lat,
        MAX(max_g_longitudinal) AS session_max_g_lon,
        
        -- Neumáticos
        AVG(avg_tyre_temp_front) AS session_avg_tyre_temp_front,
        AVG(avg_tyre_temp_rear) AS session_avg_tyre_temp_rear,
        MAX(max_tyre_temp_lf) AS session_max_tyre_temp_lf,
        MAX(max_tyre_temp_rf) AS session_max_tyre_temp_rf,
        MAX(max_tyre_temp_lr) AS session_max_tyre_temp_lr,
        MAX(max_tyre_temp_rr) AS session_max_tyre_temp_rr
        
    FROM laps
    GROUP BY 1, 2, 3, 4, 5
)

SELECT 
    *,
    -- Índice de consistencia (menor es mejor)
    ROUND(speed_consistency_std / session_avg_speed_kmh * 100, 2) AS consistency_index
FROM session_stats
ORDER BY session_date DESC
