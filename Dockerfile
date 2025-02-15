# Usa un'immagine Python leggera
FROM python:3.11-slim

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia i file richiesti nel container
COPY cookies.txt /app/cookies.txt
COPY ffmpeg /app/ffmpeg
COPY files /app/files
COPY ytdlapi.py /app/ytdlapi.py

# Imposta i permessi di esecuzione per ffmpeg e ffprobe
RUN chmod +x /app/ffmpeg/ffmpeg /app/ffmpeg/ffprobe

# Installa le dipendenze richieste (se ce ne sono)
RUN pip install --no-cache-dir -r requirements.txt || true

# Espone la porta 5000 (se necessario)
EXPOSE 5000

# Comando di avvio
CMD ["python", "ytdlapi.py"]
