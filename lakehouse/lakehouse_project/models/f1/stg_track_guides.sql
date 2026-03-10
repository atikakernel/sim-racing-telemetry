-- models/f1/stg_track_guides.sql

WITH source AS (
    -- Tomamos la versión más reciente de cada pista
    SELECT 
        track_name,
        full_content,
        url,
        ingestion_date,
        ROW_NUMBER() OVER (PARTITION BY track_name ORDER BY ingestion_date DESC) as rn
    FROM bronze_wikipedia_tracks
)

SELECT 
    track_name,
    url,
    -- Cortamos el texto porque pasarle 10.000 palabras a la IA es lento.
    -- Tomamos los primeros 3000 caracteres que suelen tener la intro y características.
    SUBSTR(full_content, 1, 3000) as resumen_tecnico
FROM source
WHERE rn = 1