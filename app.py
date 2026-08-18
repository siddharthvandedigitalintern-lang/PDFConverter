import io
import hashlib
import json
import os
import re
import shutil
import time
import uuid
import webbrowser
from collections import Counter, defaultdict
from pathlib import Path
from threading import Thread, Timer

import fitz
try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from google import genai

try:
    from weasyprint import HTML
except (ImportError, OSError):
    HTML = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

import logging
from logging.handlers import RotatingFileHandler
log_file = UPLOAD_DIR / "app.log"
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=2)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "title_segment_id": {"type": "integer"},
        "unit_headings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "integer"},
                    "unit_number": {"type": "integer"},
                },
                "required": ["segment_id", "unit_number"],
            },
        },
        "heading_segment_ids": {"type": "array", "items": {"type": "integer"}},
        "mcq_segment_ids": {"type": "array", "items": {"type": "integer"}},
        "qa_segment_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["title_segment_id", "unit_headings", "heading_segment_ids", "mcq_segment_ids", "qa_segment_ids"],
}

PROMPT = """Classify the numbered text segments below into the supplied JSON schema.

Rules:
- Return segment IDs only. Never return or rewrite document text.
- List unit/chapter title IDs with their unit numbers in unit_headings.
- List subheading IDs, multiple-choice block IDs, and question-answer block IDs in their matching arrays.
- Normal paragraphs need no label and must not be listed.
- Keep IDs in ascending source order. If a category is absent, return an empty array.
- Choose the source segment that contains the main document title as title_segment_id.

NUMBERED SEGMENTS:
{segments}
"""


