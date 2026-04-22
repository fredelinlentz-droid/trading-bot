# Dockerfile — Trading Bot
FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p logs models

# Port exposé
EXPOSE 8000

# Variables d'environnement par défaut
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Lancement
CMD ["python", "main.py"]
