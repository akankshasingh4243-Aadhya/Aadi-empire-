FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY ["1. sniper-hub/sniper.py", "/app/sniper.py"]

RUN uv pip install --no-cache fastapi uvicorn[standard] httpx pydantic

EXPOSE 8080
CMD ["uvicorn", "sniper:app", "--host", "0.0.0.0", "--port", "8080"]
