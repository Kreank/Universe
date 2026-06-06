# ai-worker — Build-Kontext ist der ai-worker/-Ordner selbst (siehe docker-compose).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Abhaengigkeiten zuerst (Layer-Cache).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode (main.py, ollama_client.py, db.py, jobs/, prompts/, ...).
COPY . .

# main.py liegt im Root des Build-Kontexts -> /app ist auf sys.path,
# die jobs/-Package- und Top-Level-Module sind direkt importierbar.
CMD ["python", "main.py"]
