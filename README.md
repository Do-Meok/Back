# DoMeok (두고먹고)

보유 재료를 등록하면 RAG 기반으로 레시피를 추천해주고, 만개의 레시피 크롤링을 통해 레시피를 검색해주는 백엔드 API. 영수증 OCR로 재료를 자동 인식하고, 카카오 소셜 로그인/이메일 인증 회원가입을 지원

## Tech Stack

**Language / Runtime**
- Python 3.14 ([uv](https://github.com/astral-sh/uv) 패키지 매니저)

**Framework**
- FastAPI (+ Uvicorn)

**Database**
- PostgreSQL 15 (pgvector 확장 포함) — SQLAlchemy 2.0 (async) + Alembic 마이그레이션
- Redis — 인증 코드/리프레시 토큰/가입 임시 저장/사용량(quota) 등 단기 상태 저장

**AI / External APIs**
- OpenAI (LLM, 임베딩) + LangChain / langchain-postgres(PGVector) — 레시피 RAG 검색
- Naver CLOVA OCR — 영수증 이미지 인식
- Kakao OAuth — 소셜 로그인
- SMTP — 이메일 인증 코드 발송
- BeautifulSoup4 — 만개의 레시피 상세 페이지 크롤링

**Infra**
- Docker / Docker Compose
- Jenkins (CI/CD)
- Nginx (Reverse Proxy)

## Project Structure

```
src/
├── main.py                 # FastAPI 앱 엔트리포인트, 미들웨어/예외 핸들러 등록
├── api/
│   ├── api.py               # 버전별 라우터 취합
│   ├── deps.py               # 공용 의존성(DI) - 서비스 팩토리, 인증 유저 추출
│   └── v1/endpoints/         # 엔드포인트 (auth, user, ingredient, ocr, rag)
├── core/
│   ├── config.py              # 환경변수 기반 설정 (pydantic-settings)
│   ├── database.py            # SQLAlchemy 엔진/세션
│   ├── redis.py               # Redis 커넥션 라이프사이클
│   ├── security.py            # 비밀번호 해시, JWT 발급/검증
│   ├── quota.py               # 일일 사용량 제한 (RAG/SMTP 등)
│   ├── timezone.py            # KST 타임존 유틸
│   ├── logger.py              # loguru 설정
│   └── exception/              # 커스텀 예외, 전역 핸들러, OpenAPI 에러 응답 스키마
└── domains/
    ├── auth/                    # 로그인/회원가입/카카오 OAuth/이메일 인증/토큰 저장소
    ├── user/                    # 유저 모델·정보 조회/수정
    ├── ingredient/               # 보유 재료 CRUD
    ├── ocr/                      # 영수증 이미지 → LLM 파싱 → 재료 목록
    ├── rag/                      # 보유 재료 기반 레시피 추천 (PGVector 검색)
    ├── recipe_detail/             # 레시피 상세 크롤링·캐싱·매칭
    └── saved_recipe/               # 추천/상세에서 본 레시피 저장 목록

alembic/          # DB 마이그레이션
tests/
├── api/           # 엔드포인트 통합 테스트
└── unit/          # 서비스/유틸 단위 테스트
```

## API Overview

| Tag | Prefix | 설명 |
|---|---|---|
| Auth | `/api/v1/auth` | 로그인/로그아웃/토큰 갱신, 카카오 로그인(앱/웹), 이메일 인증 회원가입, 비밀번호 재설정 |
| Users | `/api/v1/users` | 내 정보 조회/수정, 비밀번호 변경 |
| Ingredients | `/api/v1/ingredients` | 보유 재료 추가/조회/삭제/일괄 삭제 |
| OCR | `/api/v1/ocr` | 영수증 이미지 업로드 → 구매 품목 인식 |
| Recipes | `/api/v1/recipes` | 보유 재료 기반 레시피 추천, 레시피 상세 크롤링 조회 |
| Saved_recipe | `/api/v1/recipes/saved` | 레시피 저장/목록/상세/저장 여부 확인/삭제 |

서버 실행 후 `/docs` (Swagger UI) 또는 `/redoc`에서 전체 스펙을 확인할 수 있다.

## Getting Started

### 요구 사항
- Python 3.14
- [uv](https://github.com/astral-sh/uv)
- Docker (PostgreSQL, Redis 로컬 실행용)

### 환경변수

프로젝트 루트에 `.env` 파일을 생성 후 다음과 같은 값을 채우면 됨.

```
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432
DB_NAME=domeok

REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=
PHONE_AES_KEY=
HMAC_SECRET=

OPENAI_API_KEY=
NAVER_OCR_SECRET_KEY=
NAVER_OCR_API_URL=

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=DoMeok(두고먹고)

KAKAO_REST_API_KEY=
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=
```

### 로컬 실행 (Docker Compose)

```bash
docker compose -f docker-compose.dev.yml up --build
```

### 로컬 실행 (uv 직접 실행)

```bash
uv sync

# PostgreSQL(pgvector), Redis는 별도로 기동되어 있어야 함
uv run alembic upgrade head
uv run fastapi dev src/main.py --host 0.0.0.0 --port 8000
```

서버가 뜨면 `http://localhost:8000/docs` 에서 API 문서를 확인할 수 있다.

### 테스트

```bash
uv run pytest
```

### Lint

```bash
uv run ruff check .
```

## Deployment

`docker-compose.yml`을 사용해 배포하며, Jenkins 파이프라인(`Jenkinsfile`)이 이미지 빌드·배포를 담당함.
