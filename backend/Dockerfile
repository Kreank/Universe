# Universe game-server — Container-Image
FROM python:3.12-slim

# Keine .pyc, ungepufferte Logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Abhaengigkeiten zuerst (Layer-Caching).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Applikationscode.
COPY app ./app

# Das shared/-Volume wird zur Laufzeit nach /app/shared gemountet (siehe docker-compose),
# BALANCE_PATH zeigt dorthin.
ENV BALANCE_PATH=/app/shared/balance.json

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
