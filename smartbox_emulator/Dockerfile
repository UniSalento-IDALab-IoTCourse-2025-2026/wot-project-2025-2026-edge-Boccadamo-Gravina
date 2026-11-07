FROM python:3.11-slim

# Evita la creazione di file .pyc e forza il flush dell'output standard
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Installazione dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia del codice sorgente
COPY main.py .

# Utente non privilegiato
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-u", "main.py"]
