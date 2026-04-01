#!/usr/bin/env python3
"""
generate_tailored_cv.py — Reads tailored resume JSON from stdin, fills the
LaTeX template, auto-bolds ATS keywords, compiles to PDF via pdflatex.

Expected JSON schema on stdin:
{
  "company": "Acme Corp",
  "role": "Computer Vision Engineer",
  "ats_keywords": ["PyTorch", "OpenCV", "deep learning"],
  "experiences": [
    {
      "title": "Computer Vision R&D Engineer",
      "dates": "Mar. 2025 -- Sep. 2025",
      "company": "GoPro",
      "location": "Paris, France",
      "bullets": [
        "Architected a Sim-to-Real deep learning pipeline ...",
        "Developed a procedural generation engine ..."
      ]
    }
  ],
  "projects": [
    {
      "name": "ASYEL: Sign Language Translation",
      "tech": "Deep Learning, LSTM, Time-Series",
      "dates": "Apr. 2022",
      "bullets": [
        "Architected a gesture-to-speech translation pipeline ..."
      ]
    }
  ],
  "skills": [
    {"category": "Computer Vision & 3D", "items": "OpenCV, MediaPipe, YOLO ..."},
    {"category": "Deep Learning", "items": "PyTorch, CNNs, Vision Transformers ..."}
  ]
}

Environment variables:
  CV_TEMPLATE_PATH  — path to cv_template.tex (default: ./cv_template.tex)
  CV_OUTPUT_DIR     — directory for output PDFs (default: ./output)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


# ---------------------------------------------------------------------------
# Unicode → LaTeX conversion (must run BEFORE escaping)
# ---------------------------------------------------------------------------

UNICODE_TO_LATEX = {
    "\u00b0": r"\textdegree{}",   # °
    "\u2013": "--",                # en-dash –
    "\u2014": "---",               # em-dash —
    "\u2018": "`",                 # left single quote '
    "\u2019": "'",                 # right single quote '
    "\u201c": "``",                # left double quote "
    "\u201d": "''",                # right double quote "
    "\u2026": r"\ldots{}",         # ellipsis …
    "\u00a0": "~",                 # non-breaking space
    "\u2264": r"$\leq$",          # ≤
    "\u2265": r"$\geq$",          # ≥
    "\u00d7": r"$\times$",        # ×
    "\u2192": r"$\rightarrow$",   # →
    "\u00e9": r"\'e",              # é
    "\u00e8": r"\`e",              # è
    "\u00ea": r"\^e",              # ê
    "\u00e0": r"\`a",              # à
    "\u00e7": r"\c{c}",           # ç
    "\u00f4": r"\^o",              # ô
    "\u00fc": r'\"u',              # ü
    "\u00e4": r'\"a',              # ä
    "\u00f6": r'\"o',              # ö
}


def normalize_unicode(text: str) -> str:
    """Convert common unicode characters to their LaTeX equivalents."""
    for char, latex in UNICODE_TO_LATEX.items():
        text = text.replace(char, latex)
    return text


# ---------------------------------------------------------------------------
# LaTeX escaping
# ---------------------------------------------------------------------------

LATEX_SPECIAL = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# LaTeX commands we preserve if the LLM accidentally outputs them
PRESERVED_COMMANDS = (r"\textbf{", r"\textit{", r"\emph{", r"\href{", r"\underline{")


def escape_latex(text: str) -> str:
    """Escape LaTeX special chars, preserving known commands and handling braces."""
    text = normalize_unicode(text)

    result = []
    i = 0
    while i < len(text):
        # Check for known LaTeX commands to preserve
        preserved = False
        for cmd in PRESERVED_COMMANDS:
            if text[i:i + len(cmd)] == cmd:
                result.append(cmd)
                i += len(cmd)
                # Walk to the matching closing brace, escaping content inside
                depth = 1
                while i < len(text) and depth > 0:
                    ch = text[i]
                    if ch == "{":
                        depth += 1
                        result.append(ch)
                    elif ch == "}":
                        depth -= 1
                        result.append(ch)  # closing brace preserved as-is
                    elif ch in LATEX_SPECIAL:
                        result.append(LATEX_SPECIAL[ch])
                    else:
                        result.append(ch)
                    i += 1
                preserved = True
                break

        if preserved:
            continue

        ch = text[i]
        if ch in LATEX_SPECIAL:
            result.append(LATEX_SPECIAL[ch])
        elif ch == "{":
            result.append(r"\{")
        elif ch == "}":
            result.append(r"\}")
        else:
            result.append(ch)
        i += 1

    return "".join(result)


# ---------------------------------------------------------------------------
# ATS keyword bolding
# ---------------------------------------------------------------------------

def bold_keywords(text: str, keywords: list[str]) -> str:
    """Wrap ATS keywords in \\textbf{}, longest-first, no overlaps or nesting."""
    if not keywords:
        return text

    # Deduplicate and sort longest first so "deep learning" beats "learning"
    sorted_kw = sorted(set(keywords), key=len, reverse=True)

    # Pre-mark existing \textbf{...} spans as already claimed
    claimed = set()
    for m in re.finditer(r"\\textbf\{[^}]*\}", text):
        claimed |= set(range(m.start(), m.end()))

    # Find non-overlapping keyword matches with word boundaries
    insertions = []  # (start, end, matched_text)
    for kw in sorted_kw:
        if len(kw) < 2:
            continue
        # Escape the keyword for regex, add word-boundary guards
        escaped_kw = re.escape(kw)
        pattern = re.compile(
            r"(?<![a-zA-Z0-9])" + escaped_kw + r"(?![a-zA-Z0-9])",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            span = set(range(m.start(), m.end()))
            if span & claimed:
                continue  # overlaps with existing bold or earlier keyword
            claimed |= span
            insertions.append((m.start(), m.end(), m.group(0)))

    # Apply from right to left so positions stay valid
    insertions.sort(key=lambda x: x[0], reverse=True)
    for start, end, matched in insertions:
        text = text[:start] + r"\textbf{" + matched + "}" + text[end:]

    return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_date_dashes(dates: str) -> str:
    """Ensure date ranges use LaTeX en-dash (--) consistently."""
    # Convert any dash variant (-, –, —) surrounded by spaces to LaTeX en-dash
    return re.sub(r"\s*[-\u2013\u2014]+\s*", " -- ", dates)


# ---------------------------------------------------------------------------
# LaTeX section builders
# ---------------------------------------------------------------------------

def build_experiences(experiences: list[dict], keywords: list[str]) -> str:
    """Build the LaTeX for the Experience section."""
    lines = []
    for exp in experiences:
        title = escape_latex(exp["title"])
        dates = normalize_date_dashes(escape_latex(exp["dates"]))
        company = escape_latex(exp["company"])
        location = escape_latex(exp["location"])

        lines.append(f"    \\resumeSubheading")
        lines.append(f"      {{{title}}}{{{dates}}}")
        lines.append(f"      {{{company}}}{{{location}}}")
        lines.append(f"      \\resumeItemListStart")
        for bullet in exp["bullets"]:
            bullet_escaped = escape_latex(bullet)
            bullet_bolded = bold_keywords(bullet_escaped, keywords)
            lines.append(f"        \\resumeItem{{{bullet_bolded}}}")
        lines.append(f"      \\resumeItemListEnd")
        lines.append("")
    return "\n".join(lines)


def build_projects(projects: list[dict], keywords: list[str]) -> str:
    """Build the LaTeX for the Projects section."""
    lines = []
    for proj in projects:
        name = escape_latex(proj["name"])
        tech = escape_latex(proj["tech"])
        dates = normalize_date_dashes(escape_latex(proj["dates"]))

        lines.append(f"      \\resumeProjectHeading")
        lines.append(
            f"          {{\\textbf{{{name}}} $|$ \\emph{{{tech}}}}}{{{dates}}}"
        )
        lines.append(f"          \\resumeItemListStart")
        for bullet in proj["bullets"]:
            bullet_escaped = escape_latex(bullet)
            bullet_bolded = bold_keywords(bullet_escaped, keywords)
            lines.append(f"            \\resumeItem{{{bullet_bolded}}}")
        lines.append(f"          \\resumeItemListEnd")
    return "\n".join(lines)


def build_skills(skills: list[dict], keywords: list[str]) -> str:
    """Build the LaTeX for the Technical Skills section."""
    lines = []
    for skill in skills:
        category = escape_latex(skill["category"])
        raw_items = skill["items"]
        if isinstance(raw_items, list):
            raw_items = ", ".join(str(i) for i in raw_items)
        items = escape_latex(raw_items)
        items_bolded = bold_keywords(items, keywords)
        lines.append(f"     \\textbf{{{category}}}{{: {items_bolded}}} \\\\")
    # Remove trailing \\\\ from last line
    if lines:
        lines[-1] = lines[-1].rstrip(" \\\\")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Read JSON from stdin
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Paths
    template_path = Path(
        os.environ.get("CV_TEMPLATE_PATH", Path(__file__).parent / "cv_template.tex")
    )
    output_dir = Path(
        os.environ.get("CV_OUTPUT_DIR", Path(__file__).parent / "output")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read template
    if not template_path.exists():
        print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    template = template_path.read_text(encoding="utf-8")

    # Extract fields
    company = data.get("company", "Company")
    role = data.get("role", "Role")
    keywords = data.get("ats_keywords", [])
    experiences = data.get("experiences", [])
    projects = data.get("projects", [])
    skills = data.get("skills", [])

    # Build sections
    exp_latex = build_experiences(experiences, keywords)
    proj_latex = build_projects(projects, keywords)
    skills_latex = build_skills(skills, keywords)

    # Fill template
    filled = template.replace("{{EXPERIENCES}}", exp_latex)
    filled = filled.replace("{{PROJECTS}}", proj_latex)
    filled = filled.replace("{{SKILLS}}", skills_latex)

    # Sanitize filename
    safe_company = re.sub(r"[^\w\-]", "_", company)
    safe_role = re.sub(r"[^\w\-]", "_", role)
    pdf_name = f"Riad_Boussoura_CV_{safe_company}_{safe_role}.pdf"
    pdf_path = output_dir / pdf_name

    # Compile in a temp directory to keep things clean
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "resume.tex"
        tex_file.write_text(filled, encoding="utf-8")

        # Run pdflatex twice for cross-references
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                print(f"ERROR: pdflatex failed:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
                sys.exit(1)

        # Copy PDF to output directory
        compiled_pdf = Path(tmpdir) / "resume.pdf"
        if not compiled_pdf.exists():
            print("ERROR: PDF was not generated", file=sys.stderr)
            sys.exit(1)
        shutil.copy2(compiled_pdf, pdf_path)

    # Print the output path (n8n reads this from stdout)
    print(str(pdf_path))


if __name__ == "__main__":
    main()
