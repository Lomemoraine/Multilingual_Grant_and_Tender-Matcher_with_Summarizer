import os
import re
import json
from pathlib import Path

SECTORS = ["agritech","healthtech","cleantech","edtech","fintech","wastetech"]

def normalize_budget(budget_str):
    """Return integer budget (USD) parsed from a string like '50,000 USD' or '50000 USD'."""
    if not budget_str:
        return None
    s = str(budget_str)
    # handle common thousand separators and currency symbols
    s = s.replace(',', '').replace('\u00A0', ' ')
    # find number groups (including possible decimals)
    m = re.search(r"(\d+[\d\s]*)", s)
    if not m:
        # handle compact forms like '5k' or '5K'
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*[kK]", s)
        if m2:
            try:
                return int(float(m2.group(1)) * 1000)
            except Exception:
                return None
        return None
    num = re.sub(r"\s+", '', m.group(1))
    try:
        return int(float(num))
    except Exception:
        return None

def extract_fields(text):
    # Basic line-based extraction
    fields = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^Title:\s*(.+)$", line, re.I)
        if m:
            fields['title'] = m.group(1).strip()
            continue
        m = re.match(r"^Sector:\s*(.+)$", line, re.I)
        if m:
            fields['sector'] = m.group(1).strip()
            continue
        m = re.match(r"^Budget:\s*(.+)$", line, re.I)
        if m:
            raw = m.group(1).strip()
            fields['budget'] = raw
            fields['budget_value'] = normalize_budget(raw)
            continue
        m = re.match(r"^Deadline:\s*(.+)$", line, re.I)
        if m:
            fields['deadline'] = m.group(1).strip()
            continue
        m = re.match(r"^Eligibility:\s*(.+)$", line, re.I)
        if m:
            fields['eligibility'] = m.group(1).strip()
            continue
        m = re.match(r"^Region:\s*(.+)$", line, re.I)
        if m:
            fields['region'] = m.group(1).strip()
            continue
        m = re.match(r"^Language:\s*(.+)$", line, re.I)
        if m:
            fields['language'] = m.group(1).strip()
            continue

    # Fallback: infer sector by keyword if missing
    if 'sector' not in fields:
        low = text.lower()
        for s in SECTORS:
            if s in low:
                fields['sector'] = s
                break

    # Extract a multi-line Description: block if present
    if 'description' not in fields:
        m = re.search(r"Description:\s*(.*?)(?:\n\s*(?:Eligibility:|$))", text, re.S | re.I)
        if m:
            fields['description'] = m.group(1).strip()

    return fields

def read_txt(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def read_html(path):
    from bs4 import BeautifulSoup
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text('\n')

def read_pdf(path):
    # Uses PyPDF2 to extract text
    from PyPDF2 import PdfReader
    text_parts = []
    with open(path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text() or '')
            except Exception:
                continue
    return '\n'.join(text_parts)

def parse_all(tenders_dir, out_path):
    p = Path(tenders_dir)
    records = []
    for fp in sorted(p.iterdir()):
        if not fp.is_file():
            continue
        ext = fp.suffix.lower()
        try:
            if ext == '.txt':
                text = read_txt(fp)
            elif ext in ('.htm', '.html'):
                text = read_html(fp)
            elif ext == '.pdf':
                text = read_pdf(fp)
            else:
                # skip unknown
                continue
        except Exception as e:
            print(f"Failed to read {fp}: {e}")
            continue

        fields = extract_fields(text)
        fields['file'] = str(fp)
        records.append(fields)

    # write jsonl
    with open(out_path, 'w', encoding='utf-8') as out:
        for r in records:
            out.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f"Parsed {len(records)} tenders -> {out_path}")
    return records

if __name__ == '__main__':
    base = Path('datageneration/data/tenders')
    out = Path('parsers/parsed_data/parsed_tenders.jsonl')
    os.makedirs(out.parent, exist_ok=True)
    parse_all(base, out)
