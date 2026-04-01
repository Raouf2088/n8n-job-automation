#!/usr/bin/env python3
"""Lightweight HTTP service that wraps generate_tailored_cv.py for n8n."""

import json
import io
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add pipeline dir to path so we can import the generator
sys.path.insert(0, os.path.dirname(__file__))
from generate_tailored_cv import (
    build_experiences, build_projects, build_skills,
    Path, re, subprocess, shutil, tempfile
)


class PDFHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"[pdf_service] ERROR: Invalid JSON: {e}", flush=True)
            print(f"[pdf_service] Body preview: {body[:500]}", flush=True)
            self.send_error(400, f"Invalid JSON: {e}")
            return

        try:
            pdf_bytes, filename = generate_pdf(data)
        except Exception as e:
            import traceback
            print(f"[pdf_service] ERROR: {e}", flush=True)
            traceback.print_exc()
            self.send_error(500, f"PDF generation failed: {e}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("X-Filename", filename)
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def log_message(self, format, *args):
        print(f"[pdf_service] {args[0]}", flush=True)


def generate_pdf(data):
    template_path = Path(
        os.environ.get("CV_TEMPLATE_PATH", Path(__file__).parent / "cv_template.tex")
    )
    template = template_path.read_text(encoding="utf-8")

    company = data.get("company", "Company")
    role = data.get("role", "Role")
    keywords = data.get("ats_keywords", [])
    experiences = data.get("experiences", [])
    projects = data.get("projects", [])
    skills = data.get("skills", [])

    exp_latex = build_experiences(experiences, keywords)
    proj_latex = build_projects(projects, keywords)
    skills_latex = build_skills(skills, keywords)

    filled = template.replace("{{EXPERIENCES}}", exp_latex)
    filled = filled.replace("{{PROJECTS}}", proj_latex)
    filled = filled.replace("{{SKILLS}}", skills_latex)

    safe_company = re.sub(r"[^\w\-]", "_", company)
    safe_role = re.sub(r"[^\w\-]", "_", role)
    filename = f"Riad_Boussoura_CV_{safe_company}_{safe_role}.pdf"

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "resume.tex"
        tex_file.write_text(filled, encoding="utf-8")

        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pdflatex failed:\n{result.stdout[-500:]}\n{result.stderr[-500:]}")

        compiled_pdf = Path(tmpdir) / "resume.pdf"
        if not compiled_pdf.exists():
            raise RuntimeError("PDF was not generated")

        pdf_bytes = compiled_pdf.read_bytes()

    return pdf_bytes, filename


if __name__ == "__main__":
    port = int(os.environ.get("PDF_SERVICE_PORT", 3456))
    server = HTTPServer(("0.0.0.0", port), PDFHandler)
    print(f"[pdf_service] Listening on port {port}", flush=True)
    server.serve_forever()
