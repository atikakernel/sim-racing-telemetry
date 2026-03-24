
-- Este modelo lee directamente del Parquet generado por Spark
WITH raw_data AS (
    SELECT * 
    FROM read_parquet('/home/diegokernel/proyectos/spark_airflow_telemetry/data/processed/vehicle_telemetry_agg/*.parquet')
)

SELECT 
    VehId,
    Trip,
    avg_speed_kmh,
    max_rpm,
    total_fuel_rate,
    -- Creamos una métrica inventada
    CASE 
        WHEN max_rpm > 3000 THEN 'High Intensity'
        WHEN max_rpm > 2000 THEN 'Normal'
        ELSE 'Eco'
    END AS driving_style
FROM raw_data
WHERE total_fuel_rate IS NOT NULL OR avg_speed_kmh > 0
