"""
PDF to Markdown Converter
Sugarclass Screening Task - Trainee SWE

Supports:
- Headings detection (by font size)
- Paragraphs
- Lists (bullet & numbered)
- Bold / italic formatting (via font flags)
- Tables (via pdfplumber)
- OCR fallback for scanned PDFs
"""

import re
import fitz          # PyMuPDF — font-size + style info
import pdfplumber    # table extraction


# ─── Helpers ────────────────────────────────────────────────────────────────

def _flags_to_md(text: str, flags: int) -> str:
    """Wrap text in Markdown bold/italic markers based on PDF font flags."""
    bold   = bool(flags & (1 << 4))   # bit 4 = bold
    italic = bool(flags & (1 << 1))   # bit 1 = italic
    if bold and italic:
        return f"***{text}***"
    if bold:
        return f"**{text}**"
    if italic:
        return f"*{text}*"
    return text


def _is_list_item(text: str):
    """Return (marker, rest) if the line looks like a list item, else None."""
    # Bullet: -, •, *, ·, –
    m = re.match(r'^[\-\•\*\·\–]\s+(.+)', text)
    if m:
        return '-', m.group(1)
    # Numbered: 1. or 1)
    m = re.match(r'^(\d+)[.)]\s+(.+)', text)
    if m:
        return m.group(1) + '.', m.group(2)
    return None


def _table_to_md(table) -> str:
    """Convert a pdfplumber table (list of rows) to a Markdown table string."""
    if not table or len(table) < 1:
        return ''
    rows = []
    for i, row in enumerate(table):
        cells = [str(c or '').replace('\n', ' ').strip() for c in row]
        rows.append('| ' + ' | '.join(cells) + ' |')
        if i == 0:                          # separator after header row
            rows.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
    return '\n'.join(rows)


# ─── OCR fallback ────────────────────────────────────────────────────────────

def _ocr_page(page_fitz) -> str:
    """Rasterise a page and run Tesseract OCR. Used when no text is embedded."""
    try:
        import pytesseract
        from PIL import Image
        import io
        pix = page_fitz.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes('png')))
        return pytesseract.image_to_string(img)
    except Exception as e:
        return f"[OCR failed: {e}]"


# ─── Core extraction ─────────────────────────────────────────────────────────

def extract_page(fitz_doc, plumber_doc, page_index: int) -> str:
    """
    Extract one page and return Markdown text.

    Strategy:
    1. Use pdfplumber to find tables and their bounding boxes.
    2. Use PyMuPDF blocks (which carry font-size / flags) for everything else.
    3. Detect headings by comparing span font-size to the page median.
    4. Detect list items by leading bullet/number patterns.
    5. Fall back to OCR if the page has no extractable text.
    """
    fitz_page    = fitz_doc[page_index]
    plumber_page = plumber_doc.pages[page_index]

    # ── 1. Extract tables first ──────────────────────────────────────────────
    tables    = plumber_page.find_tables()
    table_bbs = []   # bounding boxes of table regions (to skip later)
    table_mds = {}   # map top-y → markdown string

    for tbl in tables:
        data = tbl.extract()
        if data:
            bb = tbl.bbox           # (x0, y0, x1, y1) in PDF points
            table_bbs.append(bb)
            table_mds[bb[1]] = _table_to_md(data)

    # ── 2. Collect font sizes to determine heading thresholds ────────────────
    all_sizes = []
    blocks = fitz_page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        if block.get("type") != 0:   # 0 = text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = round(span["size"])
                if sz > 0:
                    all_sizes.append(sz)

    body_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 12

    # ── 3. Walk text blocks ──────────────────────────────────────────────────
    md_lines = []

    # Insert table placeholders sorted by y-position
    pending_tables = sorted(table_mds.items())   # [(y, md_str), ...]
    table_idx = 0

    def _in_table(block_y):
        for (x0, y0, x1, y1) in table_bbs:
            if y0 <= block_y <= y1:
                return True
        return False

    pending_number = None   # buffers a lone digit line like "1" until next line

    for block in blocks:
        if block.get("type") != 0:
            continue

        block_y = block["bbox"][1]

        # Flush any pending tables that appear before this block
        while table_idx < len(pending_tables) and pending_tables[table_idx][0] < block_y:
            md_lines.append('\n' + pending_tables[table_idx][1] + '\n')
            table_idx += 1

        # Skip blocks that sit inside a table region
        if _in_table(block_y):
            continue

        for line in block.get("lines", []):
            line_parts = []
            line_size  = 0

            for span in line.get("spans", []):
                t = span["text"].strip()
                if not t:
                    continue
                line_size = max(line_size, round(span["size"]))
                line_parts.append(_flags_to_md(t, span["flags"]))

            raw = ' '.join(line_parts).strip()
            if not raw:
                continue

            # ── Lone number guard ──────────────────────────────────────────
            # Some PDFs style list numbers slightly larger than body text,
            # which would wrongly trigger heading detection.
            # If the entire line is just a bare number, always buffer it
            # regardless of font size — never treat it as a heading.
            if re.match(r'^\d+$', raw):
                pending_number = raw
                continue

            # Flush a buffered number: prepend it to the current line
            if pending_number is not None:
                raw = f'{pending_number}. {raw}'
                pending_number = None

            # ── Heading detection ──────────────────────────────────────────
            if line_size >= body_size + 6:
                md_lines.append(f'\n# {raw}\n')
            elif line_size >= body_size + 3:
                md_lines.append(f'\n## {raw}\n')
            elif line_size >= body_size + 1:
                md_lines.append(f'\n### {raw}\n')
            else:
                # ── List detection ─────────────────────────────────────────
                li = _is_list_item(raw)
                if li:
                    marker, content = li
                    md_lines.append(f'{marker} {content}')
                else:
                    md_lines.append(raw)

    # Flush remaining tables
    while table_idx < len(pending_tables):
        md_lines.append('\n' + pending_tables[table_idx][1] + '\n')
        table_idx += 1

    result = '\n'.join(md_lines).strip()

    # ── 4. OCR fallback ──────────────────────────────────────────────────────
    if not result:
        result = _ocr_page(fitz_page)

    return result


# ─── Public API ──────────────────────────────────────────────────────────────

def convert(pdf_path: str, output_path: str | None = None) -> str:
    """
    Convert a PDF file to Markdown.

    Args:
        pdf_path:    Path to the input PDF.
        output_path: If provided, write result to this file.

    Returns:
        The full Markdown string.
    """
    fitz_doc    = fitz.open(pdf_path)
    plumber_doc = pdfplumber.open(pdf_path)

    pages_md = []
    for i in range(len(fitz_doc)):
        page_md = extract_page(fitz_doc, plumber_doc, i)
        pages_md.append(page_md)

    plumber_doc.close()
    fitz_doc.close()

    markdown = '\n\n---\n\n'.join(pages_md)   # page separator

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f'✅  Saved: {output_path}')

    return markdown