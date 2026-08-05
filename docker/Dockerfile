FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi pydantic uvicorn

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.methodologies.humanizer:create_api_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
