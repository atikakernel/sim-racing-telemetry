-- Silver Layer: Telemetría ACC limpia
-- Filtra datos en movimiento, tipos correctos

{{ config(materialized='table') }}

WITH raw_data AS (
    SELECT * FROM {{ source('bronze', 'bronze_acc_telemetry') }}
    WHERE "SPEED" IS NOT NULL 
      AND "SPEED" > 2.78  -- >10 km/h en m/s
),

cleaned AS (
    SELECT
        -- Metadata
        "_source_file" AS source_file,
        "_source_path" AS source_path,
        "_track" AS track,
        "_car" AS car,
        "_session_date" AS session_date,
        "_sample_index" AS sample_index,
        
        -- Tiempo (SPEED se graba a 60Hz = 16.667ms por sample)
        ROUND(CAST("_sample_index" AS DOUBLE) * 16.667, 0) AS time_ms,
        
        -- Conducción (SPEED viene en m/s, convertir a km/h)
        CAST("SPEED" AS DOUBLE) * 3.6 AS speed_kmh,
        CAST("THROTTLE" AS DOUBLE) AS throttle_pct,
        CAST("BRAKE" AS DOUBLE) AS brake_pct,
        CAST("STEERANGLE" AS DOUBLE) AS steer_angle,
        CAST("GEAR" AS INTEGER) AS gear,
        CAST("CLUTCH" AS DOUBLE) AS clutch_pct,
        CAST("RPMS" AS INTEGER) AS rpm,
        
        -- G-Forces
        CAST("G_LAT" AS DOUBLE) AS g_lateral,
        CAST("G_LON" AS DOUBLE) AS g_longitudinal,
        
        -- Electrónica
        CAST("TC" AS INTEGER) AS tc_level,
        CAST("ABS" AS INTEGER) AS abs_level,
        
        -- Neumáticos - Temperaturas
        CAST("TYRE_TAIR_LF" AS DOUBLE) AS tyre_temp_lf,
        CAST("TYRE_TAIR_RF" AS DOUBLE) AS tyre_temp_rf,
        CAST("TYRE_TAIR_LR" AS DOUBLE) AS tyre_temp_lr,
        CAST("TYRE_TAIR_RR" AS DOUBLE) AS tyre_temp_rr,
        
        -- Neumáticos - Presiones
        CAST("TYRE_PRESS_LF" AS DOUBLE) AS tyre_press_lf,
        CAST("TYRE_PRESS_RF" AS DOUBLE) AS tyre_press_rf,
        CAST("TYRE_PRESS_LR" AS DOUBLE) AS tyre_press_lr,
        CAST("TYRE_PRESS_RR" AS DOUBLE) AS tyre_press_rr,
        
        -- Frenos - Temperaturas
        CAST("BRAKE_TEMP_LF" AS DOUBLE) AS brake_temp_lf,
        CAST("BRAKE_TEMP_RF" AS DOUBLE) AS brake_temp_rf,
        CAST("BRAKE_TEMP_LR" AS DOUBLE) AS brake_temp_lr,
        CAST("BRAKE_TEMP_RR" AS DOUBLE) AS brake_temp_rr,
        
        -- Velocidad ruedas
        CAST("WHEEL_SPEED_LF" AS DOUBLE) AS wheel_speed_lf,
        CAST("WHEEL_SPEED_RF" AS DOUBLE) AS wheel_speed_rf,
        CAST("WHEEL_SPEED_LR" AS DOUBLE) AS wheel_speed_lr,
        CAST("WHEEL_SPEED_RR" AS DOUBLE) AS wheel_speed_rr,
        
        -- Lap detection
        CAST("LAP_BEACON" AS DOUBLE) AS lap_beacon
        
    FROM raw_data
)

SELECT * FROM cleaned
