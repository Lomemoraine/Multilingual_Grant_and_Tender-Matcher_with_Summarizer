# Multilingual Grant & Tender Matcher

## Overview
This project matches organization profiles to tender/grant announcements across languages (English/French). It generates synthetic tenders, parses files (.txt/.html/.pdf) into structured records, ranks matches using TF‑IDF and BM25, and produces short multilingual summaries explaining matches.

Deliverables:
- `datageneration/generator.py` → synthetic tenders and profiles
- `parsers/parse_tenders.py` → parser that writes `parsers/parsed_data/parsed_tenders.jsonl`
- `matcher.py` → matching pipeline (methods: `tfidf`, `bm25`, `combined`) and summary generation
- `summaries/` → generated profile-tender Markdown summaries
- `matcher_eval.json`, `matcher_eval_all.json` → evaluation metrics
- `eval_notebook.ipynb` → quick evaluation notebook showing metrics and example misses

---

## Workflow 
1. Generate synthetic data: tenders and profiles.
2. Parse the tender files into JSONL with structured fields (`title`, `sector`, `budget_value`, `deadline`, `description`, ...).
3. Run the matcher BM25 recommended best performer in terms of evaluation to produce top-K matches per profile and short summaries.
4. Inspect `summaries/` and `matcher_eval.json` / `matcher_eval_all.json` for metrics.

---

Prerequisites:
- Python 3.10+ (use the included virtual environment or create one)
- Recommended packages: `PyPDF2`, `beautifulsoup4`, `scikit-learn`, `rank_bm25`, `numpy`, `pandas`

1. Create and activate a virtualenv (optional but recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt

```

3. Generate data (creates `datageneration/data/tenders` and `datageneration/data/profiles.json`):

```powershell
python datageneration/generator.py
```

4. Parse tenders into structured JSONL:

```powershell
python parsers/parse_tenders.py
# output -> parsers/parsed_data/parsed_tenders.jsonl
```

5. Run the matcher (defaults to `bm25`):

```powershell
python matcher.py --method bm25 --parsed parsers/parsed_data/parsed_tenders.jsonl --profiles datageneration/data/profiles.json --out summaries --topk 5
```

6. Run all methods and save a summary of metrics:

```powershell

python -c "import runpy,sys, json; methods=['tfidf','bm25','combined']; results={};
for m in methods:
  sys.argv=['matcher.py','--method',m,'--parsed','parsers/parsed_data/parsed_tenders.jsonl','--out',f'summaries_{m}']; runpy.run_path('matcher.py', run_name='__main__');
  with open('matcher_eval.json','r',encoding='utf-8') as f: results[m]=json.load(f)
open('matcher_eval_all.json','w',encoding='utf-8').write(json.dumps(results,ensure_ascii=False,indent=2))"
```

7. Inspect results:

- Summaries: `summaries/` (one file per profile-tender pair)
- Evaluation: `matcher_eval.json` (last run) and `matcher_eval_all.json` (per-method)
- Notebook: open `eval_notebook.ipynb` and run cells — it displays a results table and confusion cases.


