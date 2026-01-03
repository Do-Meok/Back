# 1. 파이썬 베이스 이미지
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정
# ✅ 변경: 개발 버전과 동일하게 /venv 사용 (시스템 파이썬과 격리)
# ✅ 추가: UV_COMPILE_BYTECODE=1 (설치 시 .pyc 파일을 미리 컴파일하여 실행 속도 향상)
ENV UV_PROJECT_ENVIRONMENT="/venv"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul \
    UV_COMPILE_BYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

# 4. 필수 시스템 패키지 및 타임존 설정
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata curl && \
    rm -rf /var/lib/apt/lists/*

# 5. uv 설치
RUN pip install --no-cache-dir uv

# 6. 의존성 설치
COPY pyproject.toml uv.lock ./

# ✅ 변경: uv sync 사용
# --frozen: uv.lock 파일 기준으로만 설치 (버전 변경 방지)
# --no-dev: 배포판이므로 개발용 패키지 제외 (테스트 도구 등)
# --no-install-project: 프로젝트 자체는 설치하지 않고 의존성만 설치
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 7. 프로젝트 전체 복사
COPY . .

# 8. FastAPI 실행
# --reload 제거 (배포 환경)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "on", "--proxy-headers", "--forwarded-allow-ips", "*"]