# Stage 1: Install texlive and Python in a full Debian image
FROM debian:bookworm-slim AS texlive

RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-latex-recommended \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Copy into n8n image
FROM n8nio/n8n:latest

USER root

# Copy texlive and python from the build stage
COPY --from=texlive /usr/bin/pdflatex /usr/bin/pdflatex
COPY --from=texlive /usr/bin/kpsewhich /usr/bin/kpsewhich
COPY --from=texlive /usr/bin/mktexfmt /usr/bin/mktexfmt
COPY --from=texlive /usr/share/texlive /usr/share/texlive
COPY --from=texlive /usr/share/texmf /usr/share/texmf
COPY --from=texlive /var/lib/texmf /var/lib/texmf
COPY --from=texlive /usr/bin/python3 /usr/bin/python3
COPY --from=texlive /usr/lib/python3* /usr/lib/python3/
COPY --from=texlive /usr/lib/x86_64-linux-gnu/libpython3* /usr/lib/x86_64-linux-gnu/
COPY --from=texlive /usr/lib/x86_64-linux-gnu/libexpat* /usr/lib/x86_64-linux-gnu/
COPY --from=texlive /etc/texmf /etc/texmf

# Copy pipeline scripts
COPY pipeline/ /home/node/pipeline/

# Set environment variables for the CV generator
ENV CV_TEMPLATE_PATH=/home/node/pipeline/cv_template.tex
ENV CV_OUTPUT_DIR=/home/node/pipeline/output

# Create output directory
RUN mkdir -p /home/node/pipeline/output && \
    chown -R node:node /home/node/pipeline

USER node
