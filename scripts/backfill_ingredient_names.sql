-- langchain_pg_embedding 테이블에 정규화된 재료 배열(ingredient_names) 컬럼을 백필하고
-- GIN 인덱스를 생성하는 1회성 SQL 스크립트.

-- 1) 컬럼 추가 (이미 있으면 스킵)
ALTER TABLE langchain_pg_embedding ADD COLUMN IF NOT EXISTS ingredient_names text[];

-- 2) 백필: document의 "parsed_ingredients: ..." 부분을 콤마로 분리 후
--    공백 제거 + 소문자화(정규화)하여 중복 제거한 배열로 저장.
UPDATE langchain_pg_embedding
SET ingredient_names = COALESCE(
    (
        SELECT array_agg(DISTINCT lower(replace(part_raw, ' ', '')))
        FROM unnest(
            string_to_array(
                (regexp_match(document, 'parsed_ingredients:\s*(.*)'))[1],
                ','
            )
        ) AS raw(part_original)
        CROSS JOIN LATERAL (SELECT trim(part_original) AS part_raw) t
        WHERE trim(part_raw) <> ''
    ),
    ARRAY[]::text[]
)
WHERE ingredient_names IS NULL;

-- 3) GIN 인덱스 생성 (동시성 모드: 서비스 중단 없이 생성됨)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_langchain_pg_embedding_ingredient_names
ON langchain_pg_embedding USING GIN (ingredient_names);
