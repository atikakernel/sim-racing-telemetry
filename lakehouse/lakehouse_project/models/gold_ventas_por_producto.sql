{{ config(
    materialized='table',
    pre_hook="
      INSTALL httpfs;
      LOAD httpfs;
      CREATE OR REPLACE SECRET minio_secret (
          TYPE S3,
          PROVIDER CONFIG,
          KEY_ID 'admin',
          SECRET 'password123',
          REGION 'us-east-1',
          ENDPOINT 'localhost:9000',
          URL_STYLE 'path',
          USE_SSL false
      );
    "
) }}

WITH silver_data AS (
    SELECT * FROM delta_scan('s3://silver/ventas_delta')
)

SELECT 
    product_name,
    COUNT(*) as total_transacciones,
    SUM(amount) as ventas_totales,
    AVG(amount) as ticket_promedio
FROM silver_data
GROUP BY 1
ORDER BY ventas_totales DESC