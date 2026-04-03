# PDF to Markdown Converter

A simple command-line tool that takes a PDF and converts it into a Markdown file. Built with Python, runs fully on CPU, no internet or paid APIs required.

---

## What it does

- Detects headings, paragraphs, bullet and numbered lists
- Picks up bold and italic text
- Extracts tables and converts them to Markdown format
- Falls back to OCR if the PDF is scanned or image-based

---

## Project Structure

```
pdf-to-markdown/
│
├── app.py            ← the file you run
├── converter.py      ← core logic
├── samples/
│   ├── sample_test.pdf        ← example input PDF
│   └── test_output.md         ← expected output for sample_test.pdf
│
└── README.md
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/pdf-to-markdown.git
cd pdf-to-markdown
```

### 2. Create a virtual environment

Keeps dependencies isolated from the rest of your system. Recommended but not required.

**Mac / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install pymupdf pdfplumber pytesseract Pillow
```

### 4. Install Tesseract (only if you need OCR)

Only needed for scanned or image-based PDFs. Skip this if your PDFs are regular text documents.

**Mac**
```bash
brew install tesseract
```

**Ubuntu / Debian**
```bash
sudo apt install tesseract-ocr
```

**Windows**
Download and run the installer from https://github.com/UB-Mannheim/tesseract/wiki — make sure to tick "Add to PATH" during setup.

---

## Usage

```bash
python app.py input.pdf output.md
```

Just give it a PDF and a name for the output file. The output file is created automatically — you don't need to create it yourself.

**Examples**

```bash
# Both files in the same folder
python app.py report.pdf report.md

# PDF in a subfolder
python app.py samples/report.pdf samples/report.md

# Full path (Mac/Linux)
python app.py /Users/yourname/Downloads/document.pdf output.md

# Full path (Windows)
python app.py C:\Users\yourname\Downloads\document.pdf output.md
```

---

## How Detection Works — Examples

Here is what the converter actually does with different kinds of content in a PDF.

### Headings

The converter reads the font size of every line. If a line is noticeably larger than the body text, it becomes a heading. The bigger the difference, the higher the heading level.

**PDF looks like:**
```
Introduction          ← large font (22pt)
Getting Started       ← medium font (16pt)
Prerequisites         ← slightly larger (13pt)
This is body text.    ← normal (10pt)
```

**Output:**
```markdown
# Introduction

## Getting Started

### Prerequisites

This is body text.
```

---

### Bold and Italic

PDF fonts carry style flags internally. The converter reads those flags directly — no guessing involved.

**PDF looks like:**
```
This is bold text and this is italic and this is both.
```

**Output:**
```markdown
This is **bold text** and this is *italic* and this is ***both***.
```

---

### Bullet Lists

Lines starting with `-`, `•`, `*`, or `–` are detected as bullet items.

**PDF looks like:**
```
• Install Python
• Clone the repo
• Run the script
```

**Output:**
```markdown
- Install Python
- Clone the repo
- Run the script
```

---

### Numbered Lists

Lines starting with `1.`, `2.`, `1)` etc. are detected as numbered items. Some PDFs put the number and the text on separate lines with different font sizes — the converter handles this and merges them correctly.

**PDF looks like:**
```
1. Open the file
2. Edit the config
3. Save and exit
```

**Output:**
```markdown
1. Open the file
2. Edit the config
3. Save and exit
```

---

### Tables

Tables are detected by `pdfplumber` which finds grid structures on the page. Each cell is extracted and the converter builds a standard Markdown table with a header separator row.

**PDF looks like:**
```
┌───────┬─────┬────────┐
│ Name  │ Age │ City   │
├───────┼─────┼────────┤
│ Alice │ 30  │ London │
│ Bob   │ 25  │ Paris  │
└───────┴─────┴────────┘
```

**Output:**
```markdown
| Name  | Age | City   |
| ---   | --- | ---    |
| Alice | 30  | London |
| Bob   | 25  | Paris  |
```

---

### Scanned / Image PDFs (OCR)

If a page has no extractable text (i.e. it is a scanned document), the converter rasterises the page into an image and runs Tesseract OCR on it. This is slower but means the tool never silently produces an empty output file.

---

## Limitations

- Complex multi-column layouts may not convert perfectly
- Password-protected PDFs are not supported
- Images inside PDFs are skipped — only text and tables are extracted
- Scanned PDFs work but are slower — OCR on large files (50+ pages) will take time

---

## Dependencies

| Library | Purpose |
|---|---|
| `pymupdf` | Text extraction with font and style info |
| `pdfplumber` | Table extraction |
| `pytesseract` + `Pillow` | OCR for scanned PDFs |
