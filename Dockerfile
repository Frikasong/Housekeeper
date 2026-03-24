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

COPY ["Tool_Creation/01.local app version/requirements.txt", "."]
RUN pip install --no-cache-dir -r requirements.txt

COPY ["Tool_Creation/01.local app version/app.py", \
      "Tool_Creation/01.local app version/evidence_stats.json", \
      "Tool_Creation/01.local app version/gunicorn.conf.py", "./"]
COPY ["Tool_Creation/01.local app version/templates/", "templates/"]
COPY ["Tool_Creation/01.local app version/content/", "content/"]

RUN mkdir -p uploads

EXPOSE 10000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