def _looks_like_list(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    markers = sum(
        bool(re.match(r"^(?:[\u2022\u25cf\u25aa\u25b6\uf0d8]|\d{1,2}[.)])\s+", line))
        for line in lines
    )
    return markers >= 2


def extract_segments(pdf_path: Path, image_dir: Path | None = None) -> list[dict]:
    segments = []
    image_hashes = Counter()
    page_count = 0
    if image_dir:
        image_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        page_count = len(document)
        for page_number, page in enumerate(document, start=1):
            tables = []
            try:
                for table in page.find_tables().tables:
                    rows = [
                        [re.sub(r"\s+", " ", cell or "").strip() for cell in row]
                        for row in table.extract()
                    ]
                    rows = [row for row in rows if any(row)]
                    if rows and max(map(len, rows), default=0) >= 2:
                        tables.append({"type": "table", "bbox": tuple(table.bbox), "rows": rows})
            except Exception:
                app.logger.debug("Table extraction unavailable on page %s", page_number, exc_info=True)

            blocks = page.get_text("dict").get("blocks", [])
            entries = [*blocks, *tables]
            entries.sort(key=lambda block: (round(block["bbox"][1]), block["bbox"][0]))
            for block in entries:
                if block.get("type") == "table":
                    previous_table = next(
                        (item for item in reversed(segments) if item.get("type") == "table"),
                        None,
                    )
                    if (
                        previous_table
                        and previous_table["page"] == page_number - 1
                        and not previous_table["rows"]
                        and len(previous_table["headers"]) == len(block["rows"][0])
                    ):
                        previous_table["rows"].extend(block["rows"])
                        continue
                    segments.append({
                        "id": len(segments) + 1,
                        "page": page_number,
                        "type": "table",
                        "headers": block["rows"][0],
                        "rows": block["rows"][1:],
                    })
                    continue

                block_rect = fitz.Rect(block["bbox"])
                if block.get("type") == 0 and any(
                    fitz.Rect(table["bbox"]).contains(block_rect.tl)
                    and fitz.Rect(table["bbox"]).contains(block_rect.br)
                    for table in tables
                ):
                    continue

                if block.get("type") == 1 and image_dir:
                    x0, y0, x1, y1 = block["bbox"]
                    image = block.get("image", b"")
                    if x1 - x0 >= 60 and y1 - y0 >= 35 and len(image) >= 1000:
                        extension = block.get("ext", "png")
                        image_path = image_dir / f"page-{page_number}-image-{len(segments) + 1}.{extension}"
                        image_path.write_bytes(image)
                        image_hash = hashlib.sha256(image).hexdigest()
                        image_hashes[image_hash] += 1
                        segments.append({
                            "id": len(segments) + 1,
                            "page": page_number,
                            "type": "image",
                            "src": image_path.resolve().as_uri(),
                            "image_hash": image_hash,
                        })
                    continue

                if block.get("type") != 0:
                    continue

                lines = []
                spans = []
                for line in block.get("lines", []):
                    line_spans = line.get("spans", [])
                    line_text = "".join(span.get("text", "") for span in line_spans).rstrip()
                    if line_text.strip():
                        lines.append(line_text)
                        spans.extend(line_spans)

                text = "\n".join(lines).strip()
                if not text or text == str(page_number):
                    continue

                visible_spans = [span for span in spans if span.get("text", "").strip()]
                font_size = max((float(span.get("size", 0)) for span in visible_spans), default=0)
                total_chars = sum(len(span.get("text", "").strip()) for span in visible_spans)
                bold_chars = sum(
                    len(span.get("text", "").strip())
                    for span in visible_spans
                    if "bold" in span.get("font", "").lower() or span.get("flags", 0) & 16
                )
                segments.append({
                    "id": len(segments) + 1,
                    "page": page_number,
                    "type": "text",
                    "text": text,
                    "font_size": round(font_size, 2),
                    "is_bold": total_chars > 0 and bold_chars / total_chars >= 0.5,
                    "preserve_lines": _looks_like_list(text),
                })
    if image_dir:
        recurring = {
            image_hash for image_hash, count in image_hashes.items()
            if count >= max(2, page_count * 0.6)
        }
        kept = []
        for segment in segments:
            if segment.get("image_hash") in recurring:
                Path(segment["src"].removeprefix("file:///")).unlink(missing_ok=True)
                continue
            segment.pop("image_hash", None)
            kept.append(segment)
        segments = kept
    for new_id, segment in enumerate(segments, start=1):
        segment["id"] = new_id
    return segments


def _clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _clean_latex_symbols(text: str) -> str:
    symbols = {
        "\\alpha": "α",
        "\\beta": "β",
        "\\gamma": "γ",
        "\\rho": "ρ",
        "\\mu": "μ",
        "\\sigma": "σ",
        "\\theta": "θ",
        "\\delta": "δ",
        "\\epsilon": "ε",
        "\\pi": "π",
        "\\chi": "χ",
        "\\eta": "η",
        "\\lambda": "λ",
        "\\omega": "ω",
        "\\phi": "φ",
        "\\psi": "ψ",
        "\\tau": "τ",
        "\\xi": "ξ",
        "\\zeta": "ζ"
    }
    for k, v in symbols.items():
        text = text.replace(k, v)
        text = text.replace(k.upper(), v.upper() if hasattr(v, 'upper') else v)
        
    # Replace plain word forms to unicode Greek symbols
    text = re.sub(r"\balpha\b", "α", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbeta\b", "β", text, flags=re.IGNORECASE)
    
    # Translate common subscript representations
    text = re.sub(r"\bH0\b|\bH_0\b", "H₀", text)
    text = re.sub(r"\bHa\b|\bH_a\b", "Hₐ", text)
    text = re.sub(r"\bH1\b|\bH_1\b", "H₁", text)
    return text


def _markdown_to_html(text: str) -> str:
    parts = text.split("**")
    result = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            result.append(f"<strong>{part}</strong>")
        else:
            result.append(part)
    text = "".join(result)
    
    parts = text.split("__")
    result = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            result.append(f"<strong>{part}</strong>")
        else:
            result.append(part)
    return "".join(result)


def _plain_markdown(value: str) -> str:
    value = re.sub(r"!\[[^]]*\]\([^)]+\)", "", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"^#{1,6}\s+", "", value.strip())
    value = value.replace("<br>", "\n")
    value = _clean_latex_symbols(value)
    value = _markdown_to_html(value)
    return re.sub(r"[ \t]+", " ", value).strip()



def extract_segments_layout(source_path: Path, image_dir: Path) -> list[dict]:
    """Fast layout-aware extraction with stable page and box reading order."""
    image_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with fitz.open(source_path) as doc:
            page_count = len(doc)
    except Exception:
        page_count = 1
    
    # Process the document in chunks of 8 pages, running each chunk in a separate python subprocess.
    # This guarantees that all memory allocated by PyMuPDF/fitz is completely reclaimed by the OS
    # upon subprocess exit, keeping container memory usage under 300MB at all times.
    import subprocess
    import sys
    import json
    import tempfile
    
    chunks = []
    chunk_size = 8
    
    for start_idx in range(0, page_count, chunk_size):
        end_idx = min(start_idx + chunk_size, page_count)
        pages_list = list(range(start_idx, end_idx))
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            
        try:
            cmd = [
                sys.executable,
                "-c",
                "import pymupdf4llm, json; "
                f"chunks = pymupdf4llm.to_markdown(r'{source_path.as_posix()}', pages={pages_list}, page_chunks=True, write_images=True, image_path=r'{image_dir.as_posix()}', image_format='jpg', use_ocr=False, force_text=False, header=False, footer=False); "
                f"open(r'{tmp_path.as_posix()}', 'w', encoding='utf-8').write(json.dumps(chunks))"
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired as e:
                app.logger.error(f"Extraction subprocess timed out on pages {start_idx}-{end_idx}")
                raise RuntimeError(f"Extraction subprocess timed out on pages {start_idx}-{end_idx}") from e
            except subprocess.CalledProcessError as e:
                app.logger.error(f"Extraction subprocess failed on pages {start_idx}-{end_idx}. stderr: {e.stderr}")
                raise RuntimeError(f"Extraction subprocess failed: {e.stderr or e.output}") from e
            
            if tmp_path.exists():
                chunk_data = json.loads(tmp_path.read_text(encoding="utf-8"))
                chunks.extend(chunk_data)
            else:
                raise RuntimeError(f"Subprocess did not generate segments for pages {start_idx}-{end_idx}.")
        finally:
            tmp_path.unlink(missing_ok=True)
        
    segments = []
    for chunk in chunks:
        page = int(chunk["metadata"]["page_number"])
        markdown = chunk["text"]
        for box in chunk.get("page_boxes", []):
            kind = box["class"]
            if kind in {"page-header", "page-footer"}:
                continue
            start, stop = box["pos"]
            raw = markdown[start:stop].strip()
            if not raw:
                continue
            if kind == "picture":
                match = re.search(r"!\[[^]]*\]\(([^)]+)\)", raw)
                if match:
                    image_path = Path(match.group(1))
                    if not image_path.is_absolute():
                        image_path = BASE_DIR / image_path
                    if image_path.exists():
                        segments.append({"page": page, "type": "image", "src": image_path.resolve().as_uri()})
                continue
            if kind == "table":
                table_rows = []
                for line in raw.splitlines():
                    if not line.strip().startswith("|"):
                        continue
                    cells = [_plain_markdown(cell.strip()) for cell in line.strip().strip("|").split("|")]
                    if cells and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                        table_rows.append(cells)
                if table_rows:
                    segments.append({"page": page, "type": "table", "headers": table_rows[0], "rows": table_rows[1:]})
                continue

            text = _plain_markdown(raw)
            if not text:
                continue
            heading = kind in {"title", "section-header"}
            source_list = kind == "list-item"
            segments.append({
                "page": page,
                "type": "text",
                "text": text,
                "font_size": 24 if kind == "title" else (16 if heading else 10.5),
                "is_bold": heading,
                "preserve_lines": False,
                "docling_label": "section_header" if heading else kind.replace("-", "_"),
                "source_list": source_list,
            })

    for identifier, segment in enumerate(segments, start=1):
        segment["id"] = identifier
    if not any(segment.get("type", "text") == "text" for segment in segments):
        raise ValueError("No readable PDF content was found.")
    return segments


def structure_with_gemini(segments: list[dict]) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

    text_segments = [segment for segment in segments if segment.get("type", "text") == "text"]
    numbered_text = "\n\n".join(
        f"[SEGMENT {segment['id']} | PAGE {segment['page']} | "
        f"FONT {segment.get('font_size', 0):g} | BOLD {'YES' if segment.get('is_bold') else 'NO'}]\n"
        f"{segment['text']}"
        for segment in text_segments
    )
    client = genai.Client(api_key=api_key)
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=PROMPT.format(segments=numbered_text),
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": CLASSIFICATION_SCHEMA,
                    "temperature": 0,
                },
            )
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    data = response.parsed or json.loads(response.text)
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    if not isinstance(data, dict):
        raise RuntimeError("Gemini returned an invalid classification.")
    return data


def local_classification(segments: list[dict]) -> dict:
    """Classify common study-note structures without changing their text."""
    text_segments = [segment for segment in segments if segment.get("type", "text") == "text"]
    size_counts = Counter()
    for segment in text_segments:
        size_counts[round(float(segment.get("font_size", 0)), 1)] += len(segment.get("text", ""))
    body_size = size_counts.most_common(1)[0][0] if size_counts else 10.5

    first_page = [segment for segment in text_segments if segment.get("page") == 1]
    docling_titles = [segment for segment in first_page if segment.get("docling_label") == "title"]
    cover_titles = [
        segment for segment in first_page
        if re.search(r"\bTHE\s+STUDY\s+SUPERPACK\b", segment["text"], re.IGNORECASE)
        and not re.fullmatch(r"THE\s+STUDY\s+SUPERPACK", segment["text"], re.IGNORECASE)
    ]
    layout_titles = [
        segment for segment in first_page
        if segment.get("docling_label") == "section_header"
        and not re.fullmatch(r"[A-Z]{2,10}\s+(?:SEMESTER|SEM)\s*[IVX\d]+", segment["text"], re.IGNORECASE)
        and not re.fullmatch(r"THE\s+STUDY\s+SUPERPACK|INSTITUTION\s*:?", segment["text"], re.IGNORECASE)
    ]
    title_candidates = docling_titles or cover_titles or layout_titles or [
        segment for segment in first_page
        if not re.search(
            r"\b(?:semester|unit|superpack|prepared|institution|full study|detailed|quick-hit|glossary|multiple choice|practice questions|answer key)\b",
            segment["text"], re.IGNORECASE,
        )
        and not re.match(r"^[\u2022\u25cf\u25cb\u25aa]", segment["text"].lstrip())
    ] or first_page or text_segments
    title_id = max(
        title_candidates,
        key=lambda segment: (float(segment.get("font_size", 0)), bool(segment.get("is_bold")), -segment["id"]),
    )["id"]
    roman_numbers = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
    unit_headings = []
    for segment in text_segments:
        text = _clean_html(segment["text"])
        unit_match = re.match(r"^unit\s*[-\u2013\u2014:]?\s*(\d+|[ivx]+)\b", text, re.IGNORECASE)
        if unit_match:
            token = unit_match.group(1).lower()
            unit_number = int(token) if token.isdigit() else roman_numbers.get(token, len(unit_headings) + 1)
            unit_headings.append({"segment_id": segment["id"], "unit_number": unit_number})

    first_unit_id = min((u["segment_id"] for u in unit_headings), default=None)
    heading_ids, mcq_ids, qa_ids = [], [], []
    section = None
    
    for segment in text_segments:
        text = _clean_html(segment["text"])
        clean_q_text = re.sub(r"^[\u2022\u25cf\u25cb\u25aa\uf0b7\u200b\u2023\u2043\u2055\u25b6\-*+\s]+", "", text).strip()
        inside_unit = (first_unit_id is None) or (segment["id"] >= first_unit_id)
        
        unit_match = re.match(r"^unit\s*[-\u2013\u2014:]?\s*(\d+|[ivx]+)\b", text, re.IGNORECASE)
        if unit_match:
            section = None
            continue

        if re.search(r"multiple\s+choice|\bmcqs?\b", text, re.IGNORECASE):
            if inside_unit:
                section = "mcq"
                heading_ids.append(segment["id"])
                continue
        answer_heading = re.search(
            r"(short|long)\s+answer\s+questions?|(short|long)\s+question[\s\-–—]answers?",
            text, re.IGNORECASE
        )
        if answer_heading:
            if inside_unit:
                q_type = (answer_heading.group(1) or answer_heading.group(2)).lower()
                section = f"qa_{q_type}"
                heading_ids.append(segment["id"])
                continue

        is_question = (
            bool(re.match(r"^Q\s*\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]", clean_q_text, re.IGNORECASE))
            or (section in {"mcq", "qa_short"} and bool(re.match(r"^(?:Q\s*)?\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]", clean_q_text, re.IGNORECASE)))
            or (section == "qa_long" and bool(re.match(r"^Q\s*\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]", clean_q_text, re.IGNORECASE)))
            or (bool(re.match(r"^(?:Q\s*)?\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]", clean_q_text, re.IGNORECASE)) and clean_q_text.strip().endswith("?"))
        )
        if is_question and section == "mcq":
            mcq_ids.append(segment["id"])
            continue
        if is_question and section == "qa_short":
            qa_ids.append(segment["id"])
            continue
        if is_question and section == "qa_long":
            qa_ids.append(segment["id"])
            continue

        is_heading = (
            not re.fullmatch(r"answers?\s*:?\s*", text, re.IGNORECASE)
            and not re.match(r"^[\u2022\u25cf\u25cb\u25aa\uf0b7\u200b\u2023\u2043\u2055\u25b6\-*+]\s*", text)
            and bool(
                segment.get("docling_label") == "section_header"
                or segment.get("is_bold")
                and len(text) <= 120
                and (
                    float(segment.get("font_size", 0)) >= body_size - 0.2
                    or text.isupper()
                    or re.match(r"^(?:objectives?|key glossary|quick revision|detailed notes)\b", text, re.IGNORECASE)
                )
            )
        )
        if is_heading and segment["id"] != title_id:
            heading_ids.append(segment["id"])

    return {
        "title_segment_id": title_id,
        "unit_headings": unit_headings,
        "heading_segment_ids": heading_ids,
        "mcq_segment_ids": mcq_ids,
        "qa_segment_ids": qa_ids,
    }


def merge_classifications(local: dict, ai: dict) -> dict:
    """Keep deterministic source-pattern matches and add AI-only classifications."""
    units = {item["segment_id"]: item for item in ai.get("unit_headings", [])}
    units.update({item["segment_id"]: item for item in local.get("unit_headings", [])})
    return {
        "title_segment_id": local.get("title_segment_id") or ai.get("title_segment_id"),
        "unit_headings": [units[key] for key in sorted(units)],
        "heading_segment_ids": sorted(set(local.get("heading_segment_ids", [])) | set(ai.get("heading_segment_ids", []))),
        "mcq_segment_ids": sorted(set(local.get("mcq_segment_ids", [])) | set(ai.get("mcq_segment_ids", []))),
        "qa_segment_ids": sorted(set(local.get("qa_segment_ids", [])) | set(ai.get("qa_segment_ids", []))),
    }


def build_document(segments: list[dict], classification: dict) -> dict:
    by_id = {segment["id"]: segment for segment in segments}
    text_segments = [segment for segment in segments if segment.get("type", "text") == "text"]
    text_by_id = {segment["id"]: segment for segment in text_segments}
    title_id = classification.get("title_segment_id")
    if title_id not in text_by_id:
        title_id = text_segments[0]["id"]

    unit_headings = {
        item.get("segment_id"): item.get("unit_number")
        for item in classification.get("unit_headings", [])
        if item.get("segment_id") in text_by_id and isinstance(item.get("unit_number"), int)
    }
    headings = set(classification.get("heading_segment_ids", [])) & text_by_id.keys()
    mcqs = set(classification.get("mcq_segment_ids", [])) & text_by_id.keys()
    qas = set(classification.get("qa_segment_ids", [])) & text_by_id.keys()
    mcq_questions = {
        segment_id for segment_id in mcqs
        if re.match(
            r"^(?:Q\s*)?\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]",
            re.sub(r"^[\u2022\u25cf\u25cb\u25aa\uf0b7\u200b\u2023\u2043\u2055\u25b6\-*+\s]+", "", _clean_html(text_by_id[segment_id]["text"])).strip(),
            re.IGNORECASE
        )
    }
    qa_questions = {
        segment_id for segment_id in qas
        if re.match(
            r"^(?:Q\s*)?\d+[.)]\s*(?:[\"\u201c\u2018'(]\s*)?[A-Za-z]",
            re.sub(r"^[\u2022\u25cf\u25cb\u25aa\uf0b7\u200b\u2023\u2043\u2055\u25b6\-*+\s]+", "", _clean_html(text_by_id[segment_id]["text"])).strip(),
            re.IGNORECASE
        )
    }

    size_counts = Counter()
    for segment in text_segments:
        size = round(float(segment.get("font_size", 0)), 1)
        if size:
            size_counts[size] += len(segment["text"])
    body_size = size_counts.most_common(1)[0][0] if size_counts else 0
    first_unit_id = min(unit_headings, default=None)
    front_matter = [
        segment["text"]
        for segment in text_segments
        if first_unit_id and segment["id"] < first_unit_id and segment["id"] != title_id
    ]

    units = []
    current_unit = None
    current_number = None
    index = 0
    while index < len(segments):
        segment = segments[index]
        if first_unit_id and segment["id"] < first_unit_id:
            index += 1
            continue
        if segment["id"] == title_id:
            index += 1
            continue

        if segment.get("type") == "image":
            if current_unit is not None:
                current_unit["content"].append({"type": "image", "src": segment["src"]})
            index += 1
            continue

        if segment.get("type") == "table":
            if current_unit is None:
                current_number = 1
                current_unit = {"unit_number": 1, "heading": "Unit 1", "content": []}
                units.append(current_unit)
            current_unit["content"].append({
                "type": "table",
                "headers": segment["headers"],
                "rows": segment["rows"],
            })
            index += 1
            continue

        unit_number = unit_headings.get(segment["id"], current_number or 1)
        if unit_number < 1:
            unit_number = current_number or 1

        if current_unit is None or unit_number != current_number:
            current_number = unit_number
            current_unit = {"unit_number": unit_number, "heading": f"Unit {unit_number}", "content": []}
            units.append(current_unit)

        if segment["id"] in unit_headings:
            current_unit["heading"] = segment["text"]
            index += 1
            continue

        if segment["id"] in mcq_questions or segment["id"] in qa_questions:
            item_type = "mcq" if segment["id"] in mcq_questions else "qa"
            grouped = [segment]
            next_index = index + 1
            boundary_ids = set(unit_headings) | headings | mcq_questions | qa_questions
            while (
                next_index < len(segments)
                and segments[next_index]["id"] not in boundary_ids
                and segments[next_index].get("type", "text") == "text"
            ):
                grouped.append(segments[next_index])
                next_index += 1

            raw_lines = []
            for grouped_segment in grouped:
                lines = [line.strip() for line in grouped_segment.get("text", "").splitlines() if line.strip()]
                if item_type == "qa" and grouped_segment is not segment and grouped_segment.get("source_list"):
                    lines = [f"• {line}" for line in lines]
                raw_lines.extend(lines)
            question = raw_lines[0] if raw_lines else ""

            if item_type == "mcq":
                combined_text = " ".join(raw_lines)
                marker_pattern = re.compile(
                    r"\b([A-Da-d])[.)]\s+"                     # a) or A) or a. or A.
                    r"|(?<=\s)([A-D])\s+(?=[A-Z(0-9])"         # A Option
                    r"|\b(Answer|Ans|answer|ans|ANSWER|ANS)\s*:\s*" # Answer: or Ans:
                )
                markers = []
                for match in marker_pattern.finditer(combined_text):
                    label = match.group(1) or match.group(2)
                    is_answer = bool(match.group(3))
                    markers.append({
                        "start": match.start(),
                        "end": match.end(),
                        "label": label,
                        "is_answer": is_answer
                    })
                    if is_answer:
                        break
                if markers:
                    question = combined_text[:markers[0]["start"]].strip()
                    options = []
                    answer = ""
                    for i, marker in enumerate(markers):
                        start_val = marker["end"]
                        end_val = markers[i+1]["start"] if i + 1 < len(markers) else len(combined_text)
                        chunk = combined_text[start_val:end_val].strip()
                        if marker["is_answer"]:
                            answer = chunk
                        else:
                            options.append({
                                "label": marker["label"].lower(),
                                "text": chunk
                            })
                    question = re.sub(r"\s*-\s*$", "", question).strip()

                else:
                    question = raw_lines[0] if raw_lines else ""
                    options = []
                    answer = ""
                current_unit["content"].append({
                    "type": "mcq", "question": question, "options": options,
                    "answer": answer, "text": "\n".join(raw_lines),
                })
            else:
                answer_start = next(
                    (position for position, line in enumerate(raw_lines[1:], start=1)
                     if re.match(r"^Answer\s*:?", _clean_html(line), re.IGNORECASE)),
                    None,
                )
                if answer_start is not None:
                    question = " ".join(raw_lines[:answer_start])
                    answer_lines = raw_lines[answer_start:]
                else:
                    answer_lines = raw_lines[1:]
                answer_text = "\n".join(answer_lines)
                answer_text = re.sub(r"^(?:Answer\s*:?\s*)+", "", answer_text, flags=re.IGNORECASE)
                current_unit["content"].append({
                    "type": "qa", "question": question,
                    "answer": answer_text, "text": "\n".join(raw_lines),
                })
            index = next_index
            continue

        if segment["id"] in headings:
            current_unit["content"].append({
                "type": "heading", "text": segment["text"],
                "is_section_heading": segment["text"].isupper(),
                "heading_level": (
                    "subheading"
                    if float(segment.get("font_size", 0)) < 13.5
                    or re.match(r"^\d+(?:\.\d+)*\b", _clean_html(segment["text"]))
                    or _clean_html(segment["text"]).endswith(":")
                    else "section"
                ),
            })
        else:
            source_heading = bool(
                body_size
                and segment.get("is_bold")
                and float(segment.get("font_size", 0)) >= body_size + 1.4
            )
            current_unit["content"].append({
                "type": "heading" if source_heading else "paragraph",
                "text": segment["text"],
                "is_answer": bool(re.match(r"^answer\s*(?::|$)", _clean_html(segment["text"]), re.IGNORECASE)),
                "is_section_heading": source_heading and segment["text"].isupper(),
                "heading_level": (
                    "subheading"
                    if re.match(r"^\d+\.\d+\b", _clean_html(segment["text"])) or _clean_html(segment["text"]).endswith(":")
                    else "section"
                ),
                "preserve_lines": bool(segment.get("preserve_lines")),
                "source_list": bool(segment.get("source_list")),
            })
        index += 1

    return {
        "title": " ".join(by_id[title_id]["text"].splitlines()),
        "front_matter": front_matter,
        "units": units,
    }


def _component_kind(heading: str) -> str | None:
    text = re.sub(r"\s+", " ", heading).strip().lower()
    if re.search(r"(?:deep[ -]?dive|detailed)\s+notes", text):
        return "notes"
    if re.search(r"quick(?:[ -]hit)?\s+revision|key\s+points", text):
        return "summary"
    if "glossary" in text:
        return "glossary"
    if re.search(r"multiple\s+choice|\bmcqs?\b", text):
        return "mcq"
    if re.search(r"short\s+answer\s+questions?", text):
        return "short_qa"
    if re.search(r"long\s+answer\s+questions?", text):
        return "long_qa"
    return None


def _cover_title(text: str) -> str:
    text = _clean_html(text)
    text = re.split(r"\bTHE\s+STUDY\s+SUPERPACK\b|\bFULL\s+STUDY\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if not text.isupper():
        return text
    acronyms = {"AI", "BBA", "BCA", "DBMS", "ICT", "IT", "MBA", "MCA"}
    minor = {"and", "for", "of", "the"}
    words = text.split()
    return " ".join(
        word if word in acronyms else (word.lower() if index and word.lower() in minor else word.capitalize())
        for index, word in enumerate(words)
    )


def _cover_subtitle(front: list[str]) -> str:
    joined = " ".join(front)
    semester = re.search(r"\b([A-Z]{2,10})\s+(?:SEMESTER|SEM)\s*[-:]?\s*([IVX]+|\d+)\b", joined, re.IGNORECASE)
    units = re.search(r"\bUNITS?\s*([0-9][0-9,\s&-]*)", joined, re.IGNORECASE)
    if not semester:
        return ""
    roman = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6"}
    result = f"{semester.group(1).upper()} · Semester {roman.get(semester.group(2).upper(), semester.group(2))}"
    if units:
        result += f" · Units {units.group(1).strip(' ,:-')}"
    return result


def componentize_document(document: dict) -> dict:
    """Map preserved source items to fixed Notes Ninja visual components."""
    default_labels = {
        "notes": "Deep-Dive Notes",
        "summary": "Quick-Hit Revision - Key Points",
        "glossary": "Key Glossary Terms",
        "mcq": "Multiple Choice Questions (MCQs)",
        "short_qa": "Short Answer Questions",
        "long_qa": "Long Answer Question",
    }
    mcq_count = 0
    for unit in document["units"]:
        section_counter = 0
        subheading_counter = 0
        unit["display_heading"] = re.sub(
            r"^unit\s*[-\u2013\u2014:]?\s*(?:\d+|[ivx]+)\s*[-\u2013\u2014:]?\s*",
            "", unit["heading"], flags=re.IGNORECASE,
        ).strip() or unit["heading"]
        content_items = unit["content"]
        if content_items and re.fullmatch(
            r"\(?\s*part\s+\d+\s*\)?", content_items[0].get("text", ""), re.IGNORECASE
        ):
            unit["display_heading"] += f" {content_items[0]['text'].strip()}"
            content_items = content_items[1:]
        blocks = []
        current = {"type": "notes", "label": default_labels["notes"], "items": []}

        def flush():
            nonlocal current
            if current["items"]:
                blocks.append(current)

        for item in content_items:
            if item["type"] == "paragraph" and item.get("source_list"):
                numbered = bool(re.match(r"^\d+[.)]\s+", _clean_html(item["text"])))
                list_kind = "numbered" if numbered else "bullets"
                clean_text = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", item["text"]).strip()
                if current["type"] == "notes" and current["items"] and current["items"][-1].get("type") == "paragraph" and current["items"][-1].get("list_kind") == list_kind:
                    current["items"][-1]["list_items"].append(clean_text)
                    continue
                else:
                    item["list_kind"] = list_kind
                    item["list_items"] = [clean_text]
            if item["type"] == "paragraph" and item.get("preserve_lines"):
                lines = [line.strip() for line in item["text"].splitlines() if line.strip()]
                numbered = all(re.match(r"^\d+[.)]\s+", _clean_html(line)) for line in lines)
                marked = all(
                    re.match(r"^(?:[\u2022\u25cf\u25aa\u25b6\uf0d8]|\d+[.)])\s+", _clean_html(line))
                    for line in lines
                )
                if marked:
                    item["list_kind"] = "numbered" if numbered else "bullets"
                    item["list_items"] = [
                        re.sub(r"^(?:[\u2022\u25cf\u25aa\u25b6\uf0d8]|\d+[.)])\s+", "", line)
                        for line in lines
                    ]

            if item["type"] in {"mcq", "qa"}:
                question_match = re.match(
                    r"^(?:Q\s*)?(\d+)[.)]\s*(.*)$", _clean_html(item.get("question", "")), re.IGNORECASE
                )
                item["number"] = question_match.group(1) if question_match else ""
                item["question_body"] = question_match.group(2) if question_match else item.get("question", "")
            if item["type"] == "mcq":
                answer_match = re.match(r"^\s*\(?([A-Da-d])\)?", _clean_html(item.get("answer", "")))
                item["answer_letter"] = answer_match.group(1).upper() if answer_match else ""

            if item["type"] == "heading":
                kind = _component_kind(item["text"])
                if kind:
                    flush()
                    current = {"type": kind, "label": default_labels[kind], "items": []}
                    continue
                
                # Auto-number headings inside main 'notes' block
                if current["type"] == "notes":
                    clean_text = re.sub(r"^\s*(?:\d+(?:\.\d+)*\b[:.)\s-]*)+", "", item["text"]).strip()
                    if "decision" in clean_text.lower():
                        item["text"] = "Decision Rule"
                    elif item.get("heading_level") == "section":
                        section_counter += 1
                        subheading_counter = 0
                        item["text"] = f"{section_counter}. {clean_text}"
                    elif item.get("heading_level") == "subheading":
                        subheading_counter += 1
                        item["text"] = f"{section_counter}.{subheading_counter} {clean_text}"

            inferred = None
            if item["type"] == "mcq":
                inferred = "mcq"
                mcq_count += 1
            elif item["type"] == "qa" and current["type"] not in {"short_qa", "long_qa"}:
                inferred = "short_qa"

            if inferred and current["type"] != inferred:
                flush()
                current = {"type": inferred, "label": default_labels[inferred], "items": []}
            if current["type"] == "glossary" and item["type"] == "paragraph":
                item["text"] = re.sub(r"^[\u2022\u25cf\u25cb\u25aa\uf0b7\u200b\u2023\u2043\u2055\u25b6\-*+\s]+", "", item["text"]).strip()
            current["items"].append(item)
        flush()
        for block in blocks:
            if block["type"] != "summary":
                continue
            merged = []
            for item in block["items"]:
                starts_point = bool(re.match(r"^[\s\u200b]*[\u2022\u25cf\u25cb\u25aa\uf0b7]", item.get("text", "")))
                if item.get("type") == "paragraph" and merged and "text" in merged[-1] and not starts_point:
                    merged[-1]["text"] += " " + item.get("text", "").strip()
                else:
                    merged.append(item)
            block["items"] = merged
        unit["blocks"] = blocks

    document["mcq_count"] = mcq_count
    document.setdefault("footer_subject", _clean_html(document["title"]))
    front = [_clean_html(text) for text in document.get("front_matter", [])]
    source_title = document["title"]
    document["title"] = _cover_title(source_title)
    document["cover_subtitle"] = _cover_subtitle([_clean_html(source_title), *front])
    document["cover_scope"] = ""
    document["cover_institution"] = next(
        (text for text in reversed(front) if "university" in text.lower() or "college" in text.lower()), ""
    )
    prepared = next((text for text in front if "prepared by" in text.lower()), "")
    document["cover_prepared_by"] = prepared.split(":", 1)[-1].strip() if prepared else ""
    document["cover_pills"] = [
        "Deep-Dive Notes", "Quick Revision", "Key Glossary",
        f"{mcq_count} MCQs" if mcq_count else "MCQs", "Practice Q&A", "Answer Key",
    ]
    return document


def render_pdf(html: str, output_path: Path) -> None:
    import subprocess
    import tempfile
    
    exe_path = BASE_DIR / "weasyprint-windows" / "dist" / "weasyprint.exe"
    if exe_path.exists():
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as temp_html:
            temp_html.write(html)
            temp_html_path = temp_html.name
        
        try:
            cmd = [
                str(exe_path),
                "--base-url", str(BASE_DIR),
                temp_html_path,
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Standalone WeasyPrint failed: {result.stderr}")
        finally:
            try:
                os.unlink(temp_html_path)
            except Exception:
                pass
    else:
        # Run WeasyPrint in a subprocess on Linux to completely isolate memory
        import sys
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as temp_html:
            temp_html.write(html)
            temp_html_path = temp_html.name
        try:
            cmd = [
                sys.executable,
                "-m",
                "weasyprint",
                "--base-url", str(BASE_DIR),
                temp_html_path,
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                app.logger.warning(f"Subprocess WeasyPrint failed (rc={result.returncode}), attempting inline fallback. Stderr: {result.stderr}")
                HTML(string=html, base_url=str(BASE_DIR)).write_pdf(output_path)
        except Exception as exc:
            app.logger.warning(f"Subprocess WeasyPrint raised exception: {exc}, attempting inline fallback.")
            HTML(string=html, base_url=str(BASE_DIR)).write_pdf(output_path)
        finally:
            try:
                os.unlink(temp_html_path)
            except Exception:
                pass


def validate_rendered_content(segments: list[dict], classification: dict, output_path: Path) -> None:
    """Reject an output that lost a meaningful part of the ordered source content."""
    first_unit = min(
        (item["segment_id"] for item in classification.get("unit_headings", [])),
        default=None,
    )
    title_id = classification.get("title_segment_id")
    source_parts = []
    for segment in segments:
        if first_unit and segment["id"] < first_unit and segment["id"] != title_id:
            continue
        if segment.get("type", "text") == "text":
            source_parts.append(segment["text"])
        elif segment.get("type") == "table":
            source_parts.extend(cell for row in [segment["headers"], *segment["rows"]] for cell in row)

    words = lambda value: set(re.findall(r"[A-Za-z0-9]{4,}", value.lower()))
    expected = words(" ".join(source_parts))
    with fitz.open(output_path) as pdf:
        actual = words(" ".join(page.get_text() for page in pdf))
    missing = expected - actual
    if len(missing) > max(3, int(len(expected) * 0.02)):
        app.logger.warning(f"Content validation warning: {len(missing)} source terms were not rendered in the final PDF: {list(missing)[:20]}")


def _cross_page_mcqs(document) -> dict:
    layout = defaultdict(lambda: {"cards": [], "clear": []})
    question_pattern = re.compile(r"^(?:Q\s*)?(\d+)[.)]\s*(.+)", re.IGNORECASE)
    option_pattern = re.compile(r"^([A-D])[.)]\s*(.+)", re.IGNORECASE)
    answer_pattern = re.compile(r"^Answer\s*:\s*\(?([A-D])\)?[.)]?\s*(.*)", re.IGNORECASE)

    def page_lines(page):
        result = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text = "".join(span.get("text", "") for span in line.get("spans", []))
                text = re.sub(r"\s+", " ", text.replace("\u200b", "")).strip()
                text = re.sub(r'"([^"\n]+)"', r'“\1”', text)
                if text and not re.fullmatch(r"\d+", text):
                    result.append({"text": text, "bbox": fitz.Rect(line["bbox"])})
        return sorted(result, key=lambda item: (round(item["bbox"].y0), item["bbox"].x0))

    for page_index in range(len(document) - 1):
        current, following = page_lines(document[page_index]), page_lines(document[page_index + 1])
        starts = [index for index, line in enumerate(current) if question_pattern.match(line["text"])]
        if not starts:
            continue
        start = starts[-1]
        if any(answer_pattern.match(line["text"]) for line in current[start + 1:]):
            continue
        next_question = next((index for index, line in enumerate(following) if question_pattern.match(line["text"])), len(following))
        continuation = following[:next_question]
        answer_index = next((index for index, line in enumerate(continuation) if answer_pattern.match(line["text"])), None)
        if answer_index is None:
            continue

        group = current[start:] + continuation[:answer_index + 1]
        question_match = question_pattern.match(group[0]["text"])
        question_parts = [question_match.group(2)]
        options, current_option = {}, None
        for line in group[1:-1]:
            option_match = option_pattern.match(line["text"])
            if option_match:
                current_option = option_match.group(1).upper()
                options[current_option] = option_match.group(2)
            elif current_option:
                options[current_option] += " " + line["text"]
            else:
                question_parts.append(line["text"])
        if len(options) < 2:
            continue

        answer = answer_pattern.match(group[-1]["text"]).group(1).upper()
        layout[page_index]["clear"].append((current[start]["bbox"].y0 - 4, current[-1]["bbox"].y1 + 4))
        layout[page_index + 1]["clear"].append((continuation[0]["bbox"].y0 - 4, continuation[answer_index]["bbox"].y1 + 4))
        layout[page_index + 1]["cards"].append({
            "number": question_match.group(1),
            "question": " ".join(question_parts),
            "options": options,
            "answer": answer,
            "answer_text": answer_pattern.match(group[-1]["text"]).group(2).strip(),
            "source_y0": continuation[0]["bbox"].y0 - 4,
            "source_y1": continuation[answer_index]["bbox"].y1 + 4,
        })
    return layout


def _mcq_cards(source_page, target_page, y_offset: float, regular_font: Path, bold_font: Path, answer_font: Path, extra=None) -> None:
    regular_metrics = fitz.Font(fontfile=str(regular_font))
    bold_metrics = fitz.Font(fontfile=str(bold_font))
    lines = []
    for block in source_page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            text = re.sub(r"\s+", " ", text.replace("\u200b", "")).strip()
            text = re.sub(r'"([^"\n]+)"', r'“\1”', text)
            if text:
                lines.append({"text": text, "bbox": fitz.Rect(line["bbox"])})
    lines.sort(key=lambda line: (round(line["bbox"].y0), line["bbox"].x0))

    question_pattern = re.compile(r"^(?:Q\s*)?(\d+)[.)]\s*(.+)", re.IGNORECASE)
    option_pattern = re.compile(r"^([A-D])[.)]\s*(.+)", re.IGNORECASE)
    answer_pattern = re.compile(r"^Answer\s*:\s*\(?([A-D])\)?[.)]?\s*(.*)", re.IGNORECASE)

    cards = []
    for start, line in enumerate(lines):
        question_match = question_pattern.match(line["text"])
        if not question_match:
            continue
        end = next(
            (index for index in range(start + 1, len(lines)) if answer_pattern.match(lines[index]["text"])),
            None,
        )
        next_question = next(
            (index for index in range(start + 1, len(lines)) if question_pattern.match(lines[index]["text"])),
            len(lines),
        )
        if end is None or end >= next_question:
            continue

        question_parts = [question_match.group(2)]
        options = {}
        current_option = None
        for item in lines[start + 1:end]:
            option_match = option_pattern.match(item["text"])
            if option_match:
                current_option = option_match.group(1).upper()
                options[current_option] = option_match.group(2)
            elif current_option:
                options[current_option] += " " + item["text"]
            else:
                question_parts.append(item["text"])
        if len(options) < 2:
            continue

        answer_match = answer_pattern.match(lines[end]["text"])
        answer = answer_match.group(1).upper()
        group = lines[start:end + 1]
        cards.append({
            "number": question_match.group(1),
            "question": " ".join(question_parts),
            "options": options,
            "answer": answer,
            "answer_text": answer_match.group(2).strip(),
            "source_y0": group[0]["bbox"].y0 + y_offset - 4,
            "source_y1": group[-1]["bbox"].y1 + y_offset + 4,
        })

    # Measurements taken from the approved Notes Ninja reference PDF.
    x0, x1 = 48.19, source_page.rect.width - 48.19
    if extra:
        for clear_y0, clear_y1 in extra["clear"]:
            target_page.draw_rect(fitz.Rect(x0, clear_y0 + y_offset, x1, clear_y1 + y_offset), color=None, fill=(1, 1, 1))
        cards.extend({**card, "source_y0": card["source_y0"] + y_offset, "source_y1": card["source_y1"] + y_offset} for card in extra["cards"])

    if not cards:
        return

    cards.sort(key=lambda card: card["source_y0"])
    inner_width = x1 - x0 - 28.7
    source_top = min(card["source_y0"] for card in cards)
    source_bottom = max(card["source_y1"] for card in cards)
    prepared = []
    for item in cards:
        question = f"Q{item['number']}. {item['question']}"
        question_lines = max(1, int(bold_metrics.text_length(question, fontsize=10.5) / inner_width) + 1)
        option_lines = 0
        for letter, text in item["options"].items():
            width = regular_metrics.text_length(f"{letter}) {text}", fontsize=10.5)
            option_lines += max(1, int(width / (inner_width - 25.5)) + 1)
        answer_text = item.get("answer_text") or item["options"].get(item["answer"], "")
        answer_width = bold_metrics.text_length("Answer: ", fontsize=10.5) + regular_metrics.text_length(
            f"({item['answer'].lower()}) {answer_text}", fontsize=10.5
        )
        answer_lines = max(1, int(answer_width / inner_width) + 1)
        height = 14.4 + question_lines * 16.3 + 3.6 + option_lines * 16.3 + 6.3 + answer_lines * 16.3 + 10
        prepared.append({
            **item,
            "question_text": question,
            "question_lines": question_lines,
            "option_lines": option_lines,
            "answer_text": answer_text,
            "answer_lines": answer_lines,
            "height": height,
        })

    gap = 8.5
    total_height = sum(item["height"] for item in prepared) + gap * (len(prepared) - 1)
    following = [
        line["bbox"].y0 + y_offset
        for line in lines
        if line["bbox"].y0 + y_offset > source_bottom + 2 and not re.fullmatch(r"\d+", line["text"])
    ]
    available_bottom = min(following, default=target_page.rect.height - 35) - 8
    if source_top + total_height > available_bottom:
        return

    target_page.draw_rect(fitz.Rect(x0, source_top, x1, max(source_bottom, source_top + total_height)), color=None, fill=(1, 1, 1))
    cursor = source_top
    for item in prepared:
        y0, y1 = cursor, cursor + item["height"]
        card = fitz.Rect(x0, y0, x1, y1)
        target_page.draw_rect(
            card,
            color=(0.863, 0.914, 0.898),
            fill=(0.969, 0.988, 0.980),
            width=0.75,
            radius=0.035,
        )
        target_page.draw_line(
            fitz.Point(x0 + 1.5, y0 + 2.5),
            fitz.Point(x0 + 1.5, y1 - 2.5),
            color=(0, 0.529, 0.373),
            width=3,
        )
        question_rect = fitz.Rect(x0 + 14.35, y0 + 12, x1 - 14.35, y0 + 12 + item["question_lines"] * 16.3)
        target_page.insert_textbox(
            question_rect,
            item["question_text"],
            fontname="body-bold", fontfile=str(bold_font), fontsize=10.5, lineheight=1.25,
            color=(0.09, 0.125, 0.114),
        )

        option_top = question_rect.y1 + 3.5
        for letter, text in item["options"].items():
            option_width = regular_metrics.text_length(f"{letter}) {text}", fontsize=10.5)
            line_count = max(1, int(option_width / (inner_width - 25.5)) + 1)
            option_rect = fitz.Rect(x0 + 39.85, option_top, x1 - 14.35, option_top + line_count * 16.3)
            target_page.insert_textbox(
                option_rect,
                f"{letter.lower()}) {text}",
                fontname="body", fontfile=str(regular_font), fontsize=10.5, lineheight=1.25,
                color=(0.09, 0.125, 0.114),
            )
            option_top += line_count * 16.3

        answer_y = option_top + 6.3
        answer_label_width = bold_metrics.text_length("Answer: ", fontsize=10.5)
        target_page.insert_text(
            fitz.Point(x0 + 14.35, answer_y + 10.5),
            "Answer: ",
            fontname="body-bold", fontfile=str(bold_font), fontsize=10.5, color=(0, 0.407, 0.286),
        )
        target_page.insert_textbox(
            fitz.Rect(x0 + 14.35 + answer_label_width, answer_y, x1 - 14.35, y1 - 7),
            f"({item['answer'].lower()}) {item['answer_text']}",
            fontname="body", fontfile=str(regular_font), fontsize=10.5, lineheight=1.25,
            color=(0, 0.407, 0.286),
        )
        cursor = y1 + gap


def render_branded_pdf(source_path: Path, output_path: Path, title: str | None = None) -> None:
    """Preserve every source page exactly and add branding outside its canvas."""
    green = (0, 0.529, 0.373)
    gray = (0.36, 0.39, 0.38)
    top_space = 0
    font_file = BASE_DIR / "static" / "fonts" / "LiberationSans-Regular.ttf"
    body_bold_file = BASE_DIR / "static" / "fonts" / "LiberationSans-Bold.ttf"
    bold_font_file = BASE_DIR / "static" / "fonts" / "Poppins-Bold.ttf"

    with fitz.open(source_path) as source, fitz.open() as output:
        watermark_images = []
        repeated_sizes = Counter()
        for page in source:
            for image in page.get_images(full=True):
                rects = page.get_image_rects(image[0])
                if not rects:
                    continue
                rect = rects[0]
                large_centered = (
                    rect.width > page.rect.width * 0.55
                    and rect.height > page.rect.height * 0.45
                    and abs(rect.x0 + rect.x1 - page.rect.width) < page.rect.width * 0.2
                )
                if large_centered and image[1]:
                    signature = (image[2], image[3])
                    repeated_sizes[signature] += 1
                    watermark_images.append((page, image[0], signature))
        recurring = {size for size, count in repeated_sizes.items() if count >= max(2, len(source) * 0.6)}
        for page, xref, signature in watermark_images:
            if signature in recurring:
                page.delete_image(xref)
        cross_page_layout = _cross_page_mcqs(source)

        first_width, first_height = source[0].rect.width, source[0].rect.height
        cover = output.new_page(width=first_width, height=first_height)
        cover.insert_textbox(
            fitz.Rect(48.19, first_height * 0.36, first_width - 48.19, first_height * 0.39),
            "N O T E S  N I N J A",
            fontname="body-bold", fontfile=str(body_bold_file), fontsize=11, color=green,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        clean_title = re.sub(r"(?i)\.docx.*$|\s*\(\d+\)$", "", title or source.metadata.get("title") or "Study Notes")
        clean_title = " ".join(clean_title.replace("_", " ").split())
        title_rect = fitz.Rect(48.19, first_height * 0.405, first_width - 48.19, first_height * 0.53)
        cover_title_font = fitz.Font(fontfile=str(body_bold_file))
        title_size = 28
        while title_size >= 18:
            estimated_lines = max(1, int(cover_title_font.text_length(clean_title, fontsize=title_size) / title_rect.width) + 1)
            if estimated_lines * title_size * 1.25 <= title_rect.height:
                break
            title_size -= 1
        cover.insert_textbox(
            title_rect, clean_title,
            fontname="body-bold", fontfile=str(body_bold_file), fontsize=title_size, lineheight=1.05,
            color=(0.09, 0.125, 0.114),
            align=fitz.TEXT_ALIGN_CENTER,
        )
        cover.insert_textbox(
            fitz.Rect(48.19, first_height * 0.56, first_width - 48.19, first_height * 0.60),
            "Clean, structured study notes",
            fontname="body", fontfile=str(font_file), fontsize=10.5, color=gray,
        )
        cover.insert_textbox(
            fitz.Rect(0, first_height - 33, first_width, first_height - 19),
            "Notes Ninja  \u2022  1", fontname="body", fontfile=str(font_file), fontsize=8,
            color=gray, align=fitz.TEXT_ALIGN_CENTER,
        )

        for index, source_page in enumerate(source):
            width, height = source_page.rect.width, source_page.rect.height
            page = output.new_page(width=width, height=height)
            page.show_pdf_page(fitz.Rect(0, 0, width, height), source, index)
            _mcq_cards(source_page, page, top_space, font_file, body_bold_file, bold_font_file, cross_page_layout.get(index))
            for block in source_page.get_text("dict").get("blocks", []):
                if block.get("type") != 0 or block["bbox"][1] < height * 0.92:
                    continue
                block_text = "".join(
                    span.get("text", "")
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                ).strip()
                if re.fullmatch(r"(?:Page\s*)?\d+", block_text, re.IGNORECASE):
                    page.draw_rect(fitz.Rect(block["bbox"]) + (-2, -2, 2, 2), color=None, fill=(1, 1, 1))
            page.insert_textbox(
                fitz.Rect(0, height - 33, width, height - 19),
                f"Notes Ninja  \u2022  Page {index + 2}",
                fontname="body",
                fontfile=str(font_file),
                fontsize=8,
                color=gray,
                align=fitz.TEXT_ALIGN_CENTER,
            )

        metadata = source.metadata.copy()
        metadata["producer"] = "Notes Ninja PDF Formatter"
        output.set_metadata(metadata)
        output.save(output_path, garbage=4, deflate=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/logs")
def get_logs():
    log_file = UPLOAD_DIR / "app.log"
    if not log_file.exists():
        return "No logs found.", 404
    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
        last_lines = lines[-500:]
        return "<pre>" + "\n".join(last_lines) + "</pre>"
    except Exception as exc:
        return f"Error reading logs: {exc}", 500


def _update_status(job_id, status, progress, message="", error=None, filename=None):
    status_path = UPLOAD_DIR / f"{job_id}.status.json"
    data = {"status": status, "progress": progress, "message": message}
    if error:
        data["error"] = error
    if filename:
        data["filename"] = filename
    status_path.write_text(json.dumps(data), encoding="utf-8")


def _process_pdf_async(job_id, source_path, output_path, image_dir, filename):
    app.logger.info(f"[{job_id}] Starting async layout redesign for: {filename}")
    _update_status(job_id, "processing", 5, "Initializing processing...", filename=filename)
    try:
        try:
            with app.app_context():
                try:
                    with fitz.open(source_path) as doc:
                        page_count = len(doc)
                except Exception:
                    page_count = 1
                
                if page_count > 100:
                    app.logger.info(f"[{job_id}] Document has {page_count} pages. Exceeds safe redesign threshold of 100 pages. Swapping to fast branded PDF fallback to prevent server crash.")
                    _update_status(job_id, "processing", 50, "Redesigning document using branded fallback engine...", filename=filename)
                    render_branded_pdf(source_path, output_path, filename)
                else:
                    _update_status(job_id, "processing", 10, "Extracting text and layout segments from PDF...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 1: Extracting text & layout segments from source PDF...")
                    segments = extract_segments_layout(source_path, image_dir)
                    app.logger.info(f"[{job_id}] Extracted {len(segments)} segments successfully.")
                    
                    _update_status(job_id, "processing", 25, "Running layout structure classification...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 2: Running local layout classification...")
                    classification = local_classification(segments)
                    
                    _update_status(job_id, "processing", 35, "Building structured document...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 3: Building and formatting document structures...")
                    document = build_document(segments, classification)
                    clean_title = re.sub(r"(?i)\.docx.*$|\s*\(\d+\)$", "", Path(filename).stem)
                    clean_title = " ".join(clean_title.replace("_", " ").split())
                    original_title = document["title"]
                    document["title"] = original_title or clean_title
                    document["footer_subject"] = _cover_title(original_title)
                    document = componentize_document(document)
                    
                    # 1. Render Cover Page PDF
                    _update_status(job_id, "processing", 40, "Compiling Cover Page layout...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 4: Compiling Cover Page HTML template...")
                    cover_pdf_path = UPLOAD_DIR / f"{job_id}.cover.pdf"
                    cover_html = render_template("notesninja.html", document=document, skip_units=True)
                    
                    # Free segments/classification before compiling PDF to optimize memory
                    app.logger.info(f"[{job_id}] Cleaning extraction memory before rendering...")
                    del segments
                    del classification
                    import gc
                    gc.collect()
                    
                    _update_status(job_id, "processing", 45, "Generating Cover Page PDF...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 5: Rendering Cover Page PDF via WeasyPrint...")
                    render_pdf(cover_html, cover_pdf_path)
                    app.logger.info(f"[{job_id}] Cover Page rendered successfully.")
                    
                    # 2. Render each Unit PDF
                    unit_pdf_paths = []
                    original_units = document.get("units", [])
                    if original_units:
                        app.logger.info(f"[{job_id}] Step 6: Rendering {len(original_units)} units individually to stay under RAM limit...")
                        for index, unit in enumerate(original_units):
                            unit_progress = 50 + int((index / len(original_units)) * 40)
                            unit_name = unit.get("display_heading") or f"Unit {unit.get('unit_number')}"
                            _update_status(job_id, "processing", unit_progress, f"Rendering {unit_name} (Section {index + 1} of {len(original_units)})...", filename=filename)
                            
                            app.logger.info(f"[{job_id}] Rendering Unit {index + 1}/{len(original_units)}: {unit.get('display_heading')}...")
                            unit_pdf_path = UPLOAD_DIR / f"{job_id}.unit_{index}.pdf"
                            
                            unit_doc = document.copy()
                            unit_doc["units"] = [unit]
                            
                            unit_html = render_template("notesninja.html", document=unit_doc, skip_cover=True)
                            
                            # Force gc between unit compiles
                            gc.collect()
                            
                            render_pdf(unit_html, unit_pdf_path)
                            unit_pdf_paths.append(unit_pdf_path)
                    else:
                        app.logger.info(f"[{job_id}] Step 6: No units found to render.")
                    
                    del document
                    gc.collect()
                    
                    # 3. Merge Cover and Units using PyMuPDF (fitz)
                    _update_status(job_id, "processing", 92, "Merging redesigned page layouts...", filename=filename)
                    app.logger.info(f"[{job_id}] Step 7: Merging cover and unit PDFs into final output...")
                    with fitz.open() as output_pdf:
                        if cover_pdf_path.exists():
                            with fitz.open(cover_pdf_path) as cover:
                                output_pdf.insert_pdf(cover)
                            cover_pdf_path.unlink(missing_ok=True)
                        
                        for path in unit_pdf_paths:
                            if path.exists():
                                with fitz.open(path) as unit_pdf:
                                    output_pdf.insert_pdf(unit_pdf)
                                path.unlink(missing_ok=True)
                        
                        output_pdf.save(output_path)
                    app.logger.info(f"[{job_id}] PDF compilation and merging completed successfully!")
        except Exception:
            _update_status(job_id, "processing", 95, "Design failed, preparing basic branded fallback...", filename=filename)
            app.logger.exception(f"[{job_id}] Layout conversion failed; falling back to branded PDF pages")
            import gc
            gc.collect()
            render_branded_pdf(source_path, output_path, filename)
        
        if not output_path.exists():
            raise RuntimeError("Failed to generate output PDF file.")
            
        _update_status(job_id, "completed", 100, "Redesign complete!", filename=filename)
    except Exception as exc:
        app.logger.exception("PDF formatting failed")
        _update_status(job_id, "failed", 0, "Error occurred during redesign.", error=str(exc))
    finally:
        source_path.unlink(missing_ok=True)
        shutil.rmtree(image_dir, ignore_errors=True)
        (UPLOAD_DIR / f"{job_id}.cover.pdf").unlink(missing_ok=True)
        for i in range(100):
            (UPLOAD_DIR / f"{job_id}.unit_{i}.pdf").unlink(missing_ok=True)


@app.post("/format")
def format_pdf():
    uploaded = request.files.get("pdf")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Please choose a PDF file."), 400
    if Path(uploaded.filename).suffix.lower() != ".pdf":
        return jsonify(error="Only PDF files are supported."), 400

    job_id = uuid.uuid4().hex
    source_path = UPLOAD_DIR / f"{job_id}.pdf"
    output_path = UPLOAD_DIR / f"{job_id}.output.pdf"
    image_dir = UPLOAD_DIR / f"{job_id}.images"
    status_path = UPLOAD_DIR / f"{job_id}.status.json"

    try:
        uploaded.save(source_path)
        _update_status(job_id, "processing", 0, "PDF upload successful, starting worker thread...", filename=uploaded.filename)
        
        # Start background processing thread
        thread = Thread(
            target=_process_pdf_async,
            args=(job_id, source_path, output_path, image_dir, uploaded.filename)
        )
        thread.start()
        
        return jsonify(job_id=job_id), 202
    except Exception as exc:
        source_path.unlink(missing_ok=True)
        status_path.unlink(missing_ok=True)
        shutil.rmtree(image_dir, ignore_errors=True)
        return jsonify(error=str(exc)), 500


@app.get("/status/<job_id>")
def get_status(job_id):
    status_path = UPLOAD_DIR / f"{job_id}.status.json"
    if not status_path.exists():
        return jsonify(error="Job not found"), 404
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as exc:
        return jsonify(status="failed", error=str(exc)), 500


@app.get("/download/<job_id>")
def download_pdf(job_id):
    status_path = UPLOAD_DIR / f"{job_id}.status.json"
    if not status_path.exists():
        return "Job not found", 404
    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        status_data = {}
    output_path = UPLOAD_DIR / f"{job_id}.output.pdf"
    if not output_path.exists():
        return "File not found or processing failed", 404
    
    filename = status_data.get("filename", "redesigned.pdf")
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
        
    def cleanup():
        time.sleep(300)
        output_path.unlink(missing_ok=True)
        status_path.unlink(missing_ok=True)
        
    Thread(target=cleanup).start()
    
    return send_file(
        output_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="PDF is too large. Maximum size is 25 MB."), 413


def _open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    # Open browser only once on initial launch (parent process), not on reloads
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        Timer(1.5, _open_browser).start()

    print("\n" + "="*60)
    print(" NOTES NINJA PDF FORMATTER STARTED")
    print(" Click the link to open the app: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True)
