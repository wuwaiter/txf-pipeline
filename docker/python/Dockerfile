FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y gcc build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.toml .
COPY src/ ./src/
COPY frontend/ ./frontend/

ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["python", "-m", "app.main"]
