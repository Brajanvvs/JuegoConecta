# Imagen del juego. Solo Python y Flask.
# Los eventos se escriben en /var/log/conecta4 y Promtail los lee desde ahí.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV LOG_PATH=/var/log/conecta4/juego.log

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
