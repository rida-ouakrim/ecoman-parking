FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY . .

# Exposer le port par défaut de Streamlit
EXPOSE 8501

# Commande de démarrage par défaut
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.baseUrlPath=parking"]
