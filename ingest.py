"""
ingest.py - Ingest and extract structured knowledge from Burj_Khalifa_Encyclopedia.pdf.

Extracts text into:
- data/knowledge_base.md (formatted Markdown organized by sections 1-12)
- data/chunks.json (JSON array with one entry per section: section_number, title, content)

Re-running this script refreshes the knowledge base.
"""

import json
import re
from pathlib import Path
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "Burj_Khalifa_Encyclopedia.pdf"
DATA_DIR = BASE_DIR / "data"
KB_MD_PATH = DATA_DIR / "knowledge_base.md"
CHUNKS_JSON_PATH = DATA_DIR / "chunks.json"


def clean_page_text(text: str) -> str:
    """Remove running page headers/footers and normalize unicode typographic quotes/dashes."""
    if not text:
        return ""

    # Normalize typographic quotes and dashes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2013", "-").replace("\u2014", "--")

    # Filter out page header/footer lines
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Header: "Burj Khalifa: An Encyclopedia of Its Construction"
        if re.match(r"^Burj Khalifa:\s*An Encyclopedia of Its Construction$", stripped, re.IGNORECASE):
            continue
        # Header: "Page X"
        if re.match(r"^Page\s+\d+$", stripped, re.IGNORECASE):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_sections(pdf_path: Path) -> list[dict]:
    """Extract sections 1 through 12 from pages 3 to end of the PDF."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    # Page 1 is Cover, Page 2 is Table of Contents; content starts on Page 3 (index 2)
    body_pages = reader.pages[2:]
    cleaned_pages = [clean_page_text(p.extract_text() or "") for p in body_pages]
    combined_body = "\n".join(cleaned_pages)

    # Regex matches section numbers like "1. At a Glance", "12. Notes on Sources..."
    pattern = r"(?m)^(\d{1,2})\.\s+([^\n\r]+)"
    matches = list(re.finditer(pattern, combined_body))

    chunks = []
    for i, match in enumerate(matches):
        sec_num = int(match.group(1))
        title = match.group(2).strip()

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(combined_body)

        content = combined_body[start_pos:end_pos].strip()
        # Clean up excess consecutive blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)

        chunks.append({
            "section_number": sec_num,
            "title": title,
            "content": content
        })

    return chunks


def build_markdown_kb(chunks: list[dict]) -> str:
    """Format chunks into a comprehensive, readable Markdown document."""
    header = (
        "# Burj Khalifa: An Encyclopedia of Its Construction\n\n"
        "> Official Knowledge Base extracted from `Burj_Khalifa_Encyclopedia.pdf`.\n"
        "> Dubai, United Arab Emirates | Height: 828 metres (2,717 feet) | Construction: January 2004 - January 2010\n\n"
        "---\n\n"
    )

    section_texts = []
    for c in chunks:
        sec_num = c["section_number"]
        title = c["title"]
        content = c["content"]
        section_texts.append(f"## Section {sec_num}: {title}\n\n{content}\n")

    return header + "\n---\n\n".join(section_texts)


def run_ingestion():
    print(f"[Ingest] Processing PDF: {PDF_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    chunks = extract_sections(PDF_PATH)
    if not chunks:
        raise RuntimeError("No sections were extracted from the PDF. Check PDF structure.")

    print(f"[Ingest] Extracted {len(chunks)} sections.")
    for c in chunks:
        print(f"  - Section {c['section_number']}: {c['title']} ({len(c['content'])} chars)")

    # Build knowledge base Markdown
    kb_md = build_markdown_kb(chunks)
    with open(KB_MD_PATH, "w", encoding="utf-8") as f:
        f.write(kb_md)
    print(f"[Ingest] Saved {KB_MD_PATH} ({len(kb_md)} chars)")

    # Save chunks JSON
    with open(CHUNKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"[Ingest] Saved {CHUNKS_JSON_PATH}")


if __name__ == "__main__":
    run_ingestion()
