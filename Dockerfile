FROM python:3.11-slim

# Install LibreOffice (headless) for DOCX/XLSX/PPTX rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py evidence_stats.json gunicorn.conf.py ./
COPY templates/ templates/

RUN mkdir -p uploads

EXPOSE 10000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
