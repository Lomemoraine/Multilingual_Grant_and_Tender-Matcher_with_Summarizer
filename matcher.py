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
    if not parts:
        parts = [str(v) for v in d.values()]
    return '\n'.join(parts)

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
    # budget fit heuristic
    budget_val = parse_budget(budget)
    employees = profile.get('employees', 0)
    if budget_val >= 200000 and employees >= 50:
        fit = 'well suited to mid-to-large teams'
    elif budget_val >= 50000:
        fit = 'appropriate for growing SMEs'
    else:
        fit = 'suited for small enterprises or pilots'

    if lang.upper().startswith('FR'):
        summary = (f"{tender.get('title','Le dossier')} correspond au profil car secteur: {sector}. "
                   f"Budget: {budget} — {fit}. Date limite: {deadline}.")
    else:
        summary = (f"{tender.get('title','This tender')} matches the profile: sector {sector}. "
                   f"Budget: {budget} — {fit}. Deadline: {deadline}.")

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

    corpus = [doc_text(d) for d in docs]
    vectorizer = TfidfVectorizer(max_df=0.9, min_df=1)
    X = vectorizer.fit_transform(corpus)

    os.makedirs(out_dir, exist_ok=True)
    summaries = []

    for p in profiles:
        q = p.get('needs_text','')
        qv = vectorizer.transform([q])
        sims = cosine_similarity(qv, X)[0]
        ranked_idx = sims.argsort()[::-1][:topk]
        for rank, idx in enumerate(ranked_idx, start=1):
            doc = docs[idx]
            summary = generate_summary(p, doc, lang=(p.get('languages') or ['EN'])[0])
            fname = Path(out_dir) / f"profile_{p['id']}_tender_{doc.get('file','').split('_')[-1].split('.')[0]}.md"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# Profile {p['id']} — Tender {doc.get('file')}\n\n")
                f.write(summary + '\n')
            summaries.append((p['id'], doc.get('file'), sims[idx]))
    return summaries

def run_bm25(parsed_path, profiles_path, out_dir, topk=5):
    from rank_bm25 import BM25Okapi

    docs = load_parsed(parsed_path)
    profiles = load_profiles(profiles_path)

    tokenized_corpus = [tokenize_simple(doc_text(d)) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    os.makedirs(out_dir, exist_ok=True)
    summaries = []

    for p in profiles:
        q = p.get('needs_text','')
        q_tokens = tokenize_simple(q)
        scores = bm25.get_scores(q_tokens)
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:topk]
        for rank, idx in enumerate(ranked_idx, start=1):
            doc = docs[idx]
            summary = generate_summary(p, doc, lang=(p.get('languages') or ['EN'])[0])
            fname = Path(out_dir) / f"profile_{p['id']}_tender_{doc.get('file','').split('_')[-1].split('.')[0]}.md"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# Profile {p['id']} — Tender {doc.get('file')}\n\n")
                f.write(summary + '\n')
            summaries.append((p['id'], doc.get('file'), scores[idx]))
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
    p.add_argument('--method', choices=['tfidf','bm25'], default='tfidf')
    p.add_argument('--parsed', default='datageneration/data/parsed_tenders.jsonl')
    p.add_argument('--profiles', default='datageneration/data/profiles.json')
    p.add_argument('--out', default='summaries')
    p.add_argument('--topk', type=int, default=5)
    p.add_argument('--gold', default='datageneration/data/gold_matches.csv')
    args = p.parse_args()

    if args.method == 'tfidf':
        preds = run_tfidf(args.parsed, args.profiles, args.out, topk=args.topk)
    else:
        preds = run_bm25(args.parsed, args.profiles, args.out, topk=args.topk)

    print(f"Wrote summaries to {args.out}")
    if os.path.exists(args.gold):
        metrics = evaluate_topk(preds, args.gold, topk=args.topk)
        print('Evaluation:', metrics)
        with open('matcher_eval.json','w',encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

if __name__ == '__main__':
    main()
