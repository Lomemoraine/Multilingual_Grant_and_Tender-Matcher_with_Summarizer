import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Dict

def load_parsed(path: str) -> List[Dict]:
    docs = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))
    return docs

def load_profiles(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def doc_text(d: Dict) -> str:
    parts = []
    for k in ('title','description','eligibility'):
        if d.get(k):
            parts.append(d[k])
    # fallback join other fields
    if not parts or ('description' not in d and d.get('file')):
        # try to load description from source file if available
        fp = d.get('file')
        if fp:
            try:
                p = Path(fp)
                ext = p.suffix.lower()
                text = ''
                if ext == '.pdf':
                    from PyPDF2 import PdfReader
                    with open(p, 'rb') as f:
                        reader = PdfReader(f)
                        text = '\n'.join([page.extract_text() or '' for page in reader.pages])
                elif ext in ('.htm', '.html'):
                    from bs4 import BeautifulSoup
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                        text = soup.get_text('\n')
                else:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()

                if text:
                    m = re.search(r"Description:\s*(.*?)(?:\n\s*Eligibility:|\Z)", text, re.S | re.I)
                    if m:
                        parts.append(m.group(1).strip())
            except Exception:
                # ignore extraction errors and fallback
                pass

    if not parts:
        parts = [str(v) for v in d.values()]
    return '\n'.join(parts)


def strip_boilerplate(text: str) -> str:
    """Remove common boilerplate sentences that add noise for TF-IDF/BM25.

    This keeps key descriptive content while removing repetitive application
    instructions, evaluation boilerplate, and obvious budget/deadline lines.
    """
    if not text:
        return text
    # normalize whitespace
    text = re.sub(r"\r\n|\r", "\n", text)
    # split into candidate sentences by punctuation and newlines
    parts = re.split(r'(?<=[\.!?])\s+|\n+', text)
    keep = []
    # patterns that signal boilerplate (EN/FR)
    boiler_patterns = [
        r"applicants? (are )?invited",
        r"appel à propositions",
        r"les candidats",
        r"all submissions",
        r"will be evaluated",
        r"les soumissions seront évaluées",
        r"please submit",
        r"veuillez soumettre",
        r"submission must",
        r"date limite",
        r"deadline:",
        r"budget disponible",
        r"available budget",
        r"applicants are requested",
        r"applicants must",
    ]
    bp = re.compile('|'.join(boiler_patterns), re.I)
    for s in parts:
        s_stripped = s.strip()
        if not s_stripped:
            continue
        # skip sentences that look like boilerplate
        if bp.search(s_stripped):
            continue
        # skip very short generic lines like 'Eligibility: SMEs'
        if len(s_stripped.split()) < 3 and ':' in s_stripped:
            continue
        keep.append(s_stripped)
    return ' '.join(keep)

def tokenize_simple(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ]+", ' ', s)
    return [t for t in s.split() if t]

def parse_budget(b: str) -> int:
    if not b:
        return 0
    nums = re.findall(r"\d+", b.replace(',', ''))
    if not nums:
        return 0
    # join in case of multiple groups (e.g. 1 000 000)
    return int(''.join(nums))

def generate_summary(profile: Dict, tender: Dict, lang: str='EN') -> str:
    # extract key elements
    sector = tender.get('sector','unknown')
    budget = tender.get('budget','unknown')
    deadline = tender.get('deadline','unknown')
    # budget fit heuristic (uses parsed numeric budgets when available)
    budget_val = None
    if tender.get('budget_value') is not None:
        try:
            budget_val = int(tender.get('budget_value'))
        except Exception:
            budget_val = None
    employees = profile.get('employees', 0)

    # desired budget by company size
    if employees >= 100:
        desired = 200000
    elif employees >= 50:
        desired = 50000
    elif employees >= 10:
        desired = 5000
    else:
        desired = 5000

    def budget_fit_score(bv, desired):
        if bv is None:
            return 0.0
        diff = abs(bv - desired)
        score = 1.0 - (diff / max(desired, 1))
        return max(0.0, min(1.0, score))

    fit_score = budget_fit_score(budget_val, desired)
    if budget_val is None:
        fit_text = 'budget unspecified'
    else:
        if fit_score > 0.66:
            fit_text = 'well matched to the company size'
        elif fit_score > 0.33:
            fit_text = 'moderately matched'
        else:
            fit_text = 'may be too large or too small'

    # matched terms heuristic (for explainability)
    from collections import Counter
    from math import isfinite
    prof_terms = tokenize_simple(profile.get('needs_text',''))
    doc_terms = tokenize_simple(doc_text(tender))
    matched_terms = set(prof_terms) & set(doc_terms)

    if lang.upper().startswith('FR'):
        summary = (
            f"{tender.get('title','Le dossier')} correspond au profil — secteur: {sector}. "
            f"Budget: {budget} ({fit_text}). Date limite: {deadline}. "
            f"Mots correspondants: {', '.join(sorted(list(matched_terms))[:5])}.")
    else:
        summary = (
            f"{tender.get('title','This tender')} matches the profile — sector: {sector}. "
            f"Budget: {budget} ({fit_text}). Deadline: {deadline}. "
            f"Matching terms: {', '.join(sorted(list(matched_terms))[:5])}.")

    # enforce ~80 words max
    words = summary.split()
    if len(words) > 80:
        summary = ' '.join(words[:80])
    return summary

def run_tfidf(parsed_path, profiles_path, out_dir, topk=5):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = load_parsed(parsed_path)
    profiles = load_profiles(profiles_path)

    corpus = [strip_boilerplate(doc_text(d)) for d in docs]
    vectorizer = TfidfVectorizer(max_df=0.9, min_df=1)
    X = vectorizer.fit_transform(corpus)

    os.makedirs(out_dir, exist_ok=True)
    summaries = []

    alpha = 0.3  # weight for budget fit boost
    for p in profiles:
        q = p.get('needs_text','')
        qv = vectorizer.transform([q])
        sims = cosine_similarity(qv, X)[0]
        # compute budget fit boost per document
        boosts = []
        for d in docs:
            bv = d.get('budget_value')
            employees = p.get('employees', 0)
            # desired budget
            if employees >= 100:
                desired = 200000
            elif employees >= 50:
                desired = 50000
            elif employees >= 10:
                desired = 5000
            else:
                desired = 5000
            if bv is None:
                boosts.append(0.0)
            else:
                diff = abs(int(bv) - desired)
                score = 1.0 - (diff / max(desired, 1))
                score = max(0.0, min(1.0, score))
                boosts.append(score)

        final_scores = [s + alpha * b for s, b in zip(sims, boosts)]
        ranked_idx = sorted(range(len(final_scores)), key=lambda i: final_scores[i], reverse=True)[:topk]
        for rank, idx in enumerate(ranked_idx, start=1):
            doc = docs[idx]
            final_score = final_scores[idx]
            summary = generate_summary(p, doc, lang=(p.get('languages') or ['EN'])[0])
            fname = Path(out_dir) / f"profile_{p['id']}_tender_{doc.get('file','').split('_')[-1].split('.')[0]}.md"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# Profile {p['id']} — Tender {doc.get('file')}\n\n")
                f.write(summary + '\n')
                f.write(f"\n_Score: {final_score:.4f}_\n")
            summaries.append((p['id'], doc.get('file'), final_score))
    return summaries

def run_bm25(parsed_path, profiles_path, out_dir, topk=5):
    from rank_bm25 import BM25Okapi

    docs = load_parsed(parsed_path)
    profiles = load_profiles(profiles_path)

    tokenized_corpus = [tokenize_simple(strip_boilerplate(doc_text(d))) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    os.makedirs(out_dir, exist_ok=True)
    summaries = []

    alpha = 0.3
    for p in profiles:
        q = p.get('needs_text','')
        q_tokens = tokenize_simple(q)
        scores = bm25.get_scores(q_tokens)
        # budget boost
        boosts = []
        for d in docs:
            bv = d.get('budget_value')
            employees = p.get('employees', 0)
            if employees >= 100:
                desired = 200000
            elif employees >= 50:
                desired = 50000
            elif employees >= 10:
                desired = 5000
            else:
                desired = 5000
            if bv is None:
                boosts.append(0.0)
            else:
                diff = abs(int(bv) - desired)
                score = 1.0 - (diff / max(desired, 1))
                score = max(0.0, min(1.0, score))
                boosts.append(score)

        final_scores = [s + alpha * b for s, b in zip(scores, boosts)]
        ranked_idx = sorted(range(len(final_scores)), key=lambda i: final_scores[i], reverse=True)[:topk]
        for rank, idx in enumerate(ranked_idx, start=1):
            doc = docs[idx]
            final_score = final_scores[idx]
            summary = generate_summary(p, doc, lang=(p.get('languages') or ['EN'])[0])
            fname = Path(out_dir) / f"profile_{p['id']}_tender_{doc.get('file','').split('_')[-1].split('.')[0]}.md"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# Profile {p['id']} — Tender {doc.get('file')}\n\n")
                f.write(summary + '\n')
                f.write(f"\n_Score: {final_score:.4f}_\n")
            summaries.append((p['id'], doc.get('file'), final_score))
    return summaries


def run_combined(parsed_path, profiles_path, out_dir, topk=5, w_tfidf=0.5, w_bm25=0.5, alpha=0.3):
    """Combine TF-IDF cosine similarity and BM25 scores into a single ranking.

    Scores are normalized to [0,1] per-profile and then combined with weights.
    A small budget-fit boost (alpha) is added as before.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from rank_bm25 import BM25Okapi
    import numpy as np

    docs = load_parsed(parsed_path)
    profiles = load_profiles(profiles_path)

    corpus = [strip_boilerplate(doc_text(d)) for d in docs]
    vectorizer = TfidfVectorizer(max_df=0.9, min_df=1)
    X = vectorizer.fit_transform(corpus)

    tokenized_corpus = [tokenize_simple(doc_text(d)) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    os.makedirs(out_dir, exist_ok=True)
    summaries = []

    for p in profiles:
        q = p.get('needs_text','')
        # TF-IDF sims
        qv = vectorizer.transform([q])
        tfidf_sims = cosine_similarity(qv, X)[0]
        # BM25 scores
        q_tokens = tokenize_simple(q)
        bm25_scores = np.array(bm25.get_scores(q_tokens), dtype=float)

        # normalize both to 0-1
        def norm0to1(arr):
            a = np.array(arr, dtype=float)
            if a.size == 0:
                return a
            mn, mx = a.min(), a.max()
            if mx <= mn:
                return np.zeros_like(a)
            return (a - mn) / (mx - mn)

        tfidf_n = norm0to1(tfidf_sims)
        bm25_n = norm0to1(bm25_scores)

        # budget boost
        boosts = []
        for d in docs:
            bv = d.get('budget_value')
            employees = p.get('employees', 0)
            if employees >= 100:
                desired = 200000
            elif employees >= 50:
                desired = 50000
            elif employees >= 10:
                desired = 5000
            else:
                desired = 5000
            if bv is None:
                boosts.append(0.0)
            else:
                diff = abs(int(bv) - desired)
                score = 1.0 - (diff / max(desired, 1))
                score = max(0.0, min(1.0, score))
                boosts.append(score)

        boosts = np.array(boosts, dtype=float)

        combined = w_tfidf * tfidf_n + w_bm25 * bm25_n
        final_scores = combined + alpha * boosts

        ranked_idx = list(np.argsort(final_scores)[::-1][:topk])
        for idx in ranked_idx:
            doc = docs[idx]
            final_score = float(final_scores[idx])
            summary = generate_summary(p, doc, lang=(p.get('languages') or ['EN'])[0])
            fname = Path(out_dir) / f"profile_{p['id']}_tender_{doc.get('file','').split('_')[-1].split('.')[0]}.md"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# Profile {p['id']} — Tender {doc.get('file')}\n\n")
                f.write(summary + '\n')
                f.write(f"\n_Score: {final_score:.4f}_\n")
            summaries.append((p['id'], doc.get('file'), final_score))

    return summaries

def evaluate_topk(predictions, gold_csv, topk=5):
    import csv
    gold = {}
    with open(gold_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            pid = int(row[0]); tid = int(row[1])
            gold.setdefault(pid, set()).add(tid)

    # build ranking dict per profile from predictions
    preds = {}
    for pid, file, score in predictions:
        # extract tender id from filename end like tender_12.html
        m = re.search(r"tender_(\d+)", str(file))
        if not m:
            continue
        tid = int(m.group(1))
        preds.setdefault(pid, []).append(tid)

    mrrs = []
    recalls = []
    misses = []
    for pid, gold_set in gold.items():
        ranked = preds.get(pid, [])[:topk]
        # MRR
        rr = 0.0
        for i, tid in enumerate(ranked, start=1):
            if tid in gold_set:
                rr = 1.0 / i
                break
        mrrs.append(rr)
        # recall@k: proportion of gold retrieved in topk
        retrieved = sum(1 for tid in ranked if tid in gold_set)
        recalls.append(retrieved / len(gold_set))
        if retrieved == 0:
            misses.append(pid)

    import statistics
    return {
        'MRR@%d' % topk: statistics.mean(mrrs) if mrrs else 0.0,
        'Recall@%d' % topk: statistics.mean(recalls) if recalls else 0.0,
        'misses_sample': misses[:3]
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--method', choices=['combined','tfidf','bm25'], default='bm25')
    p.add_argument('--parsed', default='parsers/parsed_data/parsed_tenders.jsonl')
    p.add_argument('--profiles', default='datageneration/data/profiles.json')
    p.add_argument('--out', default='summaries')
    p.add_argument('--topk', type=int, default=5)
    p.add_argument('--gold', default='datageneration/data/gold_matches.csv')
    args = p.parse_args()

    if args.method == 'tfidf':
        preds = run_tfidf(args.parsed, args.profiles, args.out, topk=args.topk)
    elif args.method == 'bm25':
        preds = run_bm25(args.parsed, args.profiles, args.out, topk=args.topk)
    else:
        preds = run_combined(args.parsed, args.profiles, args.out, topk=args.topk)

    print(f"Wrote summaries to {args.out}")
    if os.path.exists(args.gold):
        metrics = evaluate_topk(preds, args.gold, topk=args.topk)
        print('Evaluation:', metrics)
        with open('matcher_eval.json','w',encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

if __name__ == '__main__':
    main()
