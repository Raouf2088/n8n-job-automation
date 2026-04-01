FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-latex-recommended \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/

ENV CV_TEMPLATE_PATH=/app/cv_template.tex
ENV PDF_SERVICE_PORT=3456

EXPOSE 3456

CMD ["python3", "/app/pdf_service.py"]
