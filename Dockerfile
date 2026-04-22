# 1. 파이썬 베이스 이미지 설치
FROM python:3.14-slim

# 2. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치 (캐싱 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 5. 소스 코드 복사
COPY . .

# 6. 실행 명령(uv를 통해 실행)
CMD ["uv", "run", "fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]