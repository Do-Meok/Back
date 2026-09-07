"""
langchain_pg_embedding 테이블에 정규화된 재료 배열(ingredient_names) 컬럼을 백필하고
GIN 인덱스를 생성하는 1회성 스크립트.

document(page_content)의 "parsed_ingredients: ..." 줄을 파싱해 정규화된 재료명 배열로 저장한다.
이 배열/인덱스는 domains.rag.retriever.RecipeRetriever.search_exact_matches 의
SQL containment(<@) 검색이 사용한다.

실행:
    uv run python scripts/backfill_ingredient_names.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import psycopg

from core.config import settings
from domains.rag.mapper import normalize_ingredient_name, parse_page_content, split_ingredients

BATCH_SIZE = 2000


def _to_psycopg_dsn(rag_url: str) -> str:
    return rag_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    dsn = _to_psycopg_dsn(settings.rag_url)

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE langchain_pg_embedding ADD COLUMN IF NOT EXISTS ingredient_names text[]")

        total_updated = 0
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, document FROM langchain_pg_embedding WHERE ingredient_names IS NULL LIMIT %s",
                    (BATCH_SIZE,),
                )
                rows = cur.fetchall()

            if not rows:
                break

            updates = []
            for row_id, document in rows:
                parsed = parse_page_content(document or "")
                names = split_ingredients(parsed)
                normalized = sorted({normalize_ingredient_name(name) for name in names if name.strip()})
                updates.append((normalized, row_id))

            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE langchain_pg_embedding SET ingredient_names = %s WHERE id = %s",
                    updates,
                )

            total_updated += len(updates)
            print(f"backfilled {total_updated} rows...")

        print("creating GIN index (CONCURRENTLY)...")
        with conn.cursor() as cur:
            cur.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_langchain_pg_embedding_ingredient_names "
                "ON langchain_pg_embedding USING GIN (ingredient_names)"
            )

    print(f"done. total rows backfilled: {total_updated}")


if __name__ == "__main__":
    main()
