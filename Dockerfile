# python 3.10 이미지 설치 - slim(가벼운 버전)
FROM python:3.10-slim

# 2️⃣ 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 및 타임존 설정
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# ✅ 변경된 부분: requirements.txt 대신 pyproject.toml 사용
# 1. 설정 파일 복사 (requirements.txt 제거됨)
COPY pyproject.toml .
COPY uv.lock .

# (✅ 변경 - 캐시 마운트 적용)
# --mount=type=cache: 호스트의 캐시 폴더를 빌드 중에 끌어다 씁니다.
# 다운로드했던 패키지가 남아있어서, 2번째 빌드부터는 설치가 '즉시' 완료됩니다.
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml \
    --cache-dir /root/.cache/uv

# 프로젝트 전체 복사
COPY . .

# PYTHONPATH 설정
ENV PYTHONPATH=/app/src

# FastAPI 실행
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "on", "--proxy-headers", "--forwarded-allow-ips", "*"]