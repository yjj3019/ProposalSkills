# Optional portable runtime for the gates: python-pptx + Pillow (requirements.txt), LibreOffice for the render check,
# Poppler for page images, Noto CJK so Korean renders. Nothing here is required to use the skills.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    libreoffice-impress \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/proposal-skills
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "runtime_check.py"]
