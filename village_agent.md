# Village Agent — Product & Business Artifact

Objective
- Build a lightweight Multilingual Grant & Tender Matcher that helps entrepreneurs (often with limited literacy) discover relevant grants/tenders and understand why they match.

Target users
- Village-level entrepreneurs and small cooperative managers across Rwanda, Kenya, Senegal, DRC, Ethiopia.
- Intermediaries: NGOs, incubators, local business service providers.

Value proposition
- Surface top 5 relevant tenders per profile in the user's preferred language (EN/FR).
- Provide a short, plain-language summary per match that cites sector, budget fit, and deadline so non-experts can act quickly.

Key features
- Parser: ingest multi-format tenders (.txt/.html/.pdf), extract structured fields and normalize `budget_value` and language.
- Matcher: combined TF-IDF + BM25 ranking, with budget-fit boosting and concise summaries (≤80 words) in profile language.
- Outputs: per-profile `summaries/` folder, evaluation metrics (MRR@5, Recall@5), reproducible generator.

Deployment & UX
- CLI for batch runs (`matcher.py`) for programmatic use by intermediaries.
- Lightweight mobile/web interface idea: show top matches with one-line summary and clear CTA (Apply / Ask for help).
- Offline-capable distribution: export top matches as SMS/voice script or printable one-pagers for village agents.

Business model
- B2B SaaS to NGOs/incubators (monthly subscription for curated matching and alerts).
- One-off dataset generation and integration services for large donors.

Metrics & Success Criteria
- Match quality: MRR@5 >= 0.4 and Recall@5 >= 0.6 (initial target for production tuning).
- User uptake: conversion from match -> application assistance request.

Ethics & Data Privacy
- Only synthetic/demo data included in repo. For real deployments, remove PII and store minimal profile identifiers.
- Offer opt-in/consent for data sharing and enable local-only runs for sensitive use-cases.

Next steps (product roadmap)
1. Add a simple web/mobile UI with language and assistive voice output.
2. Integrate small multilingual embeddings for better cross-lingual matching.
3. Add feedback loop capture (which matches were useful) to improve ranking.
