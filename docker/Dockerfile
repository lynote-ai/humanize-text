# Stage 1: Build Svelte frontend with Bun
FROM oven/bun:latest AS frontend

WORKDIR /app/frontend

COPY frontend/package.json ./
RUN bun install

COPY frontend/ ./
RUN bun run build

# Stage 2: Python application
FROM python:3.11-slim AS app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy the compiled frontend into /app/static so FastAPI can serve it
COPY --from=frontend /app/frontend/dist /app/static

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
